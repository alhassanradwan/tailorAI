"""
AdaptiveAI - Chat Routes
Handles all chat-related API endpoints
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import Config
from models.user import User
from services.ai_agents import AIService
from services.agent_router import DeepAgentRouter
from services.knowledge_state import KnowledgeStateService
from services.adaptive_mode_service import AdaptiveModeService
from services.langgraph.langgraph_service import app as langgraph_app
from database import Database
from datetime import datetime
import os
import json
from groq import Groq

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)

def classify_intent_with_llm(client, message: str) -> dict:
    prompt = f"""
Classify the user's intent.

Rules:
- "testing" ONLY if the user directly asks YOU to give a quiz/test.
- If quiz/exam is mentioned as context → "learning"
- Focus on the MAIN request, not side context.

Examples:
Input: "give me a quiz on CNN"
Output: {{"intent": "testing", "question_type": "quiz"}}

Input: "explain CNN I have a quiz tomorrow"
Output: {{"intent": "learning", "question_type": "concept"}}

Input: "my teacher will test me"
Output: {{"intent": "learning", "question_type": "general"}}

Now classify:
Input: "{message}"
Output ONLY JSON:
"""
    try:
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return json.loads(res.choices[0].message.content)
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")
        return {"intent": "learning", "question_type": "general"}



@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Legacy endpoint intentionally disabled. Use /api/chat/groq."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use /api/chat/groq."
    }), 410


@chat_bp.route('/history/<user_id>', methods=['GET'])
def get_chat_history(user_id):
    """Get chat history for a specific user"""
    
    try:
        interactions = Database.get_collection('interactions')
        history = list(interactions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50))
        
        return jsonify({
            "success": True,
            "history": history
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@chat_bp.route('/analyze-progression', methods=['POST'])
def analyze_progression():
    """
    Analyze if student should level up/down
    Can be called by n8n webhook or frontend
    """
    data = request.get_json()
    
    quiz_analytics = data.get('quiz_analytics')
    chat_history = data.get('chat_history', [])
    
    result = AIService.analyze_level_progression(quiz_analytics, chat_history)
    
    return jsonify(result), 200


@chat_bp.route('/groq', methods=['POST'])
@jwt_required()
def chat_groq():
    """
    Chat via Groq API using DeepAgentRouter + KnowledgeStateService.

    Expected payload:
    {
        "message": "Explain gradient descent",
        "profile": { "skill_level": "intermediate", ... },
        "chat_history": [ {"role": "user", "content": "..."}, ... ]
    }

    JWT identity supplies user_id automatically.
    """
    try:
        data = request.get_json()
        message = data.get('message')
        profile = data.get('profile', {})
        chat_history = data.get('chat_history', [])

        if not message:
            return jsonify({"error": "Message is required"}), 400

        user_id = get_jwt_identity()

        # 1. Load server-side knowledge state
        ks = KnowledgeStateService.get(user_id)

        req_mode_pref = (
            profile.get('force_tutoring_mode')
            or profile.get('adaptive_preference')
            or (profile.get('conversation_preferences', {}) or {}).get('adaptive_preference')
            or ''
        )
        req_mode_pref = req_mode_pref.strip().lower()
        if req_mode_pref in {'auto', 'automatic'}:
            req_mode_pref = ''
        if req_mode_pref == 'guided':
            req_mode_pref = 'socratic'

        req_tone_pref = (
            profile.get('force_tone')
            or (profile.get('conversation_preferences', {}) or {}).get('preferred_tone')
            or ''
        )
        req_tone_pref = req_tone_pref.strip().lower()
        if req_tone_pref in {'auto', 'automatic'}:
            req_tone_pref = ''
        if req_tone_pref == 'professional':
            req_tone_pref = 'formal'

        req_length_pref = (profile.get('conversation_preferences', {}) or {}).get('preferred_length', '').strip().lower()
        if req_length_pref in {'auto', 'automatic'}:
            req_length_pref = ''
        if profile.get('force_tone', '').strip().lower() == 'concise':
            req_length_pref = 'short'

        conv = ks.get('conversation_preferences', {}) or {}
        changed = False
        if req_mode_pref in {'', 'direct', 'supportive', 'socratic', 'supportive_socratic'} and conv.get('adaptive_preference') != req_mode_pref:
            conv['adaptive_preference'] = req_mode_pref
            changed = True
        if req_tone_pref in {'', 'friendly', 'formal', 'socratic'} and conv.get('preferred_tone') != req_tone_pref:
            conv['preferred_tone'] = req_tone_pref
            changed = True
        if req_length_pref in {'', 'short', 'detailed'} and conv.get('preferred_length') != req_length_pref:
            conv['preferred_length'] = req_length_pref
            changed = True
        if changed:
            ks['conversation_preferences'] = conv
            try:
                KnowledgeStateService.save(user_id, ks)
            except Exception as e:
                logger.warning("Failed to persist tone/mode preferences: %s", e)

        graph_result = langgraph_app.invoke({
            'message':         message,
            'profile':         profile,
            'knowledge_state': ks,
            'chat_history':    chat_history,
            'agent_outputs':   [],
            'next_steps':      [],
            'analysis':        {},
            'final_response':  {},
        })
        result = graph_result.get('final_response', {})
        
        agents_involved = result.get('agents_involved', [])
        result['agent'] = agents_involved[0] if agents_involved else 'general'

        if not result.get('success'):
            return jsonify({"success": False, "error": result.get('error', 'Unknown error')}), 500

        analysis = result.get('analysis', {})
        recs = analysis.get('recommendations', {})

        mode = result.get('tutoring_mode')
        reason = result.get('mode_reason')
        if not mode:
            mode, reason = AdaptiveModeService.decide_mode(
                learner_level=ks.get('skill_level', 'intermediate'),
                uncertainty_markers=analysis.get('message_analysis', {}).get('uncertainty_markers', 0),
                misconception_detected=recs.get('misconception_detected', False),
                emotional_state=recs.get('emotional_state', 'neutral'),
                low_mastery_detected=False,
                user_preference=ks.get('conversation_preferences', {}).get('adaptive_preference'),
            )
        recs['tutoring_mode'] = mode
        recs['mode_reason'] = reason

        # Quiz Inference Logic
        intent = (result.get('generation', {}) or {}).get('intent') or 'general_fallback'
        
        quiz_recommended = False
        quiz_trigger_reason = 'direct_request'
        
        # Check explicit testing intent using the specific LLM function
        msg_lower = message.lower()
        if 'quiz' in msg_lower or 'test' in msg_lower or 'exam' in msg_lower or 'assess' in msg_lower:
            client = Groq(api_key=os.getenv('GROQ_API_KEY'))
            intent_class = classify_intent_with_llm(client, message)
            is_quiz = intent_class.get('intent') == 'testing'
        else:
            is_quiz = result.get('user_intent') == 'testing' or 'quiz_generator' in result.get('nodes_involved', [])
        
        # 1. Direct Request
        if is_quiz:
            quiz_recommended = True
            quiz_trigger_reason = 'direct_request'
        else:
            # 2. Topic Shift (Only recommend quiz if mastery is very low)
            current_topics = analysis.get('topics', [])
            past_topics = ks.get('recent_topics', [])
            if current_topics and past_topics and current_topics[0] not in past_topics:
                mastery = ks.get('topics', {}).get(current_topics[0], {}).get('mastery_level', 0.5)
                # Ensure topic shifts don't randomly give a quiz unless the user really struggles
                if mastery < 0.2:
                    quiz_recommended = True
                    quiz_trigger_reason = 'weak_performance'
            # 4. Repetitive Asking
            elif analysis.get('message_analysis', {}).get('uncertainty_markers', 0) > 3:
                quiz_recommended = True
                quiz_trigger_reason = 'repetitive_asking'

        # Pick up any pending post-quiz explanation context stored by submit_quiz()
        # and inject it so the agent can explain wrong answers this turn.
        pending_quiz_context = ""
        try:
            qcc = Database.get_collection("quiz_chat_context").find_one(
                {"user_id": user_id}, {"_id": 0}
            )
            if qcc:
                pending_quiz_context = qcc.get("context", "")
                # Delete it so it's only injected once
                Database.get_collection("quiz_chat_context").delete_one({"user_id": user_id})
        except Exception as _qcc_err:
            logger.warning("Failed to load quiz_chat_context: %s", _qcc_err)

        # Override LLM text if quiz to avoid leaking quiz text in chat
        if quiz_recommended:
            result['response'] = "I've prepared a tailored Knowledge Check for you! Opening the quiz now..."

        # 3. Update knowledge state from analysis (server-side analytics)
        try:
            KnowledgeStateService.update_from_analysis(user_id, analysis, message)
        except Exception as e:
            logger.warning("Failed to update knowledge state: %s", e)

        # 4. Save interaction to DB (replaces old 'conversations' save)
        try:
            interactions = Database.get_collection('interactions')
            interactions.insert_one({
                "user_id": user_id,
                "user_message": message,
                "ai_response": result['response'],
                "agent": result['agent'],
                "agent_name": result.get('agent_name', ''),
                "tokens_used": result.get('tokens_used', 0),
                "response_time_ms": result.get('response_time_ms', 0),
                "analysis": {
                    "topics": analysis.get('topics', []),
                    "complexity": analysis.get('complexity', 'intermediate'),
                    "question_type": analysis.get('question_type', 'general'),
                    "method": analysis.get('analysis_method', 'keywords'),
                    "mode": mode,
                    "mode_reason": reason,
                    "generation": result.get('generation', {}),
                },
                "tutoring_mode": mode,
                "mode_reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning("Failed to save interaction: %s", e)

        # 5. Bump user stats counter
        try:
            users = Database.get_collection('users')
            users.update_one(
                {"user_id": user_id},
                {"$inc": {"stats.total_conversations": 1, "stats.total_tokens": result.get('tokens_used', 0)}},
            )
        except Exception as e:
            logger.warning("Failed to update user stats: %s", e)

        # 6. Return response + lightweight metadata
        logger.debug(
            "chat_groq return mode=%s reason=%s analysis_mode=%s",
            mode,
            reason,
            analysis.get('recommendations', {}).get('tutoring_mode'),
        )

        dynamic_response = result.get('dynamic_response') or {
            'response_schema_version': 'v1',
            'message_type': 'dynamic_blocks',
            'content_blocks': [
                {
                    'type': 'text',
                    'title': None,
                    'text': result.get('response', ''),
                    'language': None,
                    'rows': [],
                    'items': [],
                }
            ] if result.get('response') else [],
            'metadata': {
                'intent': (result.get('generation', {}) or {}).get('intent') or 'general_fallback',
                'confidence': 0.0,
                'fallback_used': False,
                'fallback_reason': None,
            },
        }

        # Intercept LLM's raw text if it's a quiz to ensure it NEVER leaks chat questions
        final_response = result.get('response', '')
        if quiz_recommended:
            final_response = "I've prepared a tailored Knowledge Check for you! Opening the quiz now..."
            if dynamic_response and 'content_blocks' in dynamic_response:
                dynamic_response['content_blocks'] = [{
                    'type': 'text',
                    'title': None,
                    'text': final_response,
                    'language': None,
                    'rows': [],
                    'items': [],
                }]

        return jsonify({
            "success": True,
            "response": final_response,
            # When quiz_recommended=True the frontend should call POST /api/quiz/generate
            # with {"message": message, "trigger_reason": quiz_trigger_reason}
            # — passing the raw message so topic + count are extracted correctly.
            "quiz_user_message": message if quiz_recommended else None,
            # Injected into the next chat turn's system context after quiz submission
            "pending_quiz_context": pending_quiz_context or None,
            "model": "llama-3.3-70b-versatile",
            "agent": result['agent'],
            "agent_name": result.get('agent_name', ''),
            "tokens_used": result.get('tokens_used', 0),
            "mode": mode,
            "reason": reason,
            "quiz_recommended": quiz_recommended,
            "quiz_trigger_reason": quiz_trigger_reason,
            "analysis": {
                "topics": analysis.get('topics', []),
                "complexity": analysis.get('complexity'),
                "question_type": analysis.get('question_type'),
                "mode": mode,
                "mode_reason": reason,
            },
            "generation": result.get('generation', {}),
            "response_schema_version": dynamic_response.get('response_schema_version', 'v1'),
            "message_type": dynamic_response.get('message_type', 'dynamic_blocks'),
            "content_blocks": dynamic_response.get('content_blocks', []),
            "response_metadata": dynamic_response.get('metadata', {}),
            "dynamic_schema_enabled": bool(Config.DYNAMIC_CHAT_SCHEMA_ENABLED),
        }), 200

    except Exception as e:
        logger.error("Groq chat error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500