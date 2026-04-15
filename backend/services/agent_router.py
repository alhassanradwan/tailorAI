"""
AdaptiveAI — Deep Agent Router (pre-LangChain)
Single entry point for:
  1. Topic routing → DS / ML / DL agent
  2. Personalized system prompt construction
  3. Groq API call
  4. Inline analysis (no extra HTTP round-trip)

When LangChain is added later, replace the internals of `generate()`
without changing the interface.
"""

import os
import re
import json
import time
import logging
from datetime import datetime
from groq import Groq
from config import Config
from services.adaptive_mode_service import AdaptiveModeService
from services.langchain_analyzer import LangChainAnalyzer
from services.langchain_generator import LangChainGenerator
from services.langchain_prompts import select_output_plan
from services.langchain_schemas import build_text_only_dynamic_envelope

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────
# Agent definitions
# ────────────────────────────────────────────────────────────
AGENTS = {
    'data_science': {
        'label': 'Data Science',
        'system': (
            "You are an expert Data Science tutor specializing in EDA, "
            "data cleaning, statistics, visualization (Matplotlib, Seaborn, Plotly), "
            "Pandas, NumPy, and feature engineering. "
            "You are the SUPERVISOR agent that oversees the learning path. "
            "Always provide practical Python code examples when relevant."
        ),
        'keywords': [
            'data', 'pandas', 'numpy', 'visualization', 'eda', 'exploratory',
            'statistics', 'correlation', 'distribution', 'cleaning', 'preprocessing',
            'matplotlib', 'seaborn', 'plotly', 'csv', 'dataframe', 'analysis',
            'sql', 'query', 'database', 'join', 'missing values', 'outlier',
        ],
    },
    'machine_learning': {
        'label': 'Machine Learning',
        'system': (
            "You are an expert Machine Learning tutor specializing in "
            "supervised/unsupervised learning, model evaluation, feature engineering, "
            "Scikit-learn, ensemble methods, and classical ML algorithms. "
            "Always explain the intuition before diving into mathematics."
        ),
        'keywords': [
            'machine learning', 'supervised', 'unsupervised', 'regression',
            'classification', 'clustering', 'random forest', 'decision tree',
            'svm', 'knn', 'k-means', 'pca', 'feature', 'training', 'testing',
            'cross-validation', 'overfitting', 'underfitting', 'scikit', 'sklearn',
            'ensemble', 'boosting', 'bagging', 'xgboost', 'lightgbm',
        ],
    },
    'deep_learning': {
        'label': 'Deep Learning',
        'system': (
            "You are an expert Deep Learning tutor specializing in neural networks, "
            "backpropagation, CNNs, RNNs/LSTMs, Transformers, TensorFlow, PyTorch, "
            "transfer learning, and modern architectures (ResNet, BERT, GPT). "
            "Balance mathematical rigor with practical intuition."
        ),
        'keywords': [
            'deep learning', 'neural network', 'cnn', 'rnn', 'lstm', 'transformer',
            'backpropagation', 'gradient descent', 'activation', 'relu', 'sigmoid',
            'tensorflow', 'pytorch', 'keras', 'epoch', 'batch', 'dropout', 'layer',
            'convolution', 'attention', 'bert', 'gpt', 'embedding', 'gan',
        ],
    },
}


# ────────────────────────────────────────────────────────────
# Lightweight keyword analysis (ported from adaptive.py)
# ────────────────────────────────────────────────────────────
_TOPIC_PATTERNS = {
    'data_science': r'\b(data science|data analysis|big data|data pipeline|etl|data warehouse)\b',
    'statistics': r'\b(statistics|mean|median|mode|variance|standard deviation|probability|bayesian|hypothesis|p-value|distribution)\b',
    'data_visualization': r'\b(visualization|plot|chart|graph|matplotlib|seaborn|plotly|dashboard)\b',
    'pandas': r'\b(pandas|dataframe|series|csv|data cleaning|data wrangling|merge|groupby)\b',
    'numpy': r'\b(numpy|array|matrix|linear algebra|vectori[sz]ation)\b',
    'sql': r'\b(sql|query|database|join|select|where|table|mysql|postgresql)\b',
    'eda': r'\b(eda|exploratory data analysis|feature engineering|missing values?|outliers?|imputation)\b',
    'machine_learning': r'\b(machine learning|ml|supervised|unsupervised|semi-supervised)\b',
    'regression': r'\b(regression|linear regression|logistic regression|ridge|lasso|elastic net)\b',
    'classification': r'\b(classification|classifier|decision tree|random forest|svm|knn|naive bayes)\b',
    'clustering': r'\b(clustering|k-means|kmeans|dbscan|hierarchical)\b',
    'ensemble': r'\b(ensemble|bagging|boosting|gradient boost|xgboost|lightgbm|catboost|adaboost|stacking)\b',
    'model_evaluation': r'\b(accuracy|precision|recall|f1.score|roc|auc|confusion matrix|cross.validation|overfitting|underfitting)\b',
    'gradient_descent': r'\b(gradient descent|sgd|learning rate|optimizer|convergence|loss function|cost function)\b',
    'regularization': r'\b(regularization|l1|l2|ridge|lasso|dropout|early stopping|weight decay)\b',
    'feature_engineering': r'\b(feature selection|feature engineering|dimensionality reduction|pca|principal component|t-sne|lda)\b',
    'neural_networks': r'\b(neural networks?|nn|perceptron|mlp|feedforward|deep learning|dl)\b',
    'cnn': r'\b(cnn|convolutional|convolution|pooling|image recognition|computer vision|resnet|vgg)\b',
    'rnn': r'\b(rnn|recurrent|lstm|gru|sequence model|time series|bidirectional)\b',
    'transformers': r'\b(transformer|attention|self.attention|bert|gpt|encoder.decoder|positional encoding)\b',
    'backpropagation': r'\b(backpropagation|backprop|chain rule|vanishing gradient|exploding gradient)\b',
    'activation_functions': r'\b(activation|relu|sigmoid|tanh|softmax|leaky relu|swish|gelu)\b',
    'transfer_learning': r'\b(transfer learning|pre.trained|fine.tun|pretrained|frozen layers?)\b',
    'gan': r'\b(gan|generative adversarial|generator|discriminator|dcgan|stylegan)\b',
    'nlp': r'\b(nlp|natural language|tokeniz|embedding|word2vec|glove|sentiment|text classification)\b',
    'reinforcement_learning': r'\b(reinforcement learning|rl|reward|policy|q-learning|dqn|actor.critic)\b',
    'python': r'\b(python|def |class |import |pip |function|decorator|generator)\b',
    'pytorch': r'\b(pytorch|torch|tensor|autograd|nn\.module|dataloader)\b',
    'tensorflow': r'\b(tensorflow|keras|tf\.|sequential|compile|fit)\b',
    'scikit_learn': r'\b(sklearn|scikit.learn|fit_transform|train_test_split|pipeline)\b',
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
    'definition': r'\b(what is|what are|define|meaning of|explain what|tell me about)\b',
    'how_to': r'\b(how to|how do i|how can i|steps to|implement|build|create|code)\b',
    'why': r'\b(why does|why do|why is|reason|cause|purpose of)\b',
    'comparison': r'\b(difference|compare|vs\.?|versus|better|which one|pros and cons)\b',
    'debugging': r'\b(error|bug|fix|issue|doesn\'?t work|wrong|fail|crash|exception)\b',
    'code_request': r'\b(write|code|coding|implement|script|program|function|show me|example code|code example|coding example|snippet|sample code|hello world|boilerplate)\b',
}

_MISCONCEPTION_INDICATORS = [
    r'\b(i thought|i assumed|isn\'?t it|wait,? so|but i think|confused because)\b',
    r'\b(that doesn\'?t make sense|contradicts?|but earlier|you said)\b',
    # Assertions / claims that may contain misconceptions
    r'\b(is basically|is essentially|is just|is the same as|is another word for)\b',
    r'\b(always|never|cannot|impossible|only way|must be|has to be)\b',
    r'\b(so basically|so that means|so it\'?s|meaning that|which means)\b',
    r'\b(the reason is|because .+ is|since .+ is|everyone knows)\b',
]

# Patterns for declarative assertions about technical concepts.
# When a student states something as fact (rather than asking), the LLM
# should verify whether it's accurate.
_ASSERTION_PATTERNS = [
    r'^(?:so |okay,? so |right,? so )?\w.+ (?:is|are|means|works? by|uses?) ',
    r'\b(?:I know|I believe|I read|I learned|from what I understand)\b',
]

_UNCERTAINTY_INDICATORS = [
    r'\b(i\'?m not sure|maybe|possibly|i think|confused|unclear|don\'?t get)\b',
    r'\b(can you clarify|could you explain again|still don\'?t understand)\b',
]


def _looks_structured_response(text: str) -> bool:
    content = (text or '').strip()
    if not content:
        return False
    has_heading = bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s+|[A-Za-z][A-Za-z ]{2,}:\s*$)', content))
    bullet_lines = re.findall(r'(?im)^\s*[-*]\s+', content)
    numbered_lines = re.findall(r'(?im)^\s*\d+\.\s+', content)
    return has_heading or len(bullet_lines) >= 2 or len(numbered_lines) >= 2


def _split_sentences_local(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?])\s+', (text or '').strip())
    return [c.strip() for c in chunks if c.strip()]


def _format_general_response(text: str) -> tuple[str, bool, str | None]:
    content = (text or '').strip()
    if not content:
        return content, False, None
    if _looks_structured_response(content):
        return content, False, None

    sentences = _split_sentences_local(content)
    if len(sentences) <= 2:
        return f"Explanation\n{content}", True, 'general_structure'

    intro = sentences[0]
    bullets = sentences[1:4]
    bullet_text = '\n'.join([f"- {s}" for s in bullets])
    formatted = (
        "Explanation\n"
        f"{intro}\n\n"
        "Key Points\n"
        f"{bullet_text}"
    )
    return formatted, True, 'general_structure'


def _format_structured_fallback(text: str, structured_intent: str | None) -> tuple[str, bool, str | None]:
    content = (text or '').strip()
    if not content:
        return content, False, None

    lower = content.lower()
    if structured_intent == 'comparison' and 'comparison' not in lower:
        return f"Explanation\n{content}\n\nComparison\n- Option A vs Option B: compare by accuracy, speed, complexity, and data requirements.", True, 'comparison_structure'
    if structured_intent == 'examples' and 'examples' not in lower:
        return f"Explanation\n{content}\n\nExamples\n- Example 1: Apply this on a simple dataset.\n- Example 2: Apply this on noisy real-world data.", True, 'examples_structure'
    if structured_intent == 'use_cases' and ('when to use' not in lower or 'when not to use' not in lower):
        return f"Explanation\n{content}\n\nWhen to Use\n- Use when assumptions and data conditions fit.\n\nWhen Not to Use\n- Avoid when assumptions break or simpler baselines perform similarly.", True, 'use_cases_structure'
    if structured_intent == 'multi_idea' and ('options' not in lower and 'approaches' not in lower):
        return f"Explanation\n{content}\n\nOptions\n- Option 1: Fast to implement\n- Option 2: Balanced tradeoff\n- Option 3: Highest potential performance\n\nRecommendation\nChoose based on your latency, accuracy, and maintenance constraints.", True, 'multi_idea_structure'

    return content, False, None


def _dynamic_block_type_from_title(title: str | None, content: str) -> str:
    title_norm = (title or '').strip().lower()
    content_norm = (content or '').lower()
    if title_norm in {'comparison', 'comparison table'}:
        return 'comparison_table'
    if title_norm in {'steps', 'key points', 'options'}:
        return 'steps'
    if title_norm in {'quiz', 'practice', 'questions'}:
        return 'quiz'
    if title_norm in {'hint', 'hints'}:
        return 'hint'
    if '```' in content_norm:
        return 'code'
    if '?' in content_norm and len(content_norm) < 280:
        return 'follow_up'
    if title_norm in {'explanation', 'summary', 'recommendation'}:
        return 'explanation'
    return 'text'


def _build_dynamic_response_payload(
    response_text: str,
    intent: str,
    confidence: float,
    fallback_used: bool,
    fallback_reason: str | None,
) -> dict:
    heading_pattern = re.compile(r'^(?:#{1,6}\s*)?([A-Za-z][A-Za-z ]{2,40})\s*:?$')
    lines = (response_text or '').splitlines()
    blocks = []
    current_title = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        heading_match = heading_pattern.match(stripped) if stripped else None
        if heading_match:
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    blocks.append({
                        'type': _dynamic_block_type_from_title(current_title, content),
                        'title': current_title,
                        'text': content,
                        'language': None,
                        'rows': [],
                        'items': [],
                    })
                current_lines = []
            current_title = heading_match.group(1).strip()
            continue
        current_lines.append(line)

    if current_lines:
        content = '\n'.join(current_lines).strip()
        if content:
            blocks.append({
                'type': _dynamic_block_type_from_title(current_title, content),
                'title': current_title,
                'text': content,
                'language': None,
                'rows': [],
                'items': [],
            })

    if not blocks:
        return build_text_only_dynamic_envelope(
            response_text=response_text,
            intent=intent,
            confidence=confidence,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ).model_dump()

    payload = build_text_only_dynamic_envelope(
        response_text='',
        intent=intent,
        confidence=confidence,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    ).model_dump()
    payload['content_blocks'] = blocks
    return payload


def _normalize_forced_mode(value: str) -> str:
    raw = (value or '').strip().lower()
    if raw in ('', 'auto', 'automatic'):
        return ''
    if raw == 'guided':
        return 'socratic'
    if raw in ('direct', 'supportive', 'socratic', 'supportive_socratic'):
        return raw
    return ''


def _normalize_forced_tone(value: str) -> str:
    raw = (value or '').strip().lower()
    if raw in ('', 'auto', 'automatic'):
        return ''
    if raw in ('friendly', 'professional', 'socratic', 'concise'):
        return raw
    return ''


def _extract_topics(message: str):
    lower = message.lower()
    return [t for t, p in _TOPIC_PATTERNS.items() if re.search(p, lower, re.I)]


def _detect_complexity(message: str):
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


def _detect_question_type(message: str):
    lower = message.lower()
    for qt, p in _QUESTION_TYPE_PATTERNS.items():
        if re.search(p, lower, re.I):
            return qt
    return 'general'


def _message_meta(message: str):
    words = message.split()
    misconceptions = []
    for p in _MISCONCEPTION_INDICATORS:
        misconceptions.extend(re.findall(p, message, re.I))
    uncertainty = 0
    for p in _UNCERTAINTY_INDICATORS:
        uncertainty += len(re.findall(p, message, re.I))
    # Detect if the message is an assertion/claim (vs a question).
    is_assertion = (
        '?' not in message
        and any(re.search(p, message, re.I) for p in _ASSERTION_PATTERNS)
    )
    return {
        'word_count': len(words),
        'has_code': bool(re.search(r'(```|def |class |import |print\(|for .* in)', message)),
        'has_question_mark': '?' in message,
        'is_assertion': is_assertion,
        'uncertainty_markers': uncertainty,
        'misconception_signals': misconceptions,
    }


def _build_recommendations(topics, complexity, qtype, ks, meta):
    """Build profile-update recommendations from analysis."""
    recs = {
        'add_to_strong_topics': [],
        'add_to_weak_topics': [],
        'move_to_strong_topics': [],
        'update_skill_level': None,
        'trigger_socratic_mode': False,
        'misconception_detected': False,
        'misconception_topic': None,
        'misconception_detail': None,
        'comprehension_check_topic': None,
        'emotional_state': 'neutral',
        'suggested_approach': 'explain_simply',
        'tutoring_mode': 'direct',
        'mode_reason': 'stable understanding detected',
    }

    strong = ks.get('strong_topics', [])
    weak = ks.get('weak_topics', [])
    topics_map = ks.get('topics', {})

    for t in topics:
        td = topics_map.get(t, {})
        cnt = td.get('count', 0) if isinstance(td, dict) else 0
        # Count the current turn (not yet persisted) when promoting strength.
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
    ba = ks.get('behavioral', {})
    cd = ba.get('complexity_distribution', {})
    total = sum(cd.values()) if cd else 0
    if total >= 10:
        adv_r = cd.get('advanced', 0) / total
        beg_r = cd.get('beginner', 0) / total
        cur = ks.get('skill_level', 'Intermediate')
        if adv_r > 0.5 and cur != 'Advanced':
            recs['update_skill_level'] = 'Advanced'
        elif beg_r > 0.6 and cur != 'Beginner':
            recs['update_skill_level'] = 'Beginner'
        elif adv_r < 0.5 and beg_r < 0.5 and cur != 'Intermediate':
            recs['update_skill_level'] = 'Intermediate'

    # misconception / socratic
    if len(meta.get('misconception_signals', [])) > 0:
        recs['misconception_detected'] = True
        recs['misconception_topic'] = topics[0] if topics else 'general'
        recs['trigger_socratic_mode'] = True

    # Confusion = misconception. Any uncertainty about a topic means the
    # student doesn't truly understand it, which counts as a misconception.
    uncertainty = meta.get('uncertainty_markers', 0)
    if uncertainty >= 1 and topics:
        recs['trigger_socratic_mode'] = True
        if not recs.get('misconception_detected'):
            recs['misconception_detected'] = True
            recs['misconception_topic'] = topics[0]
            recs['misconception_detail'] = (
                f'Student expressed confusion/uncertainty about {topics[0]}'
            )
    elif uncertainty >= 2:
        recs['trigger_socratic_mode'] = True

    # Repeated-topic confusion: if the student keeps asking beginner-level
    # questions about a topic they've already discussed 3+ times, this
    # signals persistent confusion — which often hides a misconception.
    for t in topics:
        td = topics_map.get(t, {})
        if isinstance(td, dict):
            count = td.get('count', 0)
            cl = td.get('complexity_levels', {})
            beginner_count = cl.get('beginner', 0) if isinstance(cl, dict) else 0
            total_cl = sum(cl.values()) if isinstance(cl, dict) else 0
            # 3+ interactions, mostly beginner — student is stuck
            if count >= 3 and total_cl > 0 and beginner_count / total_cl > 0.5:
                recs['trigger_socratic_mode'] = True
                if not recs.get('misconception_detected'):
                    recs['misconception_detected'] = True
                    recs['misconception_topic'] = t
                    recs['misconception_detail'] = (
                        f'Student has asked about {t} {count} times at beginner level — '
                        f'possible persistent misunderstanding'
                    )
                break

    # comprehension check
    for t, td in topics_map.items():
        if isinstance(td, dict) and td.get('count', 0) >= 5 and not td.get('verified'):
            recs['comprehension_check_topic'] = t
            break

    # Initial mode selection; final pass happens in analyze() after LLM merge.
    low_mastery = AdaptiveModeService.has_low_mastery(topics_map, topics)
    mode, reason = AdaptiveModeService.decide_mode(
        learner_level=ks.get('skill_level', 'intermediate'),
        uncertainty_markers=meta.get('uncertainty_markers', 0),
        misconception_detected=recs.get('misconception_detected', False),
        emotional_state=recs.get('emotional_state', 'neutral'),
        low_mastery_detected=low_mastery,
        user_preference=ks.get('conversation_preferences', {}).get('adaptive_preference'),
    )
    recs['tutoring_mode'] = mode
    recs['mode_reason'] = reason
    recs['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)

    return recs


def _finalize_tutoring_mode(recs, knowledge_state, topics, meta):
    """Finalize tutoring mode after LLM enrichment and heuristics merge."""
    topics_map = knowledge_state.get('topics', {})
    low_mastery = AdaptiveModeService.has_low_mastery(topics_map, topics)
    mode, reason = AdaptiveModeService.decide_mode(
        learner_level=knowledge_state.get('skill_level', 'intermediate'),
        uncertainty_markers=meta.get('uncertainty_markers', 0),
        misconception_detected=recs.get('misconception_detected', False),
        emotional_state=recs.get('emotional_state', 'neutral'),
        low_mastery_detected=low_mastery,
        user_preference=knowledge_state.get('conversation_preferences', {}).get('adaptive_preference'),
    )
    recs['tutoring_mode'] = mode
    recs['mode_reason'] = reason
    recs['trigger_socratic_mode'] = AdaptiveModeService.is_socratic(mode)
    return recs


# ────────────────────────────────────────────────────────────
# LLM fallback analysis
# ────────────────────────────────────────────────────────────
def _analyze_with_llm(client, message: str, profile: dict):
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
        logger.warning("LLM analysis fallback error: %s", e)
        return None


# ────────────────────────────────────────────────────────────
# DeepAgentRouter
# ────────────────────────────────────────────────────────────
class DeepAgentRouter:
    """
    Single entry-point for the AI tutoring pipeline:
        analyse → route → build prompt → call Groq → return
    """

    # ── routing ─────────────────────────────────────────────
    @staticmethod
    def route(query: str, knowledge_state: dict) -> str:
        """Return the best agent key for *query*."""
        lower = query.lower()
        scores = {}
        for key, cfg in AGENTS.items():
            scores[key] = sum(1 for kw in cfg['keywords'] if kw in lower)

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

        # Tie-break using user's strongest area
        strongest = knowledge_state.get('strongest_domain', 'machine_learning')
        return strongest.lower().replace(' ', '_') if strongest else 'machine_learning'

    # ── analysis (hybrid) ───────────────────────────────────
    @staticmethod
    def analyze(client, message: str, knowledge_state: dict):
        """
        Fast keyword analysis + LLM fallback.
        Returns the unified analysis dict consumed downstream.
        """
        topics_kw = _extract_topics(message)
        complexity_kw = _detect_complexity(message)
        qtype_kw = _detect_question_type(message)
        meta = _message_meta(message)

        method = 'keywords'
        topics = topics_kw
        complexity = complexity_kw
        qtype = qtype_kw
        llm_data = None
        langchain_used = False
        langchain_fallback_reason = None

        word_count = meta.get('word_count', 0)
        uncertainty = meta.get('uncertainty_markers', 0)
        should_llm = (
            len(topics_kw) == 0
            or (word_count > 50 and len(topics_kw) < 2)
            or len(meta.get('misconception_signals', [])) > 0
            # When a student makes a declarative statement about a detected
            # topic, the LLM should check for misconceptions — this is where
            # students express wrong beliefs without realising it.
            or (len(topics_kw) > 0 and meta.get('is_assertion', False))
            # Any confusion about a topic → ask LLM to diagnose what exactly
            # the student is confused about.
            or (len(topics_kw) > 0 and uncertainty >= 1)
        )
        print('USE_LANGCHAIN:', Config.USE_LANGCHAIN)
        print('should_llm:', should_llm)

        if should_llm and Config.USE_LANGCHAIN:
            try:
                lc_result = LangChainAnalyzer.analyze_message(
                    user_message=message,
                    keyword_topics=topics_kw,
                    keyword_complexity=complexity_kw,
                    keyword_question_type=qtype_kw,
                    message_meta=meta,
                    knowledge_state=knowledge_state,
                )
                if lc_result.get('used'):
                    cues = lc_result['cues']
                    langchain_used = True
                    method = 'langchain_hybrid'
                    llm_data = {
                        'emotional_state': cues.emotional_state,
                        'suggested_approach': cues.suggested_approach,
                        'is_misconception': cues.misconception_detected,
                        'misconception_detail': cues.misconception_detail,
                    }
                    topics = list(set(topics_kw + (cues.topics or [])))
                    logger.info('analysis_path=langchain_hybrid')
                else:
                    langchain_fallback_reason = lc_result.get('error') or 'unknown'
                    if langchain_fallback_reason == 'provider_or_prompt_unavailable':
                        print('analysis_debug: provider disabled or model creation failed')
                    if langchain_fallback_reason == 'parse_failed':
                        print('analysis_debug: parsing failed')
                    logger.info('analysis_path=fallback reason=%s', langchain_fallback_reason)
            except Exception as e:
                langchain_fallback_reason = 'invoke_failed'
                logger.warning('LangChain analysis integration failed: %s', e)

        print('analysis_path:', 'langchain' if langchain_used else 'fallback')
        print('analysis_fallback_reason:', langchain_fallback_reason)

        if should_llm and client and not langchain_used:
            llm_result = _analyze_with_llm(client, message, knowledge_state)
            if llm_result:
                method = 'hybrid'
                llm_data = llm_result
                topics = list(set(topics_kw + llm_result.get('topics', [])))
                complexity = llm_result.get('complexity', complexity_kw)
                qtype = llm_result.get('question_type', qtype_kw)

        recs = _build_recommendations(topics, complexity, qtype, knowledge_state, meta)

        if llm_data:
            recs['emotional_state'] = llm_data.get('emotional_state', 'neutral')
            recs['suggested_approach'] = llm_data.get('suggested_approach', 'explain_simply')
            if llm_data.get('is_misconception'):
                recs['misconception_detected'] = True
                recs['misconception_detail'] = llm_data.get('misconception_detail')
                recs['trigger_socratic_mode'] = True

            # Confusion detected by LLM = misconception.
            if llm_data.get('emotional_state') == 'confused' and topics:
                recs['trigger_socratic_mode'] = True
                if not recs.get('misconception_detected'):
                    recs['misconception_detected'] = True
                    recs['misconception_topic'] = topics[0]
                    recs['misconception_detail'] = (
                        f'LLM detected student confusion about {topics[0]}'
                    )

        recs = _finalize_tutoring_mode(recs, knowledge_state, topics, meta)

        return {
            'topics': topics,
            'complexity': complexity,
            'question_type': qtype,
            'analysis_method': method,
            'message_analysis': meta,
            'recommendations': recs,
            'confidence': 0.9 if method == 'hybrid' else 0.7,
            'langchain': {
                'used': langchain_used,
                'fallback_reason': langchain_fallback_reason,
            },
        }

    # ── system prompt builder ───────────────────────────────
    @staticmethod
    def build_system_prompt(
        agent_key: str,
        profile: dict,
        knowledge_state: dict,
        analysis: dict = None,
        forced_mode: str = None,
        forced_reason: str = None,
        rag_context: str = None,
    ):
        """
        Construct a fully-personalised system prompt merging:
        agent persona + learner profile + knowledge state + adaptations.
        """
        agent_cfg = AGENTS.get(agent_key, AGENTS['machine_learning'])
        ks = knowledge_state or {}
        ba = ks.get('behavioral', {})
        prefs = ks.get('conversation_preferences', {})
        adaptations = ks.get('current_adaptations', {})
        analysis_recs = (analysis or {}).get('recommendations', {})
        topics_map = ks.get('topics', {})
        misconceptions = ks.get('misconceptions', {})
        strong = ks.get('strong_topics', [])
        weak = ks.get('weak_topics', [])

        # effective level
        cd = ba.get('complexity_distribution', {})
        total_q = sum(cd.values()) if cd else 0
        if total_q >= 5:
            adv_r = cd.get('advanced', 0) / total_q
            beg_r = cd.get('beginner', 0) / total_q
            effective_level = 'Advanced' if adv_r > 0.5 else ('Beginner' if beg_r > 0.5 else 'Intermediate')
        else:
            effective_level = profile.get('skill_level', profile.get('python', 'Intermediate'))

        # mastery lines
        mastery_lines = []
        for topic, td in topics_map.items():
            if isinstance(td, dict) and td.get('count', 0) >= 2:
                m = td.get('mastery_level', 0)
                mastery_lines.append(f"  - {topic}: {m:.0%} mastery ({td['count']} interactions)")

        # misconception lines
        misconception_lines = []
        for topic, md in misconceptions.items():
            if isinstance(md, dict) and not md.get('corrected'):
                misconception_lines.append(f"  - {topic}: {md.get('detail', 'unclear understanding')}")

        # style preferences
        style_notes = []
        if prefs.get('prefers_examples'):
            style_notes.append('real-world examples')
        if prefs.get('prefers_code'):
            style_notes.append('code snippets')
        if prefs.get('prefers_analogies'):
            style_notes.append('analogies')
        style_str = f"Include {', '.join(style_notes)} when possible." if style_notes else ''

        # tone & length overrides
        tone_inst = ''
        length_inst = ''
        pt = prefs.get('preferred_tone', '')
        pl = prefs.get('preferred_length', '')
        forced_tone = _normalize_forced_tone(profile.get('force_tone'))

        if forced_tone == 'friendly':
            tone_inst = 'CRITICAL: Use a FRIENDLY, casual tone — warm, contractions, like a helpful friend.'
        elif forced_tone == 'professional':
            tone_inst = 'CRITICAL: Use a FORMAL, professional, academic tone.'
        elif forced_tone == 'socratic':
            tone_inst = 'CRITICAL: Use a Socratic teaching voice: ask guiding questions before direct conclusions.'
        elif forced_tone == 'concise':
            length_inst = 'CRITICAL: Keep responses concise and direct. Prefer short paragraphs and compact bullets.'

        if not tone_inst and pt == 'friendly':
            tone_inst = 'CRITICAL: Use a FRIENDLY, casual tone — warm, contractions, like a helpful friend.'
        elif not tone_inst and pt == 'formal':
            tone_inst = 'CRITICAL: Use a FORMAL, professional, academic tone.'
        if not length_inst and pl == 'short':
            length_inst = 'CRITICAL: Keep responses to 2-4 sentences MAX. Be brief and direct.'
        elif not length_inst and pl == 'detailed':
            length_inst = 'CRITICAL: Provide DETAILED responses. Go deep, cover edge cases.'

        # adaptation directives
        active_mode = forced_mode or analysis_recs.get('tutoring_mode') or adaptations.get('tutoring_mode', 'direct')
        mode_reason = forced_reason or analysis_recs.get('mode_reason') or adaptations.get('mode_reason', 'stable understanding detected')

        adapt = [AdaptiveModeService.mode_prompt_instruction(active_mode)]
        adapt.append(f"MODE REASON: {mode_reason}.")

        if AdaptiveModeService.is_socratic(active_mode):
            adapt.append("SOCRATIC SIGNAL: Ask probing questions before giving final direct answer.")
        emo = adaptations.get('emotional_state', 'neutral')
        if emo == 'frustrated':
            adapt.append("SUPPORT MODE: Be extra warm, break into tiny steps.")
        elif emo == 'curious':
            adapt.append("EXPLORATION MODE: Go deeper, share insights.")
        chk = adaptations.get('comprehension_check')
        if chk and AdaptiveModeService.is_socratic(active_mode):
            adapt.append(f"After answering, ask: 'Can you explain {chk} in your own words?'")

        learning_tone = profile.get('learning_tone', profile.get('tone', 'Friendly')).lower()
        conversation_count = profile.get('conversation_count', 0)
        name = profile.get('user_name') or profile.get('name', 'Student')

        pref_header = ''
        if tone_inst or length_inst:
            pref_header = f"""⚡ STUDENT'S EXPLICIT PREFERENCES (MUST FOLLOW):
{tone_inst}
{length_inst}
---
"""

        prompt = f"""{pref_header}{agent_cfg['system']}

You are AdaptiveAI, an intelligent tutoring assistant that truly knows this student.

=== LEARNER INTELLIGENCE PROFILE ===
Name: {name}
Effective Skill Level: {effective_level} (from {total_q} analysed interactions)
Learning Tone: {learning_tone}
Tutoring Mode: {active_mode}
Domain: {agent_cfg['label']}
Conversations: {conversation_count}
{'MASTERED: ' + ', '.join(strong) if strong else ''}
{'STILL LEARNING: ' + ', '.join(weak) if weak else ''}

{'TOPIC MASTERY MAP:' + chr(10) + chr(10).join(mastery_lines) if mastery_lines else ''}
{'ACTIVE MISCONCEPTIONS:' + chr(10) + chr(10).join(misconception_lines) if misconception_lines else ''}

=== ADAPTATION RULES ===
1. Level {effective_level}: {'Simple analogies, step-by-step, avoid jargon' if effective_level == 'Beginner' else 'Balance theory + practice' if effective_level == 'Intermediate' else 'Deep technical depth, maths, research-level'}
2. {style_str}
{chr(10).join(adapt)}

{tone_inst}
{length_inst}

{'Keep responses to 2-4 sentences MAX.' if pl == 'short' else 'Keep responses concise but thorough (150-300 words unless more detail requested).'}"""

        # ── RAG context injection (appended, never overwrites) ──
        if rag_context:
            prompt += f"""

=== RETRIEVED DOMAIN KNOWLEDGE (from knowledge graph) ===
Use the following retrieved concepts to ground your response.
Teach these concepts in YOUR tutoring voice — do not copy verbatim.
If the retrieved info contradicts your knowledge, prefer your own.
Only use what is directly relevant to the student's question.

{rag_context}
"""

        return prompt

    # ── orchestrator ────────────────────────────────────────
    @staticmethod
    def generate(message: str, profile: dict, knowledge_state: dict,
                 chat_history: list, user_id: str = None):
        """
        Full pipeline:
          analyse → route → prompt → Groq API → return
        Returns dict with: success, response, agent, tokens_used,
                           response_time_ms, analysis
        """
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'Groq API key not configured'}

        client = Groq(api_key=api_key)
        t0 = time.time()

        # 1. analyse
        analysis = DeepAgentRouter.analyze(client, message, knowledge_state)

        # 2. route
        agent_key = DeepAgentRouter.route(message, knowledge_state)

        # 2b. RAG retrieval (feature-flagged, fail-safe)
        rag_context = None
        if Config.USE_RAG:
            try:
                from services.rag.rag_router import RAGRouter
                student_context = {
                    'weak_topics': knowledge_state.get('weak_topics', []),
                }
                rag_result = RAGRouter.retrieve(agent_key, message, student_context)
                if rag_result:
                    rag_context = rag_result.get('formatted_context', '') or None
                    if rag_context:
                        logger.info('RAG context retrieved for domain=%s concepts=%s',
                                    agent_key, rag_result.get('primary_concepts', []))
            except Exception as e:
                logger.warning('RAG retrieval failed, continuing without: %s', e)

        # Single source of truth for current response mode.
        recs = analysis.get('recommendations', {})
        response_mode = recs.get('tutoring_mode') or knowledge_state.get('current_adaptations', {}).get('tutoring_mode', 'direct')
        response_reason = recs.get('mode_reason') or knowledge_state.get('current_adaptations', {}).get('mode_reason', 'stable understanding detected')

        forced_mode = _normalize_forced_mode(
            profile.get('force_tutoring_mode')
            or profile.get('adaptive_preference')
            or (profile.get('conversation_preferences', {}) or {}).get('adaptive_preference')
        )
        if forced_mode:
            response_mode = forced_mode
            response_reason = 'user selected tutoring mode'
            recs['tutoring_mode'] = response_mode
            recs['mode_reason'] = response_reason

        logger.debug(
            "DeepAgentRouter.generate pre-prompt mode=%s reason=%s analysis_mode=%s",
            response_mode,
            response_reason,
            recs.get('tutoring_mode'),
        )

        # 3. build prompt
        system_prompt = DeepAgentRouter.build_system_prompt(
            agent_key,
            profile,
            knowledge_state,
            analysis,
            forced_mode=response_mode,
            forced_reason=response_reason,
            rag_context=rag_context,
        )

        # 4. build messages
        messages = [{'role': 'system', 'content': system_prompt}]
        for m in (chat_history or [])[-10:]:
            messages.append({
                'role': m.get('role', 'user'),
                'content': m.get('content', ''),
            })
        messages.append({'role': 'user', 'content': message})

        recent_context = ' | '.join(
            [f"{m.get('role', 'user')}: {m.get('content', '')}" for m in (chat_history or [])[-4:]]
        )
        topic_context = ', '.join(analysis.get('topics', [])) or 'general'
        generation_plan = select_output_plan(
            question_type=analysis.get('question_type', 'general'),
            complexity=analysis.get('complexity', 'intermediate'),
            uncertainty_markers=(analysis.get('message_analysis', {}) or {}).get('uncertainty_markers', 0),
            has_code=(analysis.get('message_analysis', {}) or {}).get('has_code', False),
            topic_context=topic_context,
            recent_context=recent_context,
            user_message=message,
        )
        structured_intents = {'comparison', 'examples', 'use_cases', 'multi_idea'}
        use_langchain_generation = (
            Config.USE_LANGCHAIN
            and generation_plan.get('structured_response_required', False)
            and generation_plan.get('structured_intent') in structured_intents
        )
        logger.info(
            'Generation routing: path=%s structured_required=%s structured_intent=%s',
            'langchain' if use_langchain_generation else 'native',
            generation_plan.get('structured_response_required', False),
            generation_plan.get('structured_intent'),
        )

        # 5. LangChain path (feature-flagged) with strict fallback.
        attempting_langchain_generation = bool(use_langchain_generation)
        print('attempting_langchain_generation:', attempting_langchain_generation)
        generation_fallback_reason = None
        if use_langchain_generation:
            try:
                misconceptions = []
                for topic, md in (knowledge_state.get('misconceptions', {}) or {}).items():
                    if isinstance(md, dict) and not md.get('corrected'):
                        detail = (md.get('detail') or '').strip()
                        misconceptions.append(f"{topic}: {detail}" if detail else topic)

                lc_result = LangChainGenerator.generate_response(
                    tutoring_mode=response_mode,
                    user_message=message,
                    learner_level=knowledge_state.get('skill_level', profile.get('skill_level', 'intermediate')),
                    strong_topics=knowledge_state.get('strong_topics', []),
                    weak_topics=knowledge_state.get('weak_topics', []),
                    misconceptions=misconceptions,
                    recent_context=recent_context,
                    topic_context=topic_context,
                    question_type=analysis.get('question_type', 'general'),
                    complexity=analysis.get('complexity', 'intermediate'),
                    uncertainty_markers=(analysis.get('message_analysis', {}) or {}).get('uncertainty_markers', 0),
                    has_code=(analysis.get('message_analysis', {}) or {}).get('has_code', False),
                    rag_context=rag_context or '',
                )

                if lc_result.get('used') and lc_result.get('response'):
                    elapsed = round((time.time() - t0) * 1000)
                    print('generation_path:', 'langchain')
                    print('generation_fallback_reason:', None)
                    logger.info('generation_path=langchain mode=%s', response_mode)
                    return {
                        'success': True,
                        'response': lc_result['response'],
                        'agent': agent_key,
                        'agent_name': AGENTS[agent_key]['label'],
                        'tokens_used': lc_result.get('tokens_used', 0),
                        'response_time_ms': elapsed,
                        'analysis': analysis,
                        'tutoring_mode': response_mode,
                        'mode_reason': response_reason,
                        'generation': {
                            'path': 'langchain',
                            'langchain_used': True,
                            'structured_required': bool(generation_plan.get('structured_response_required', False)),
                            'structured_intent': generation_plan.get('structured_intent'),
                            'intent': generation_plan.get('intent'),
                            'sections': lc_result.get('sections', []),
                            'formatter_applied': bool(lc_result.get('formatter_applied', False)),
                            'formatter_reason': lc_result.get('formatter_reason'),
                            'fallback_reason': None,
                        },
                        'dynamic_response': lc_result.get('dynamic_response') or _build_dynamic_response_payload(
                            response_text=lc_result['response'],
                            intent=(generation_plan.get('intent') or generation_plan.get('structured_intent') or 'general_fallback'),
                            confidence=float(generation_plan.get('confidence', 0.0) or 0.0),
                            fallback_used=False,
                            fallback_reason=None,
                        ),
                    }

                generation_fallback_reason = lc_result.get('error', 'unknown')
                if generation_fallback_reason == 'provider_or_prompt_unavailable':
                    print('generation_debug: provider disabled or model creation failed')
                logger.info('generation_path=fallback reason=%s', generation_fallback_reason)
            except Exception as e:
                generation_fallback_reason = 'invoke_failed'
                logger.warning('LangChain generation integration failed, using fallback: %s', e)
        else:
            generation_fallback_reason = 'native_default_unstructured'

        # 6. call Groq fallback path
        try:
            completion = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
            )
            response_text = completion.choices[0].message.content
            tokens_used = completion.usage.total_tokens if completion.usage else 0
        except Exception as e:
            logger.error("Groq API call failed: %s", e)
            return {'success': False, 'error': str(e)}

        # In dynamic mode, avoid rigid rewriting. Keep only minimal legacy formatting when disabled.
        formatter_applied = False
        formatter_reason = None
        structured_intent = generation_plan.get('structured_intent')
        if not Config.DYNAMIC_CHAT_SCHEMA_ENABLED and generation_plan.get('structured_response_required', False):
            response_text, formatter_applied, formatter_reason = _format_structured_fallback(
                response_text,
                structured_intent,
            )

        if not Config.DYNAMIC_CHAT_SCHEMA_ENABLED and not formatter_applied:
            response_text, formatter_applied, formatter_reason = _format_general_response(response_text)

        dynamic_response = _build_dynamic_response_payload(
            response_text=response_text,
            intent=(generation_plan.get('intent') or structured_intent or 'general_fallback'),
            confidence=float(generation_plan.get('confidence', 0.0) or 0.0),
            fallback_used=bool(generation_fallback_reason),
            fallback_reason=generation_fallback_reason,
        )

        elapsed = round((time.time() - t0) * 1000)
        print('generation_path:', 'fallback')
        print('generation_fallback_reason:', generation_fallback_reason)
        logger.info('generation_path=fallback_native_groq mode=%s', response_mode)

        return {
            'success': True,
            'response': response_text,
            'agent': agent_key,
            'agent_name': AGENTS[agent_key]['label'],
            'tokens_used': tokens_used,
            'response_time_ms': elapsed,
            'analysis': analysis,
            'tutoring_mode': response_mode,
            'mode_reason': response_reason,
            'generation': {
                'path': 'native_groq',
                'langchain_used': False,
                'structured_required': bool(generation_plan.get('structured_response_required', False)),
                'structured_intent': generation_plan.get('structured_intent'),
                'intent': generation_plan.get('intent'),
                'sections': generation_plan.get('sections', []),
                'formatter_applied': formatter_applied,
                'formatter_reason': formatter_reason,
                'fallback_reason': generation_fallback_reason,
            },
            'dynamic_response': dynamic_response,
        }
