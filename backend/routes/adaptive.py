"""
AdaptiveAI - Hybrid Conversation Analysis & Adaptive Engine
Phase 1: Memory & Persistence
Phase 2: Adaptive Intelligence (Hybrid: Keywords + LLM)
Phase 3: Feedback & Testing (Comprehension checks, mastery scoring)
Phase 4: Advanced Features (Knowledge state, misconceptions, Socratic mode)
"""

from flask import Blueprint, request, jsonify
from database import Database
from datetime import datetime
from services.adaptive_mode_service import AdaptiveModeService
import os
import re
import json

adaptive_bp = Blueprint('adaptive', __name__)

# ============================================================
# PHASE 1: HYBRID ANALYSIS ENGINE (Keywords + LLM Fallback)
# ============================================================

TOPIC_PATTERNS = {
    # Data Science
    'data_science': r'\b(data science|data analysis|data engineering|big data|data pipeline|etl|data warehouse)\b',
    'statistics': r'\b(statistics|stat|mean|median|mode|variance|standard deviation|probability|bayesian|hypothesis|p-value|confidence interval|distribution)\b',
    'data_visualization': r'\b(visualization|plot|chart|graph|matplotlib|seaborn|plotly|dashboard|tableau)\b',
    'pandas': r'\b(pandas|dataframe|series|csv|data cleaning|data wrangling|merge|groupby)\b',
    'numpy': r'\b(numpy|array|matrix|linear algebra|vectori[sz]ation)\b',
    'sql': r'\b(sql|query|database|join|select|where|table|mysql|postgresql)\b',
    'eda': r'\b(eda|exploratory data analysis|feature engineering|missing values?|outliers?|imputation)\b',
    
    # Machine Learning
    'machine_learning': r'\b(machine learning|ml|supervised|unsupervised|semi-supervised)\b',
    'regression': r'\b(regression|linear regression|logistic regression|polynomial regression|ridge|lasso|elastic net)\b',
    'classification': r'\b(classification|classifier|decision tree|random forest|svm|support vector|knn|k-nearest|naive bayes|logistic)\b',
    'clustering': r'\b(clustering|k-means|kmeans|dbscan|hierarchical|spectral clustering)\b',
    'ensemble': r'\b(ensemble|bagging|boosting|gradient boost|xgboost|lightgbm|catboost|adaboost|random forest|stacking)\b',
    'model_evaluation': r'\b(accuracy|precision|recall|f1.score|roc|auc|confusion matrix|cross.validation|overfitting|underfitting|bias.variance)\b',
    'feature_engineering': r'\b(feature selection|feature engineering|dimensionality reduction|pca|principal component|t-sne|lda)\b',
    'gradient_descent': r'\b(gradient descent|sgd|learning rate|optimizer|convergence|loss function|cost function)\b',
    'regularization': r'\b(regularization|regulariz|l1|l2|ridge|lasso|dropout|early stopping|weight decay)\b',
    
    # Deep Learning
    'neural_networks': r'\b(neural network|nn|perceptron|mlp|multi.layer|feedforward|deep learning|dl)\b',
    'cnn': r'\b(cnn|convolutional|convolution|pooling|conv2d|image recognition|computer vision|resnet|vgg)\b',
    'rnn': r'\b(rnn|recurrent|lstm|gru|sequence model|time series|bidirectional)\b',
    'transformers': r'\b(transformer|attention|self.attention|multi.head|bert|gpt|encoder.decoder|positional encoding)\b',
    'backpropagation': r'\b(backpropagation|backprop|chain rule|computational graph|gradient flow|vanishing gradient|exploding gradient)\b',
    'activation_functions': r'\b(activation|relu|sigmoid|tanh|softmax|leaky relu|swish|gelu)\b',
    'optimization': r'\b(adam|rmsprop|momentum|optimizer|learning rate schedule|batch size|epoch|mini.batch)\b',
    'transfer_learning': r'\b(transfer learning|pre.trained|fine.tun|pretrained|frozen layers?)\b',
    'gan': r'\b(gan|generative adversarial|generator|discriminator|dcgan|stylegan|wgan)\b',
    'nlp': r'\b(nlp|natural language|tokeniz|embedding|word2vec|glove|sentiment|text classification|named entity|ner)\b',
    'reinforcement_learning': r'\b(reinforcement learning|rl|reward|policy|q-learning|dqn|actor.critic|exploration|exploitation|markov)\b',
    
    # Python / Programming
    'python': r'\b(python|def |class |import |pip |package|module|function|loop|list comprehension|decorator|generator)\b',
    'pytorch': r'\b(pytorch|torch|tensor|autograd|nn\.module|dataloader)\b',
    'tensorflow': r'\b(tensorflow|keras|tf\.|sequential|compile|fit)\b',
    'scikit_learn': r'\b(sklearn|scikit.learn|fit_transform|train_test_split|pipeline)\b',
}

COMPLEXITY_PATTERNS = {
    'beginner': [
        r'\b(what is|what are|explain|define|tell me about|introduction|basics?|simple|beginner|new to)\b',
        r'\b(confused|don\'?t understand|help me understand|i\'?m stuck|lost|struggling)\b',
        r'\b(can you explain|please explain|how does .* work|what does .* mean)\b',
    ],
    'intermediate': [
        r'\b(how to|how do i|implement|build|create|code|example|compare|difference between|vs\.?|versus)\b',
        r'\b(practice|project|apply|use case|when to use|best practice|optimize|improve)\b',
        r'\b(step.by.step|tutorial|guide|walk me through)\b',
    ],
    'advanced': [
        r'\b(why does|prove|derive|mathematical|theoretical|research paper|state.of.the.art)\b',
        r'\b(complex|advanced|in.depth|trade.off|architecture|scalab|distribut|production)\b',
        r'\b(from scratch|under the hood|internal|mechanism|mathematically|formally)\b',
    ]
}

QUESTION_TYPE_PATTERNS = {
    'definition': r'\b(what is|what are|define|meaning of|explain what|tell me about)\b',
    'how_to': r'\b(how to|how do i|how can i|steps to|way to|implement|build|create|code)\b',
    'why': r'\b(why does|why do|why is|why are|reason|cause|purpose of|motivation)\b',
    'comparison': r'\b(difference|compare|vs\.?|versus|better|which one|pros and cons|advantages)\b',
    'debugging': r'\b(error|bug|fix|issue|problem|doesn\'?t work|wrong|fail|crash|exception|traceback)\b',
    'code_request': r'\b(write|code|implement|script|program|function|show me|example code|snippet)\b',
}

MISCONCEPTION_INDICATORS = [
    r'\b(i thought|i assumed|isn\'?t it|wait,? so|but i think|confused because|doesn\'?t .* mean)\b',
    r'\b(that doesn\'?t make sense|contradicts?|but earlier|you said|wrong\?)\b',
    r'\b(so .* is the same as|are .* and .* the same|is it like)\b',
]

UNCERTAINTY_INDICATORS = [
    r'\b(i\'?m not sure|maybe|possibly|i think|i guess|confused|unclear|don\'?t get)\b',
    r'\b(can you clarify|what do you mean|could you explain again|still don\'?t understand)\b',
]


def extract_topics_keywords(message):
    """Phase 1: Fast keyword-based topic extraction"""
    found_topics = []
    msg_lower = message.lower()
    
    for topic, pattern in TOPIC_PATTERNS.items():
        if re.search(pattern, msg_lower, re.IGNORECASE):
            found_topics.append(topic)
    
    return found_topics


def detect_complexity(message):
    """Detect question complexity from keywords"""
    msg_lower = message.lower()
    scores = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
    
    for level, patterns in COMPLEXITY_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, msg_lower, re.IGNORECASE)
            scores[level] += len(matches)
    
    if max(scores.values()) == 0:
        return 'intermediate'  # default
    
    return max(scores, key=scores.get)


def detect_question_type(message):
    """Classify the type of question"""
    msg_lower = message.lower()
    
    for qtype, pattern in QUESTION_TYPE_PATTERNS.items():
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return qtype
    
    return 'general'


def detect_misconception_signals(message):
    """Detect if user shows signs of misconception"""
    msg_lower = message.lower()
    signals = []
    
    for pattern in MISCONCEPTION_INDICATORS:
        matches = re.findall(pattern, msg_lower, re.IGNORECASE)
        signals.extend(matches)
    
    return signals


def detect_uncertainty(message):
    """Detect uncertainty/confusion in user message"""
    msg_lower = message.lower()
    count = 0
    
    for pattern in UNCERTAINTY_INDICATORS:
        count += len(re.findall(pattern, msg_lower, re.IGNORECASE))
    
    return count


def analyze_message_meta(message):
    """Extract metadata about the message"""
    words = message.split()
    return {
        'word_count': len(words),
        'has_code': bool(re.search(r'(```|def |class |import |print\(|for .* in|if .* ==)', message)),
        'has_question_mark': '?' in message,
        'sentence_count': max(1, len(re.split(r'[.!?]+', message))),
        'uncertainty_markers': detect_uncertainty(message),
        'misconception_signals': detect_misconception_signals(message),
    }


def analyze_with_llm(message, profile):
    """Phase 2: LLM fallback for flexible analysis when keywords are insufficient"""
    try:
        from groq import Groq
        
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return None
        
        client = Groq(api_key=api_key)
        
        prompt = f"""Analyze this student message for an adaptive AI tutoring system.

Student message: "{message}"

Current student profile:
- Skill level: {profile.get('skill_level', profile.get('python', 'intermediate'))}
- Strong topics: {profile.get('strong_topics', [])}
- Weak topics: {profile.get('weak_topics', [])}

Return ONLY valid JSON (no markdown):
{{
  "topics": ["topic1"],
  "complexity": "beginner|intermediate|advanced",
  "question_type": "definition|how_to|why|comparison|debugging|code_request|quiz|general",
  "user_intent": "learning|testing",
  "is_misconception": true/false,
  "misconception_detail": "what is wrong and what is correct (or null)",
  "emotional_state": "confident|curious|confused|frustrated|neutral",
  "suggested_approach": "explain_simply|provide_examples|use_analogy|show_code|ask_questions|correct_misconception"
}}
INTENT RULE:
Set question_type="quiz" and user_intent="testing" ONLY when the user directly requests a quiz using imperative language directed at the system (e.g., "give me a quiz", "test me", "quiz me").
If quiz-related phrases appear as part of context or indirect speech (e.g., "I have a test tomorrow", "my teacher will give me a quiz"), set user_intent="learning".
Do NOT trigger quiz intent if the phrase is not a direct request to the system, even if it contains imperative wording in a different context.

Topics should be lowercase with underscores (e.g., neural_networks, gradient_descent).
Be accurate about complexity - don't overestimate."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(completion.choices[0].message.content)
        return result
        
    except Exception as e:
        print(f"LLM analysis fallback error: {e}")
        return None


def should_trigger_comprehension_check(profile):
    """Phase 3: Determine if we should ask a comprehension check question"""
    ba = profile.get('behavioral_analytics', {})
    topics = ba.get('topics_discussed', {})
    
    # Find topics discussed 5+ times without verification
    for topic, data in topics.items():
        # Skip generic fallback topics for comprehension checks
        if topic.lower() in ['general', 'unknown']:
            continue
            
        if isinstance(data, dict):
            count = data.get('count', 0)
            verified = data.get('verified', False)
            if count >= 5 and not verified:
                return topic
    
    return None


def calculate_mastery_score(topic_data):
    """Phase 3: Calculate mastery score (0-1) for a topic"""
    if not isinstance(topic_data, dict):
        return 0.0
    
    count = topic_data.get('count', 0)
    complexity_levels = topic_data.get('complexity_levels', {})
    
    # Handle both list format ["beginner", "intermediate"] and dict format {"beginner": 2}
    if isinstance(complexity_levels, list):
        beginner_q = complexity_levels.count('beginner')
        intermediate_q = complexity_levels.count('intermediate')
        advanced_q = complexity_levels.count('advanced')
    elif isinstance(complexity_levels, dict):
        beginner_q = complexity_levels.get('beginner', 0)
        intermediate_q = complexity_levels.get('intermediate', 0)
        advanced_q = complexity_levels.get('advanced', 0)
    else:
        beginner_q = intermediate_q = advanced_q = 0
    
    if count == 0:
        return 0.0
    
    # Weighted score: advanced questions indicate higher mastery
    weighted = (beginner_q * 0.2 + intermediate_q * 0.5 + advanced_q * 0.9)
    total = beginner_q + intermediate_q + advanced_q
    
    if total == 0:
        return 0.1
    
    base_mastery = weighted / total
    
    # Bonus for asking many questions (familiarity)
    familiarity_bonus = min(0.15, count * 0.015)
    
    # Penalty if mostly beginner questions after many interactions
    if count > 5 and beginner_q / total > 0.7:
        base_mastery *= 0.7  # Still struggling
    
    return min(1.0, round(base_mastery + familiarity_bonus, 2))


def build_recommendations(topics, complexity, question_type, profile, analysis_meta):
    """Phase 2+4: Build profile update recommendations"""
    recommendations = {
        'add_to_strong_topics': [],
        'add_to_weak_topics': [],
        'move_to_strong_topics': [],
        'update_skill_level': None,
        'trigger_socratic_mode': False,
        'misconception_detected': False,
        'misconception_topic': None,
        'comprehension_check_topic': None,
        'tutoring_mode': 'direct',
        'mode_reason': 'stable understanding detected',
    }
    
    strong = profile.get('strong_topics', [])
    weak = profile.get('weak_topics', [])
    ba = profile.get('behavioral_analytics', {})
    topics_discussed = ba.get('topics_discussed', {})
    
    for topic in topics:
        topic_data = topics_discussed.get(topic, {})
        topic_count = topic_data.get('count', 0) if isinstance(topic_data, dict) else 0
        
        if complexity == 'advanced' and topic_count >= 3:
            if topic not in strong:
                recommendations['add_to_strong_topics'].append(topic)
        elif complexity == 'beginner' and topic not in weak and topic not in strong:
            recommendations['add_to_weak_topics'].append(topic)
        elif complexity == 'intermediate' and topic not in weak and topic not in strong:
            recommendations['add_to_weak_topics'].append(topic)
    
    # Move from weak to strong if complexity progressed
    for topic in topics:
        if topic in weak:
            topic_data = topics_discussed.get(topic, {})
            if isinstance(topic_data, dict):
                mastery = calculate_mastery_score(topic_data)
                if mastery >= 0.65:
                    recommendations['move_to_strong_topics'].append(topic)
    
    # Skill level recommendation
    complexity_dist = ba.get('complexity_distribution', {})
    total = sum(complexity_dist.values()) if complexity_dist else 0
    
    if total >= 10:
        advanced_ratio = complexity_dist.get('advanced', 0) / total
        beginner_ratio = complexity_dist.get('beginner', 0) / total
        current_level = profile.get('skill_level', profile.get('python', 'Intermediate'))
        
        if advanced_ratio > 0.5 and current_level != 'Advanced':
            recommendations['update_skill_level'] = 'Advanced'
        elif beginner_ratio > 0.6 and current_level != 'Beginner':
            recommendations['update_skill_level'] = 'Beginner'
        elif advanced_ratio < 0.5 and beginner_ratio < 0.5 and current_level != 'Intermediate':
            recommendations['update_skill_level'] = 'Intermediate'
    
    # Misconception detection
    misconception_signals = analysis_meta.get('misconception_signals', [])
    if len(misconception_signals) > 0:
        recommendations['misconception_detected'] = True
        recommendations['misconception_topic'] = topics[0] if topics else 'general'
        recommendations['trigger_socratic_mode'] = True
    
    # Uncertainty → Socratic mode
    if analysis_meta.get('uncertainty_markers', 0) >= 2:
        recommendations['trigger_socratic_mode'] = True
    
    # Comprehension check trigger
    check_topic = should_trigger_comprehension_check(profile)
    if check_topic:
        recommendations['comprehension_check_topic'] = check_topic

    # Centralized tutoring mode decision
    low_mastery = False
    for topic in topics:
        topic_data = topics_discussed.get(topic, {})
        if isinstance(topic_data, dict) and topic_data.get('count', 0) >= 2:
            if calculate_mastery_score(topic_data) < 0.45:
                low_mastery = True
                break

    mode, reason = AdaptiveModeService.decide_mode(
        learner_level=profile.get('skill_level', profile.get('python', 'intermediate')),
        uncertainty_markers=analysis_meta.get('uncertainty_markers', 0),
        misconception_detected=recommendations.get('misconception_detected', False),
        emotional_state=recommendations.get('emotional_state', 'neutral'),
        low_mastery_detected=low_mastery,
        user_preference=profile.get('conversation_preferences', {}).get('adaptive_preference'),
    )
    recommendations['tutoring_mode'] = mode
    recommendations['mode_reason'] = reason
    recommendations['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)
    
    return recommendations


# ============================================================
# API ENDPOINT: Analyze Conversation
# ============================================================

@adaptive_bp.route('/analyze', methods=['POST'])
def analyze_conversation():
    """
    Hybrid analysis: Fast keywords first, LLM fallback if needed.
    Returns topics, complexity, question type, recommendations.
    """
    data = request.get_json()
    message = data.get('message', '')
    profile = data.get('profile', {})
    
    if not message:
        return jsonify({'success': False, 'error': 'No message provided'}), 400
    
    # === PHASE 1: Fast keyword analysis ===
    topics_kw = extract_topics_keywords(message)
    complexity_kw = detect_complexity(message)
    question_type_kw = detect_question_type(message)
    analysis_meta = analyze_message_meta(message)
    
    analysis_method = 'keywords'
    topics = topics_kw
    complexity = complexity_kw
    question_type = question_type_kw
    llm_data = None
    
    # === PHASE 2: LLM fallback when keywords aren't enough ===
    word_count = analysis_meta.get('word_count', 0)
    should_use_llm = (
        len(topics_kw) == 0 or  # No topics detected
        (word_count > 50 and len(topics_kw) < 2) or  # Long message, few topics
        len(analysis_meta.get('misconception_signals', [])) > 0  # Possible misconception
    )
    
    if should_use_llm:
        llm_result = analyze_with_llm(message, profile)
        if llm_result:
            analysis_method = 'hybrid'
            llm_data = llm_result
            
            # Merge: keyword topics + LLM topics (deduplicated)
            llm_topics = llm_result.get('topics', [])
            topics = list(set(topics_kw + llm_topics))
            
            # LLM is more nuanced for complexity when available
            complexity = llm_result.get('complexity', complexity_kw)
            question_type = llm_result.get('question_type', question_type_kw)
    
    # === PHASE 3 + 4: Build recommendations ===
    recommendations = build_recommendations(topics, complexity, question_type, profile, analysis_meta)
    
    # Add LLM-specific insights
    if llm_data:
        recommendations['emotional_state'] = llm_data.get('emotional_state', 'neutral')
        recommendations['suggested_approach'] = llm_data.get('suggested_approach', 'explain_simply')
        if llm_data.get('is_misconception'):
            recommendations['misconception_detected'] = True
            recommendations['misconception_detail'] = llm_data.get('misconception_detail')
            recommendations['trigger_socratic_mode'] = True

        # Re-evaluate mode after LLM signals are merged.
        mode, reason = AdaptiveModeService.decide_mode(
            learner_level=profile.get('skill_level', profile.get('python', 'intermediate')),
            uncertainty_markers=analysis_meta.get('uncertainty_markers', 0),
            misconception_detected=recommendations.get('misconception_detected', False),
            emotional_state=recommendations.get('emotional_state', 'neutral'),
            low_mastery_detected=False,
            user_preference=profile.get('conversation_preferences', {}).get('adaptive_preference'),
        )
        recommendations['tutoring_mode'] = mode
        recommendations['mode_reason'] = reason
        recommendations['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)
    
    return jsonify({
        'success': True,
        'analysis': {
            'topics': topics,
            'complexity': complexity,
            'question_type': question_type,
            'analysis_method': analysis_method,
            'message_analysis': analysis_meta,
            'recommendations': recommendations,
        }
    }), 200


# ============================================================
# PHASE 1: Conversation Memory & Preferences
# ============================================================

@adaptive_bp.route('/preferences/save', methods=['POST'])
def save_preferences():
    """Save conversation style preferences extracted from chat"""
    data = request.get_json()
    user_id = data.get('user_id')
    preferences = data.get('preferences', {})
    
    if not user_id:
        return jsonify({'success': False, 'error': 'No user_id'}), 400
    
    try:
        prefs_collection = Database.get_collection('user_preferences')
        prefs_collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'preferences': preferences,
                'updated_at': datetime.utcnow().isoformat()
            }},
            upsert=True
        )
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@adaptive_bp.route('/preferences/load/<user_id>', methods=['GET'])
def load_preferences(user_id):
    """Load saved conversation preferences"""
    try:
        prefs_collection = Database.get_collection('user_preferences')
        prefs = prefs_collection.find_one({'user_id': user_id}, {'_id': 0})
        return jsonify({'success': True, 'preferences': prefs or {}}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PHASE 4: Knowledge State & Misconception Tracking
# ============================================================

@adaptive_bp.route('/knowledge/save', methods=['POST'])
def save_knowledge_state():
    """Save user's knowledge state and misconceptions to DB"""
    data = request.get_json()
    user_id = data.get('user_id')
    knowledge_state = data.get('knowledge_state', {})
    misconceptions = data.get('misconceptions', {})
    
    if not user_id:
        return jsonify({'success': False, 'error': 'No user_id'}), 400
    
    try:
        ks_collection = Database.get_collection('knowledge_states')
        ks_collection.update_one(
            {'user_id': user_id},
            {'$set': {
                'user_id': user_id,
                'knowledge_state': knowledge_state,
                'misconceptions': misconceptions,
                'updated_at': datetime.utcnow().isoformat()
            }},
            upsert=True
        )
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@adaptive_bp.route('/knowledge/load/<user_id>', methods=['GET'])
def load_knowledge_state(user_id):
    """Load user's knowledge state and misconceptions"""
    try:
        ks_collection = Database.get_collection('knowledge_states')
        ks = ks_collection.find_one({'user_id': user_id}, {'_id': 0})
        return jsonify({
            'success': True,
            'knowledge_state': ks.get('knowledge_state', {}) if ks else {},
            'misconceptions': ks.get('misconceptions', {}) if ks else {}
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PHASE 3: Build Enriched Prompt for AI Responses
# ============================================================

@adaptive_bp.route('/build-prompt', methods=['POST'])
def build_enriched_prompt():
    """
    Build an enriched system prompt using full profile data.
    This is what makes the AI ACTUALLY adapt its responses.
    """
    data = request.get_json()
    profile = data.get('profile', {})
    analysis = data.get('analysis', {})
    
    ba = profile.get('behavioral_analytics', {})
    topics_discussed = ba.get('topics_discussed', {})
    complexity_dist = ba.get('complexity_distribution', {})
    misconceptions = profile.get('misconceptions', {})
    knowledge_state = profile.get('knowledge_state', {})
    conversation_prefs = profile.get('conversation_preferences', {})
    
    # Determine effective skill level from rolling average
    total_q = sum(complexity_dist.values()) if complexity_dist else 0
    if total_q >= 5:
        adv = complexity_dist.get('advanced', 0) / total_q
        beg = complexity_dist.get('beginner', 0) / total_q
        if adv > 0.5:
            effective_level = 'Advanced'
        elif beg > 0.5:
            effective_level = 'Beginner'
        else:
            effective_level = 'Intermediate'
    else:
        effective_level = profile.get('skill_level', profile.get('python', 'Intermediate'))
    
    # Build strong/weak topics summary
    strong = profile.get('strong_topics', [])
    weak = profile.get('weak_topics', [])
    
    # Build mastery map
    mastery_summary = []
    for topic, tdata in topics_discussed.items():
        if isinstance(tdata, dict) and tdata.get('count', 0) >= 2:
            mastery = calculate_mastery_score(tdata)
            mastery_summary.append(f"  - {topic}: {mastery:.0%} mastery ({tdata.get('count', 0)} interactions)")
    
    # Active misconceptions
    active_misconceptions = []
    for topic, mdata in misconceptions.items():
        if isinstance(mdata, dict) and not mdata.get('corrected', False):
            active_misconceptions.append(
                f"  - {topic}: {mdata.get('detail', 'unclear understanding')}"
            )
    
    # Conversation preferences
    preferred_style = conversation_prefs.get('explanation_style', '')
    preferred_examples = conversation_prefs.get('prefers_examples', False)
    preferred_code = conversation_prefs.get('prefers_code', False)
    preferred_analogies = conversation_prefs.get('prefers_analogies', False)
    
    # Current analysis context
    current_topics = analysis.get('topics', [])
    current_complexity = analysis.get('complexity', 'intermediate')
    current_type = analysis.get('question_type', 'general')
    recommendations = analysis.get('recommendations', {})
    
    # Build the enriched prompt
    prompt_sections = []
    
    prompt_sections.append(f"""=== LEARNER INTELLIGENCE PROFILE ===
Name: {profile.get('name', 'Student')}
Effective Skill Level: {effective_level} (based on {total_q} interactions)
Learning Style: {profile.get('tone', 'Friendly')}
Background: {profile.get('major', 'Computer Science')}
Conversations: {profile.get('conversation_count', 0)}""")
    
    if strong:
        prompt_sections.append(f"\n✅ MASTERED TOPICS: {', '.join(strong)}")
    if weak:
        prompt_sections.append(f"⚠️ LEARNING TOPICS (needs simpler explanations): {', '.join(weak)}")
    
    if mastery_summary:
        prompt_sections.append("\n📊 TOPIC MASTERY MAP:\n" + '\n'.join(mastery_summary))
    
    if active_misconceptions:
        prompt_sections.append(
            "\n🚨 ACTIVE MISCONCEPTIONS (correct these gently when relevant):\n" + 
            '\n'.join(active_misconceptions)
        )
    
    # Adaptation instructions based on analysis
    adapt_instructions = []
    
    if recommendations.get('trigger_socratic_mode'):
        adapt_instructions.append(
            "🔄 SOCRATIC MODE: Student shows confusion/misconception. "
            "First explain the concept clearly, THEN ask probing questions. "
            "Example: '...does that make sense? What do you think happens when...?'"
        )
    
    if recommendations.get('emotional_state') == 'frustrated':
        adapt_instructions.append(
            "❤️ SUPPORT MODE: Student seems frustrated. Be extra encouraging, "
            "break the concept into tiny steps, use simple analogies."
        )
    elif recommendations.get('emotional_state') == 'curious':
        adapt_instructions.append(
            "🚀 EXPLORATION MODE: Student is curious! Go deeper, share interesting facts, "
            "suggest related topics to explore."
        )
    
    if current_complexity == 'beginner' and effective_level in ['Intermediate', 'Advanced']:
        adapt_instructions.append(
            "📉 DIFFICULTY MISMATCH: Student is asking a basic question despite higher skill level. "
            "They may be reviewing or have a gap. Explain clearly but don't over-simplify."
        )
    elif current_complexity == 'advanced' and effective_level == 'Beginner':
        adapt_instructions.append(
            "📈 STRETCH QUESTION: Beginner asking an advanced question. "
            "Scaffold: Start with prerequisites, then build up to the answer."
        )
    
    # Style preferences
    style_prefs = []
    if preferred_examples:
        style_prefs.append("real-world examples")
    if preferred_code:
        style_prefs.append("code snippets")
    if preferred_analogies:
        style_prefs.append("analogies")
    if preferred_style:
        style_prefs.append(preferred_style)
    
    if style_prefs:
        adapt_instructions.append(f"📝 PREFERRED STYLE: Include {', '.join(style_prefs)} in your response.")
    
    if adapt_instructions:
        prompt_sections.append("\n=== ADAPTATION INSTRUCTIONS ===\n" + '\n'.join(adapt_instructions))
    
    # Comprehension check
    check_topic = recommendations.get('comprehension_check_topic')
    if check_topic:
        prompt_sections.append(
            f"\n💡 COMPREHENSION CHECK: After answering, ask a quick check question about '{check_topic}' "
            f"to verify understanding. Example: 'Quick check: Can you explain {check_topic} in your own words?' "
            f"(NOTE: If the user explicitly asks NOT to be asked questions, skip this check.)"
        )
    
    enriched_prompt = '\n'.join(prompt_sections)
    
    return jsonify({
        'success': True,
        'enriched_prompt': enriched_prompt,
        'effective_level': effective_level,
        'adaptations': {
            'socratic_mode': recommendations.get('trigger_socratic_mode', False),
            'emotional_state': recommendations.get('emotional_state', 'neutral'),
            'suggested_approach': recommendations.get('suggested_approach', 'explain_simply'),
            'comprehension_check': check_topic,
        }
    }), 200
