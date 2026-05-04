"""
AdaptiveAI — Knowledge State Service
Server-side source of truth for per-user analytics, mastery, misconceptions.
One document per user in the `knowledge_states` collection.
"""

import logging
from datetime import datetime
from database import Database

logger = logging.getLogger(__name__)

# ── default structures ──────────────────────────────────────
DEFAULT_BEHAVIORAL = {
    'question_types': {
        'definition': 0, 'how_to': 0, 'why': 0,
        'comparison': 0, 'debugging': 0, 'code_request': 0, 'general': 0,
    },
    'complexity_distribution': {'beginner': 0, 'intermediate': 0, 'advanced': 0},
    'skill_progression': [],
    'engagement_metrics': {
        'total_messages': 0,
        'avg_message_length': 0,
        'follow_up_rate': 0,
        'code_requests': 0,
        'uncertainty_count': 0,
    },
    'last_analyzed': None,
}


def _ensure_defaults(doc):
    """Fill in missing sub-keys so callers never KeyError."""
    if not doc:
        return None
    doc.setdefault('topics', {})
    doc.setdefault('recent_topics', [])
    doc.setdefault('behavioral', {**DEFAULT_BEHAVIORAL})
    for k, v in DEFAULT_BEHAVIORAL.items():
        doc['behavioral'].setdefault(k, v if not isinstance(v, dict) else {**v})
    doc.setdefault('misconceptions', {})
    doc.setdefault('current_adaptations', {})
    doc['current_adaptations'].setdefault('tutoring_mode', 'direct')
    doc['current_adaptations'].setdefault('mode_reason', 'stable understanding detected')
    doc['current_adaptations'].setdefault('socratic_mode', False)
    doc['current_adaptations'].setdefault('emotional_state', 'neutral')
    doc['current_adaptations'].setdefault('suggested_approach', 'explain_simply')
    doc['current_adaptations'].setdefault('comprehension_check', None)
    doc.setdefault('mode_history', [])
    doc.setdefault('strong_topics', [])
    doc.setdefault('weak_topics', [])
    doc.setdefault('conversation_preferences', {})
    doc['conversation_preferences'].setdefault('explanation_style', '')
    doc['conversation_preferences'].setdefault('prefers_examples', False)
    doc['conversation_preferences'].setdefault('prefers_code', False)
    doc['conversation_preferences'].setdefault('prefers_analogies', False)
    doc['conversation_preferences'].setdefault('preferred_tone', '')
    doc['conversation_preferences'].setdefault('preferred_length', '')
    doc['conversation_preferences'].setdefault('adaptive_preference', '')
    return doc


class KnowledgeStateService:
    """CRUD + analytics logic for the knowledge_states collection."""

    # ── read ────────────────────────────────────────────────
    @staticmethod
    def get(user_id):
        """Return the knowledge-state doc for *user_id* (or a fresh default)."""
        coll = Database.get_collection('knowledge_states')
        doc = coll.find_one({'user_id': user_id}, {'_id': 0})
        if doc:
            return _ensure_defaults(doc)
        # First time — return empty shell (not yet persisted)
        return _ensure_defaults({
            'user_id': user_id,
            'updated_at': datetime.utcnow().isoformat(),
            'topics': {},
            'behavioral': {**DEFAULT_BEHAVIORAL},
            'misconceptions': {},
            'current_adaptations': {},
            'strong_topics': [],
            'weak_topics': [],
            'conversation_preferences': {},
        })

    # ── write (full upsert) ─────────────────────────────────
    @staticmethod
    def save(user_id, state: dict):
        """Upsert the full knowledge_state document."""
        coll = Database.get_collection('knowledge_states')
        state['user_id'] = user_id
        state['updated_at'] = datetime.utcnow().isoformat()
        coll.update_one(
            {'user_id': user_id},
            {'$set': state},
            upsert=True,
        )

    # ── atomic update after a chat message ──────────────────
    @staticmethod
    def update_from_analysis(user_id, analysis: dict, message_text: str):
        """
        Merge an analysis result into the persisted knowledge state.
        Called inside /chat/groq after the AI responds.

        `analysis` keys used:
            topics, complexity, question_type,
            message_analysis, recommendations
        """
        ks = KnowledgeStateService.get(user_id)
        ba = ks['behavioral']
        topics_map = ks['topics']
        misconceptions = ks['misconceptions']
        prefs = ks['conversation_preferences']

        topics = analysis.get('topics', [])
        complexity = analysis.get('complexity', 'intermediate')
        qtype = analysis.get('question_type', 'general')
        meta = analysis.get('message_analysis', {})
        recs = analysis.get('recommendations', {})
        mode = recs.get('tutoring_mode', 'direct')
        mode_reason = recs.get('mode_reason', 'stable understanding detected')

        # 1) question type counter
        if qtype in ba['question_types']:
            ba['question_types'][qtype] += 1

        # 2) complexity distribution
        if complexity in ba['complexity_distribution']:
            ba['complexity_distribution'][complexity] += 1

        # 3) per-topic tracking
        now_iso = datetime.utcnow().isoformat()
        
        # update recent topics ring buffer (max 10)
        recent = ks.get('recent_topics', [])
        for t in topics:
            if t in recent:
                recent.remove(t)
            recent.insert(0, t)
        ks['recent_topics'] = recent[:10]

        for t in topics:
            if t not in topics_map:
                topics_map[t] = {
                    'count': 0,
                    'first_seen': now_iso,
                    'last_seen': now_iso,
                    'complexity_levels': {'beginner': 0, 'intermediate': 0, 'advanced': 0},
                    'verified': False,
                }
            td = topics_map[t]
            td['count'] += 1
            td['last_seen'] = now_iso
            if complexity in td['complexity_levels']:
                td['complexity_levels'][complexity] += 1

        # 4) engagement metrics
        eng = ba['engagement_metrics']
        eng['total_messages'] += 1
        prev_total = eng['avg_message_length'] * (eng['total_messages'] - 1)
        eng['avg_message_length'] = round(
            (prev_total + meta.get('word_count', 0)) / eng['total_messages'], 1
        )
        if meta.get('has_code'):
            eng['code_requests'] += 1
        eng['uncertainty_count'] += meta.get('uncertainty_markers', 0)

        ba['last_analyzed'] = now_iso

        # 5) strong / weak topics
        strong = list(ks['strong_topics'])
        weak = list(ks['weak_topics'])
        for t in (recs.get('add_to_strong_topics') or []):
            if t not in strong:
                strong.append(t)
        for t in (recs.get('add_to_weak_topics') or []):
            if t not in weak and t not in strong:
                weak.append(t)
        for t in (recs.get('move_to_strong_topics') or []):
            if t in weak:
                weak.remove(t)
            if t not in strong:
                strong.append(t)

        # 6) skill level progression
        new_level = recs.get('update_skill_level')
        if new_level:
            current = ks.get('skill_level', 'Intermediate')
            if new_level != current:
                ba['skill_progression'].append({
                    'from': current,
                    'to': new_level,
                    'timestamp': now_iso,
                })
                ks['skill_level'] = new_level

        # 7) knowledge-state mastery per topic
        for t in topics:
            td = topics_map.get(t, {})
            count = td.get('count', 0)
            if count >= 2:
                cl = td.get('complexity_levels', {})
                total = cl.get('beginner', 0) + cl.get('intermediate', 0) + cl.get('advanced', 0)
                if total > 0:
                    mastery = (
                        cl.get('beginner', 0) * 0.2
                        + cl.get('intermediate', 0) * 0.5
                        + cl.get('advanced', 0) * 0.9
                    ) / total + min(0.15, count * 0.015)
                    mastery = min(1.0, round(mastery, 2))
                else:
                    mastery = 0.1
                td['mastery_level'] = mastery

        # 8) misconceptions
        if recs.get('misconception_detected'):
            mt = recs.get('misconception_topic') or (topics[0] if topics else 'general')
            if mt not in misconceptions:
                misconceptions[mt] = {
                    'count': 0,
                    'detail': recs.get('misconception_detail', 'Possible misunderstanding'),
                    'first_seen': now_iso,
                    'corrected': False,
                }
            misconceptions[mt]['count'] += 1
            misconceptions[mt]['last_seen'] = now_iso

        # 9) adaptations
        ks['current_adaptations'] = {
            'tutoring_mode': mode,
            'mode_reason': mode_reason,
            'socratic_mode': recs.get('trigger_socratic_mode', False),
            'emotional_state': recs.get('emotional_state', 'neutral'),
            'suggested_approach': recs.get('suggested_approach', 'explain_simply'),
            'comprehension_check': recs.get('comprehension_check_topic'),
        }

        mode_history = ks.get('mode_history', [])
        mode_history.append({
            'mode': mode,
            'reason': mode_reason,
            'timestamp': now_iso,
        })
        ks['mode_history'] = mode_history[-100:]

        # 10) conversation preferences (keyword sniff)
        msg_lower = message_text.lower()
        if 'give me an example' in msg_lower or 'for example' in msg_lower:
            prefs['prefers_examples'] = True
        if 'show me code' in msg_lower or 'write code' in msg_lower or meta.get('has_code'):
            prefs['prefers_code'] = True
        if 'analogy' in msg_lower or 'eli5' in msg_lower:
            prefs['prefers_analogies'] = True
        if 'explain simply' in msg_lower or 'simple terms' in msg_lower:
            prefs['explanation_style'] = 'simple'
        elif 'technically' in msg_lower or 'in depth' in msg_lower:
            prefs['explanation_style'] = 'technical'
        if any(w in msg_lower for w in ('friendly', 'casual')):
            prefs['preferred_tone'] = 'friendly'
        elif any(w in msg_lower for w in ('formal', 'professional')):
            prefs['preferred_tone'] = 'formal'
        if any(w in msg_lower for w in ('short', 'brief', 'concise')):
            prefs['preferred_length'] = 'short'
        elif any(w in msg_lower for w in ('detailed', 'elaborate')):
            prefs['preferred_length'] = 'detailed'

        # ── persist ────────────────────────────────────────
        ks['topics'] = topics_map
        ks['behavioral'] = ba
        ks['misconceptions'] = misconceptions
        ks['strong_topics'] = strong
        ks['weak_topics'] = weak
        ks['conversation_preferences'] = prefs

        KnowledgeStateService.save(user_id, ks)
        logger.debug("Updated knowledge state for user %s", user_id)
        return ks

    # ── update from quiz results ────────────────────────────
    @staticmethod
    def update_from_quiz(user_id: str, quiz: dict):
        """
        Process the results of a quiz to reinforce mastery levels and find weak spots.
        """
        ks = KnowledgeStateService.get(user_id)
        topics_map = ks.get('topics', {})
        weak = ks.get('weak_topics', [])
        strong = ks.get('strong_topics', [])
        
        # Analyze performance
        questions = quiz.get('questions', [])
        answers_submitted = quiz.get('answers_submitted', {})
        
        topic_scores = {} # topic -> {'correct': 0, 'total': 0}
        for q in questions:
            t = q.get('source_topic') or quiz.get('topic')
            if t not in topic_scores:
                topic_scores[t] = {'correct': 0, 'total': 0}
            
            topic_scores[t]['total'] += 1
            if answers_submitted.get(q['question_id'], '').strip().upper() == q['correct_answer']:
                topic_scores[t]['correct'] += 1
                
        now_iso = datetime.utcnow().isoformat()
        
        for t, stats in topic_scores.items():
            if stats['total'] == 0:
                continue
                
            percentage = stats['correct'] / stats['total']
            
            # Ensure topic exists in topic map
            if t not in topics_map:
                topics_map[t] = {
                    'count': 1,
                    'first_seen': now_iso,
                    'last_seen': now_iso,
                    'complexity_levels': {'beginner': 0, 'intermediate': 1, 'advanced': 0},
                    'mastery_level': 0.1,
                    'verified': False
                }
            
            td = topics_map[t]
            current_mastery = td.get('mastery_level', 0.1)
            
            # Adjust mastery
            if percentage >= 0.8:
                # Strong performance
                td['mastery_level'] = min(1.0, current_mastery + 0.2)
                td['verified'] = True
                if t in weak:
                    weak.remove(t)
                if t not in strong:
                    strong.append(t)
            elif percentage <= 0.4:
                # Weak performance
                td['mastery_level'] = max(0.1, current_mastery - 0.2)
                if t not in weak and t not in strong:
                    weak.append(t)
                elif t in strong:
                    strong.remove(t)
                    
        ks['topics'] = topics_map
        ks['weak_topics'] = weak
        ks['strong_topics'] = strong
        
        KnowledgeStateService.save(user_id, ks)
        logger.info("[KnowledgeState] Processed quiz results for user %s. Adjusted mastery.", user_id)
        return ks
