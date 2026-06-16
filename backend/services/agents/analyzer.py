"""
Message analysis: topic extraction, complexity detection,
misconception detection, tutoring mode recommendation.
No circular imports — does NOT import from services.agents.
"""

import re
import json
import logging
from services.adaptive_mode_service import AdaptiveModeService

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# Patterns
# ────────────────────────────────────────────────────────────
_TOPIC_PATTERNS = {
    'data_science':          r'\b(data science|data analysis|big data|data pipeline|etl|data warehouse)\b',
    'statistics':            r'\b(statistics|mean|median|mode|variance|standard deviation|probability|bayesian|hypothesis|p-value|distribution)\b',
    'data_visualization':    r'\b(visualization|plot|chart|graph|matplotlib|seaborn|plotly|dashboard)\b',
    'pandas':                r'\b(pandas|dataframe|series|csv|data cleaning|data wrangling|merge|groupby)\b',
    'numpy':                 r'\b(numpy|array|matrix|linear algebra|vectori[sz]ation)\b',
    'sql':                   r'\b(sql|query|database|join|select|where|table|mysql|postgresql)\b',
    'eda':                   r'\b(eda|exploratory data analysis|feature engineering|missing values?|outliers?|imputation)\b',
    'machine_learning':      r'\b(machine learning|ml|supervised|unsupervised|semi-supervised)\b',
    'regression':            r'\b(regression|linear regression|logistic regression|ridge|lasso|elastic net)\b',
    'classification':        r'\b(classification|classifier|decision tree|random forest|svm|knn|naive bayes)\b',
    'clustering':            r'\b(clustering|k-means|kmeans|dbscan|hierarchical)\b',
    'ensemble':              r'\b(ensemble|bagging|boosting|gradient boost|xgboost|lightgbm|catboost|adaboost|stacking)\b',
    'model_evaluation':      r'\b(accuracy|precision|recall|f1.score|roc|auc|confusion matrix|cross.validation|overfitting|underfitting)\b',
    'gradient_descent':      r'\b(gradient descent|sgd|learning rate|optimizer|convergence|loss function|cost function)\b',
    'regularization':        r'\b(regularization|l1|l2|ridge|lasso|dropout|early stopping|weight decay)\b',
    'feature_engineering':   r'\b(feature selection|feature engineering|dimensionality reduction|pca|principal component|t-sne|lda)\b',
    'neural_networks':       r'\b(neural networks?|nn|perceptron|mlp|feedforward|deep learning|dl)\b',
    'cnn':                   r'\b(cnn|convolutional|convolution|pooling|image recognition|computer vision|resnet|vgg)\b',
    'rnn':                   r'\b(rnn|recurrent|lstm|gru|sequence model|time series|bidirectional)\b',
    'transformers':          r'\b(transformer|attention|self.attention|bert|gpt|encoder.decoder|positional encoding)\b',
    'backpropagation':       r'\b(backpropagation|backprop|chain rule|vanishing gradient|exploding gradient)\b',
    'activation_functions':  r'\b(activation|relu|sigmoid|tanh|softmax|leaky relu|swish|gelu)\b',
    'transfer_learning':     r'\b(transfer learning|pre.trained|fine.tun|pretrained|frozen layers?)\b',
    'gan':                   r'\b(gan|generative adversarial|generator|discriminator|dcgan|stylegan)\b',
    'nlp':                   r'\b(nlp|natural language|tokeniz|embedding|word2vec|glove|sentiment|text classification)\b',
    'reinforcement_learning': r'\b(reinforcement learning|rl|reward|policy|q-learning|dqn|actor.critic)\b',
    'python':                r'\b(python|def |class |import |pip |function|decorator|generator)\b',
    'pytorch':               r'\b(pytorch|torch|tensor|autograd|nn\.module|dataloader)\b',
    'tensorflow':            r'\b(tensorflow|keras|tf\.|sequential|compile|fit)\b',
    'scikit_learn':          r'\b(sklearn|scikit.learn|fit_transform|train_test_split|pipeline)\b',
}

_COMPLEXITY_PATTERNS = {
    'beginner': [
        r'\b(what is|what are|explain|define|tell me about|basics?|beginner|new to)\b',
        r'\b(confused|don\'?t understand|help me understand|i\'?m stuck)\b',
    ],
    'intermediate': [
        r'\b(how to|implement|build|create|compare|difference between|vs\.?|versus)\b',
        r'\b(step.by.step|tutorial|guide|when to use|best practice)\b',
    ],
    'advanced': [
        r'\b(why does|prove|derive|mathematical|theoretical|research paper|state.of.the.art)\b',
        r'\b(from scratch|under the hood|internal|mechanism|formally)\b',
    ],
}

_QUESTION_TYPE_PATTERNS = {
    'definition':   r'\b(what is|what are|define|meaning of|explain what|tell me about)\b',
    'how_to':       r'\b(how to|how do i|how can i|steps to|implement|build|create|code)\b',
    'why':          r'\b(why does|why do|why is|reason|cause|purpose of)\b',
    'comparison':   r'\b(difference|compare|vs\.?|versus|better|which one|pros and cons)\b',
    'debugging':    r'\b(error|bug|fix|issue|doesn\'?t work|wrong|fail|crash|exception)\b',
    'code_request': r'\b(write|code|coding|implement|script|program|function|show me|example code|code example|coding example|snippet|sample code|hello world|boilerplate)\b',
}

_MISCONCEPTION_INDICATORS = [
    r'\b(i thought|i assumed|isn\'?t it|wait,? so|but i think|confused because)\b',
    r'\b(that doesn\'?t make sense|contradicts?|but earlier|you said)\b',
    r'\b(is basically|is essentially|is just|is the same as|is another word for)\b',
    r'\b(always|never|cannot|impossible|only way|must be|has to be)\b',
    r'\b(so basically|so that means|so it\'?s|meaning that|which means)\b',
    r'\b(the reason is|because .+ is|since .+ is|everyone knows)\b',
]

_ASSERTION_PATTERNS = [
    r'^(?:so |okay,? so |right,? so )?\w.+ (?:is|are|means|works? by|uses?) ',
    r'\b(?:I know|I believe|I read|I learned|from what I understand)\b',
]

_UNCERTAINTY_INDICATORS = [
    r'\b(i\'?m not sure|maybe|possibly|i think|confused|unclear|don\'?t get)\b',
    r'\b(can you clarify|could you explain again|still don\'?t understand)\b',
]


# ────────────────────────────────────────────────────────────
# Public analysis functions
# ────────────────────────────────────────────────────────────
def extract_topics(message: str) -> list:
    lower = message.lower()
    return [t for t, p in _TOPIC_PATTERNS.items() if re.search(p, lower, re.I)]


def detect_complexity(message: str) -> str:
    lower = message.lower()
    scores = {'beginner': 0, 'intermediate': 0, 'advanced': 0}
    for lvl, patterns in _COMPLEXITY_PATTERNS.items():
        for p in patterns:
            scores[lvl] += len(re.findall(p, lower, re.I))
    max_score = max(scores.values())
    if max_score == 0:
        return 'intermediate'
    # Prefer advanced on ties so mathematically dense prompts are not
    # down-classified when they also contain wording like "when to use".
    tied = [lvl for lvl, score in scores.items() if score == max_score]
    for preferred in ('advanced', 'intermediate', 'beginner'):
        if preferred in tied:
            return preferred
    return 'intermediate'


def detect_question_type(message: str) -> str:
    lower = message.lower()
    for qt, p in _QUESTION_TYPE_PATTERNS.items():
        if re.search(p, lower, re.I):
            return qt
    return 'general'


def message_meta(message: str) -> dict:
    words = message.split()
    misconceptions = []
    for p in _MISCONCEPTION_INDICATORS:
        misconceptions.extend(re.findall(p, message, re.I))
    uncertainty = 0
    for p in _UNCERTAINTY_INDICATORS:
        uncertainty += len(re.findall(p, message, re.I))
    is_assertion = (
        '?' not in message
        and any(re.search(p, message, re.I) for p in _ASSERTION_PATTERNS)
    )
    return {
        'word_count':          len(words),
        'has_code':            bool(re.search(r'(```|def |class |import |print\(|for .* in)', message)),
        'has_question_mark':   '?' in message,
        'is_assertion':        is_assertion,
        'uncertainty_markers': uncertainty,
        'misconception_signals': misconceptions,
    }


def build_recommendations(topics: list, complexity: str, qtype: str, ks: dict, meta: dict) -> dict:
    """Build profile-update recommendations from analysis."""
    recs = {
        'add_to_strong_topics':    [],
        'add_to_weak_topics':      [],
        'move_to_strong_topics':   [],
        'update_skill_level':      None,
        'trigger_socratic_mode':   False,
        'misconception_detected':  False,
        'misconception_topic':     None,
        'misconception_detail':    None,
        'comprehension_check_topic': None,
        'emotional_state':         'neutral',
        'suggested_approach':      'explain_simply',
        'tutoring_mode':           'direct',
        'mode_reason':             'stable understanding detected',
    }

    strong     = ks.get('strong_topics', [])
    weak       = ks.get('weak_topics', [])
    topics_map = ks.get('topics', {})

    for t in topics:
        td  = topics_map.get(t, {})
        cnt = td.get('count', 0) if isinstance(td, dict) else 0
        mentions_after_this_turn = cnt + 1
        if complexity == 'advanced' and mentions_after_this_turn >= 3 and t not in strong:
            recs['add_to_strong_topics'].append(t)
        elif complexity in ('beginner', 'intermediate') and t not in weak and t not in strong:
            recs['add_to_weak_topics'].append(t)

    for t in topics:
        if t in weak:
            td = topics_map.get(t, {})
            if isinstance(td, dict) and td.get('mastery_level', 0) >= 0.65:
                recs['move_to_strong_topics'].append(t)

    # skill level
    ba    = ks.get('behavioral', {})
    cd    = ba.get('complexity_distribution', {})
    total = sum(cd.values()) if cd else 0
    if total >= 10:
        adv_r = cd.get('advanced', 0) / total
        beg_r = cd.get('beginner', 0) / total
        cur   = ks.get('skill_level', 'Intermediate')
        if adv_r > 0.5 and cur != 'Advanced':
            recs['update_skill_level'] = 'Advanced'
        elif beg_r > 0.6 and cur != 'Beginner':
            recs['update_skill_level'] = 'Beginner'
        elif adv_r < 0.5 and beg_r < 0.5 and cur != 'Intermediate':
            recs['update_skill_level'] = 'Intermediate'

    # misconception / socratic
    if len(meta.get('misconception_signals', [])) > 0:
        recs['misconception_detected'] = True
        recs['misconception_topic']    = topics[0] if topics else 'general'
        recs['trigger_socratic_mode']  = True

    uncertainty = meta.get('uncertainty_markers', 0)
    if uncertainty >= 1 and topics:
        recs['trigger_socratic_mode'] = True
        if not recs.get('misconception_detected'):
            recs['misconception_detected'] = True
            recs['misconception_topic']    = topics[0]
            recs['misconception_detail']   = (
                f'Student expressed confusion/uncertainty about {topics[0]}'
            )
    elif uncertainty >= 2:
        recs['trigger_socratic_mode'] = True

    # Repeated-topic confusion
    for t in topics:
        td = topics_map.get(t, {})
        if isinstance(td, dict):
            count         = td.get('count', 0)
            cl            = td.get('complexity_levels', {})
            beginner_count = cl.get('beginner', 0) if isinstance(cl, dict) else 0
            total_cl      = sum(cl.values()) if isinstance(cl, dict) else 0
            if count >= 3 and total_cl > 0 and beginner_count / total_cl > 0.5:
                recs['trigger_socratic_mode'] = True
                if not recs.get('misconception_detected'):
                    recs['misconception_detected'] = True
                    recs['misconception_topic']    = t
                    recs['misconception_detail']   = (
                        f'Student has asked about {t} {count} times at beginner level — '
                        f'possible persistent misunderstanding'
                    )
                break

    # comprehension check - only for topics relevant to the current message
    for t in topics:
        if t.lower() in ['general', 'unknown']:
            continue
        td = topics_map.get(t, {})
        if isinstance(td, dict) and td.get('count', 0) >= 5 and not td.get('verified'):
            recs['comprehension_check_topic'] = t
            break

    low_mastery = AdaptiveModeService.has_low_mastery(topics_map, topics)
    mode, reason = AdaptiveModeService.decide_mode(
        learner_level=ks.get('skill_level', 'intermediate'),
        uncertainty_markers=meta.get('uncertainty_markers', 0),
        misconception_detected=recs.get('misconception_detected', False),
        emotional_state=recs.get('emotional_state', 'neutral'),
        low_mastery_detected=low_mastery,
        user_preference=ks.get('conversation_preferences', {}).get('adaptive_preference'),
    )
    recs['tutoring_mode']        = mode
    recs['mode_reason']          = reason
    recs['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)

    return recs


def finalize_tutoring_mode(recs: dict, knowledge_state: dict, topics: list, meta: dict) -> dict:
    """Final pass on tutoring mode after LLM enrichment."""
    topics_map  = knowledge_state.get('topics', {})
    low_mastery = AdaptiveModeService.has_low_mastery(topics_map, topics)
    mode, reason = AdaptiveModeService.decide_mode(
        learner_level=knowledge_state.get('skill_level', 'intermediate'),
        uncertainty_markers=meta.get('uncertainty_markers', 0),
        misconception_detected=recs.get('misconception_detected', False),
        emotional_state=recs.get('emotional_state', 'neutral'),
        low_mastery_detected=low_mastery,
        user_preference=knowledge_state.get('conversation_preferences', {}).get('adaptive_preference'),
    )
    recs['tutoring_mode']        = mode
    recs['mode_reason']          = reason
    recs['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)
    return recs


def analyze_with_llm(client, message: str, profile: dict) -> dict | None:
    """Use Groq LLM for nuanced analysis when keywords aren't enough."""
    try:
        prompt = f"""Analyze this student message for an adaptive AI tutoring system.

Student message: "{message}"

Current skill level: {profile.get('skill_level', 'intermediate')}
Strong topics: {profile.get('strong_topics', [])}
Weak topics: {profile.get('weak_topics', [])}

MISCONCEPTION DETECTION (critical):
Set is_misconception=true if the student:
- States something factually incorrect about a technical concept
- Confuses two different concepts (e.g. "overfitting is the same as high variance")
- Makes absolute/wrong claims ("gradient descent always converges", "CNNs only work for images")
- Shows a fundamental misunderstanding even in how they phrase their question
If is_misconception is true, misconception_detail MUST explain what is wrong and what the correct understanding is.

Return ONLY valid JSON (no markdown):
{{
  "topics": ["topic1"],
  "complexity": "beginner|intermediate|advanced",
  "question_type": "definition|how_to|why|comparison|debugging|code_request|general",
  "is_misconception": true/false,
  "misconception_detail": "what is wrong and what is correct (or null)",
  "emotional_state": "confident|curious|confused|frustrated|neutral",
  "suggested_approach": "explain_simply|provide_examples|use_analogy|show_code|ask_questions|correct_misconception"
}}

Topics should be lowercase with underscores (e.g., neural_networks, gradient_descent)."""

        completion = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.1,
            max_tokens=300,
            response_format={'type': 'json_object'},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        logger.warning('LLM analysis fallback error: %s', e)
        return None