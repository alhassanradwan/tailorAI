"""LangChain prompt templates for tutoring and structured analysis."""

import re

try:
    from langchain_core.prompts import ChatPromptTemplate
except Exception:
    ChatPromptTemplate = None


MODE_SYSTEM_INSTRUCTIONS = {
    'direct': (
        'MODE: DIRECT. Give clear, efficient explanations with minimal detours while staying accurate and respectful.'
    ),
    'supportive': (
        'MODE: SUPPORTIVE. Be encouraging and patient, break concepts into small steps, and avoid heavy questioning.'
    ),
    'socratic': (
        'MODE: SOCRATIC. Ask guiding questions before direct answers and build reasoning progressively.'
    ),
    'supportive_socratic': (
        'MODE: SUPPORTIVE_SOCRATIC. Blend encouragement with guiding questions, then provide concise correction.'
    ),
}


VALID_MODES = {'direct', 'supportive', 'socratic', 'supportive_socratic'}
VALID_LEVELS = {'beginner', 'intermediate', 'advanced'}


def normalize_mode(mode: str) -> str:
    mode_norm = (mode or '').strip().lower()
    if mode_norm in VALID_MODES:
        return mode_norm
    return 'direct'


def normalize_level(level: str) -> str:
    level_norm = (level or '').strip().lower()
    if level_norm in VALID_LEVELS:
        return level_norm
    return 'intermediate'


def select_code_style_profile(learner_level: str, question_type: str, has_code: bool) -> str:
    """Return a compact code-style policy tuned to learner level and request type."""
    level = normalize_level(learner_level)
    qtype = (question_type or 'general').strip().lower()

    base = (
        'Use production-quality style: meaningful names, small focused functions, consistent formatting, '
        'input/output clarity, and no dead code. Use standard libraries/APIs correctly.'
    )

    if not has_code and qtype not in {'code_request', 'debugging', 'how_to'}:
        return base + ' Add code only if it clearly improves learning.'

    if level == 'beginner':
        return (
            base + ' Prefer readability first: straightforward control flow, explicit variable names, '
            'minimal abstractions, and one clear runnable example.'
        )
    if level == 'advanced':
        return (
            base + ' Prefer professional patterns: modular structure, efficient choices, edge-case handling, '
            'and concise, technically precise explanations.'
        )

    return (
        base + ' Balance readability and robustness: clean structure, practical defaults, and brief notes on tradeoffs.'
    )


def select_output_plan(
    question_type: str,
    complexity: str,
    uncertainty_markers: int,
    has_code: bool,
    topic_context: str,
    recent_context: str,
    user_message: str = '',
) -> dict:
    """Select a compact, adaptive response plan from weak/strong learner signals."""
    qt = (question_type or 'general').strip().lower()
    cx = normalize_level(complexity)
    uncertainty = int(uncertainty_markers or 0)

    # Do not overfit to a single message: blend with recent context signal.
    context_signal = (recent_context or '').lower()
    confusion_words = ('confused', "don't understand", 'unclear', 'stuck')
    confusion_hits = sum(1 for w in confusion_words if w in context_signal)
    confusion_state = uncertainty >= 2 or confusion_hits >= 2

    include = ['explanation']
    rationale = []

    msg = (user_message or '').lower()
    comparison_intent = qt == 'comparison' or bool(
        re.search(r'\b(compare|comparison|vs\.?|versus|difference(?:\s+between)?)\b', msg)
    )
    examples_intent = bool(
        re.search(r'\b(example|examples|for example|with examples?)\b', msg)
    )
    use_cases_intent = bool(
        re.search(r'\b(when to use|when should i use|use case|use cases|where to use)\b', msg)
    )

    structured_intent = None
    if comparison_intent:
        structured_intent = 'comparison'
    elif use_cases_intent:
        structured_intent = 'use_cases'
    elif examples_intent:
        structured_intent = 'examples'

    structured_response_required = structured_intent is not None
    visual_intent = any(k in msg for k in ('visual', 'diagram', 'flow', 'flowchart', 'chart', 'table'))

    if visual_intent and not has_code:
        include.append('visual')
        rationale.append('explicit visual request detected')

    if structured_intent == 'comparison':
        include.append('table')
        rationale.append('structured intent: comparison table required')
    elif structured_intent == 'examples':
        include.append('examples')
        rationale.append('structured intent: explanation with examples required')
    elif structured_intent == 'use_cases':
        include.append('use_cases')
        rationale.append('structured intent: use-cases breakdown required')
    elif has_code or (qt in {'code_request', 'debugging', 'how_to'} and not visual_intent):
        include.append('code')
        rationale.append('code requested or implementation-oriented question')
    elif qt in {'comparison'}:
        include.append('table')
        rationale.append('comparison is clearer in a compact table')
    elif qt in {'why', 'definition'} and cx == 'beginner':
        include.append('analogy')
        rationale.append('beginner conceptual framing benefits from analogy')

    visual_candidate_topics = ('pipeline', 'workflow', 'architecture', 'model flow', 'training loop')
    topic_text = (topic_context or '').lower()
    visual_helpful = any(t in topic_text for t in visual_candidate_topics)

    if not has_code and visual_helpful and qt in {'how_to', 'why', 'general'} and 'table' not in include:
        include.append('visual')
        rationale.append('process/architecture topic benefits from visual structure')

    if confusion_state:
        include.append('practice')
        rationale.append('confusion detected: include one short checkpoint')

    # Keep responses focused: explanation + at most one primary support + optional single practice.
    include_final = ['explanation']
    if structured_intent == 'comparison':
        include_final.append('table')
    elif structured_intent == 'examples':
        include_final.append('examples')
    elif structured_intent == 'use_cases':
        include_final.append('use_cases')
    else:
        support_priority = ['code', 'visual', 'table', 'analogy']
        selected_support = next((item for item in support_priority if item in include), None)
        if selected_support:
            include_final.append(selected_support)
    if 'practice' in include:
        include_final.append('practice')

    max_sections = 4
    if len(include_final) > max_sections:
        include_final = include_final[:max_sections]

    return {
        'sections': include_final,
        'max_sections': max_sections,
        'max_questions': 1,
        'structured_response_required': structured_response_required,
        'structured_intent': structured_intent,
        'confusion_state': confusion_state,
        'rationale': '; '.join(rationale) if rationale else 'default explanation-first plan',
    }


def response_contract(question_type: str, sections: list[str]) -> str:
    """Return a compact output-format contract to stabilize response style."""
    qtype = (question_type or 'general').strip().lower()
    sec = sections or ['explanation']
    has_code = 'code' in sec or qtype in {'code_request', 'debugging', 'how_to'}

    if 'examples' in sec:
        return (
            'FORMAT CONTRACT: 1) Concept (short and clear). '
            '2) Examples section with at least 2 concrete examples. '
            '3) Optional brief takeaway. Use clear headings.'
        )

    if 'use_cases' in sec:
        return (
            'FORMAT CONTRACT: 1) Concept summary. '
            '2) When to use (bullet list). '
            '3) When not to use (bullet list). '
            '4) Optional quick rule of thumb. Use clear headings.'
        )

    if qtype == 'comparison' or 'table' in sec:
        return (
            'FORMAT CONTRACT: 1) Brief comparison setup. '
            '2) Compact comparison table with practical criteria. '
            '3) Recommendation for when to choose each option.'
        )

    if has_code:
        return (
            'FORMAT CONTRACT: 1) Concept (1-3 short paragraphs). '
            '2) One clean code block using best style. '
            '3) Brief code explanation after code (2-5 bullets). '
            'Do not output multiple competing code versions unless explicitly asked.'
        )

    if 'visual' in sec:
        return (
            'FORMAT CONTRACT: explanation-first; then visual structure using flow steps or a compact table. '
            'Prefer chart descriptions for trends. Avoid code unless explicitly requested.'
        )

    return (
        'FORMAT CONTRACT: explanation-first; include only selected supporting element(s); '
        'keep structure concise and learner-adaptive.'
    )


def get_tutor_prompt_template():
    if not ChatPromptTemplate:
        return None

    return ChatPromptTemplate.from_messages([
        (
            'system',
            (
                'You are AdaptiveAI tutoring assistant.\n'
                '{mode_instruction}\n'
                'Learner level: {learner_level}\n'
                'Strong topics: {strong_topics}\n'
                'Weak topics: {weak_topics}\n'
                'Misconceptions: {misconceptions}\n'
                'Recent context: {recent_context}\n'
                'Topic context: {topic_context}\n'
                'Output plan sections: {output_sections}\n'
                'Output selection rationale: {output_rationale}\n'
                'Response contract: {response_contract}\n'
                'Code style profile: {code_style_profile}\n'
                'Safety defaults: learner_level={safe_learner_level}, tutoring_mode={safe_tutoring_mode}\n'
                'CRITICAL OUTPUT RULES:\n'
                '1) Use at most {max_sections} sections.\n'
                '2) Always include an explanation section.\n'
                '3) Include only the most relevant supporting element (code OR visual OR analogy OR table).\n'
                '4) Add practice/checkpoint only when useful, and ask at most {max_questions} question total.\n'
                '5) Use visuals only when they improve understanding.\n'
                '6) Keep templates adaptive to learner state, not rigid.\n'
                '7) Structure explanations as: concept (what and why) -> simple example -> code if needed -> short code explanation.\n'
                '8) When helpful, include at least one simple example.\n'
                '9) Code generation rules: clean/readable code, correct feature representation, no unnecessary complexity, correct API usage, minimal useful comments.\n'
                '10) Always explain code briefly after writing it.\n'
                '11) Ensure technical correctness: match method to problem type and avoid common mistakes.\n'
                '12) For machine learning code, choose correct model type (classification vs regression), NEVER use regression models for binary classification, and prefer standard correct algorithms.\n'
                '13) Visual guidance: use tables for comparisons, flow steps for processes, and chart descriptions for trends when useful.\n'
                '14) Coding style policy: use clear naming, deterministic structure, standard formatting, and avoid clever-but-hard-to-read shortcuts.\n'
                '15) For Python examples, follow PEP 8 style and prefer type hints when helpful for clarity.\n'
                '16) For advanced learners, keep technical depth high and avoid oversimplifying unless the learner asks to simplify.\n'
                '17) Never hallucinate APIs, libraries, papers, or facts; when uncertain, state uncertainty briefly and stay correct.\n'
                '18) Keep responses practical and accurate.'
            ),
        ),
        ('human', '{user_message}'),
    ])


def get_analysis_prompt_template():
    if not ChatPromptTemplate:
        return None

    return ChatPromptTemplate.from_messages([
        (
            'system',
            (
                'Analyze a learner message for tutoring cues. Return ONLY JSON object with keys: '
                'topics (list[string]), confusion_level (0..1), uncertainty_markers (int), '
                'misconception_detected (bool), misconception_detail (string|null), emotional_state (string), '
                'suggested_approach (string), mode_suggestion (string|null), confidence (0..1). '
                'Do not include markdown.'
            ),
        ),
        (
            'human',
            (
                'message: {user_message}\n'
                'keyword_topics: {keyword_topics}\n'
                'keyword_complexity: {keyword_complexity}\n'
                'keyword_question_type: {keyword_question_type}\n'
                'meta: {message_meta}\n'
                'knowledge_summary: {knowledge_summary}'
            ),
        ),
    ])


def mode_instruction(mode: str) -> str:
    return MODE_SYSTEM_INSTRUCTIONS.get(normalize_mode(mode), MODE_SYSTEM_INSTRUCTIONS['direct'])
