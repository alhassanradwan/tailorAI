"""LangChain prompt templates for tutoring and structured analysis."""

import re
from config import Config

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

INTENT_OUTPUT_PLANS = {
    'definition_explanation': {
        'sections': ['explanation', 'examples'],
        'structured_intent': 'examples',
    },
    'how_to_steps': {
        'sections': ['explanation', 'steps'],
        'structured_intent': None,
    },
    'comparison_choice': {
        'sections': ['explanation', 'table'],
        'structured_intent': 'comparison',
    },
    'debugging_fix': {
        'sections': ['explanation', 'steps', 'code'],
        'structured_intent': None,
    },
    'code_generation': {
        'sections': ['explanation', 'code'],
        'structured_intent': None,
    },
    'code_explanation': {
        'sections': ['explanation', 'code'],
        'structured_intent': None,
    },
    'concept_quiz': {
        'sections': ['explanation', 'practice'],
        'structured_intent': None,
    },
    'recap_summarize': {
        'sections': ['explanation', 'steps'],
        'structured_intent': None,
    },
    'roadmap_learning_plan': {
        'sections': ['explanation', 'options', 'practice'],
        'structured_intent': 'multi_idea',
    },
    'general_fallback': {
        'sections': ['explanation'],
        'structured_intent': None,
    },
}


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


def detect_dynamic_intent(question_type: str, user_message: str, has_code: bool) -> str:
    qtype = (question_type or 'general').strip().lower()
    msg = (user_message or '').strip().lower()

    if re.search(r'\b(compare|comparison|difference|vs\.?|versus|which is better)\b', msg) or qtype == 'comparison':
        return 'comparison_choice'
    if re.search(r'\b(debug|error|traceback|exception|fix|bug|fails?|not working)\b', msg) or qtype == 'debugging':
        return 'debugging_fix'
    if re.search(r'\b(write code|build code|generate code|code example|snippet)\b', msg) or qtype == 'code_request':
        return 'code_generation'
    if re.search(r'\b(explain this code|what does this code|walk me through code)\b', msg):
        return 'code_explanation'
    if re.search(r'\b(quiz|test me|ask me questions?|practice questions?)\b', msg):
        return 'concept_quiz'
    if re.search(r'\b(roadmap|study plan|learning plan|how should i learn|path to learn)\b', msg):
        return 'roadmap_learning_plan'
    if re.search(r'\b(summarize|summary|recap|tl;dr)\b', msg):
        return 'recap_summarize'
    if re.search(r'\b(how to|steps|step by step|implement)\b', msg) or qtype == 'how_to':
        return 'how_to_steps'
    if re.search(r'\b(what is|define|explain|meaning of)\b', msg) or qtype in {'definition', 'why'}:
        return 'definition_explanation'
    if has_code:
        return 'code_explanation'
    return 'general_fallback'


def select_dynamic_output_plan(
    intent: str,
    uncertainty_markers: int,
    complexity: str,
) -> dict:
    intent_key = intent if intent in INTENT_OUTPUT_PLANS else 'general_fallback'
    preset = INTENT_OUTPUT_PLANS[intent_key]
    sections = list(preset['sections'])

    if int(uncertainty_markers or 0) >= 2 and 'practice' not in sections:
        sections.append('practice')

    max_sections = 4
    if len(sections) > max_sections:
        sections = sections[:max_sections]

    return {
        'intent': intent_key,
        'sections': sections,
        'max_sections': max_sections,
        'max_questions': 1,
        'structured_response_required': preset['structured_intent'] is not None,
        'structured_intent': preset['structured_intent'],
        'confusion_state': int(uncertainty_markers or 0) >= 2,
        'rationale': f'dynamic_intent_router:{intent_key}; complexity:{normalize_level(complexity)}',
        'confidence': 0.65,
    }


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
    if Config.DYNAMIC_INTENT_ROUTER_ENABLED:
        intent = detect_dynamic_intent(
            question_type=question_type,
            user_message=user_message,
            has_code=has_code,
        )
        return select_dynamic_output_plan(
            intent=intent,
            uncertainty_markers=uncertainty_markers,
            complexity=complexity,
        )

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
    multi_idea_intent = bool(
        re.search(r'\b(ideas|options|approaches|ways|alternatives|multiple|different methods|tradeoffs?)\b', msg)
    )

    structured_intent = None
    if comparison_intent:
        structured_intent = 'comparison'
    elif use_cases_intent:
        structured_intent = 'use_cases'
    elif examples_intent:
        structured_intent = 'examples'
    elif multi_idea_intent:
        structured_intent = 'multi_idea'

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
    elif structured_intent == 'multi_idea':
        include.append('options')
        rationale.append('structured intent: multiple organized options required')
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
    elif structured_intent == 'multi_idea':
        include_final.append('options')
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

    if 'options' in sec:
        return (
            'FORMAT CONTRACT: 1) Short context/setup. '
            '2) Options section with 3-5 clearly named options as bullets or numbered list. '
            '3) For each option, include when to use and one tradeoff. '
            '4) End with a concise recommendation.'
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
                'Retrieved knowledge graph context: {rag_context}\n'
                'Output plan sections: {output_sections}\n'
                'Output selection rationale: {output_rationale}\n'
                'Response contract: {response_contract}\n'
                'Code style profile: {code_style_profile}\n'
                'Safety defaults: learner_level={safe_learner_level}, tutoring_mode={safe_tutoring_mode}\n'
                'CRITICAL OUTPUT RULES:\n'
                '1) Use at most {max_sections} sections.\n'
                '2) Always include an explanation section.\n'
                '3) Include only the most relevant supporting element (code OR visual OR analogy OR table).\n'
                '4) NEVER generate any practice questions or quiz questions here. Skip the practice section entirely.\n'
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
                '16) NO QUIZZES IN CHAT: If the user asks for a quiz, test, or practice questions, DO NOT generate actual quiz questions in your response. Instead, respond ONLY with exactly: "I\'ve prepared a tailored Knowledge Check for you! Opening the quiz now..."\n'
                '16) For advanced learners, keep technical depth high and avoid oversimplifying unless the learner asks to simplify.\n'
                '17) Never hallucinate APIs, libraries, papers, or facts; when uncertain, state uncertainty briefly and stay correct.\n'
                '18) Keep responses practical and accurate.\n'
                '19) If retrieved knowledge graph context is present, use it to ground your explanation and examples.\n'
                '20) Do not copy retrieved context verbatim; teach it in your own words and only use relevant parts.'
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
                'You are an analysis engine for an adaptive AI tutoring system. '
                'Analyze the learner message and return ONLY a JSON object (no markdown, no explanation).\n\n'
                'MISCONCEPTION DETECTION (critical):\n'
                'Set misconception_detected=true if the student:\n'
                '- States something factually incorrect about a technical concept\n'
                '- Confuses two different concepts (e.g., "overfitting is the same as high variance")\n'
                '- Uses absolute/wrong claims ("gradient descent always converges", "CNNs only work for images")\n'
                '- Shows a fundamental misunderstanding even in how they ask a question\n'
                '- Repeatedly asks the same basic question (signals hidden confusion)\n'
                'If misconception_detected=true, misconception_detail MUST explain what is wrong and what is correct.\n\n'
                'INTENT DETECTION (critical — read carefully):\n'
                'You must distinguish between a quiz/exam as CONTEXT vs as a COMMAND.\n'
                '- CONTEXT: Student mentions exam/quiz/test as motivation ("I have a test tomorrow", '
                '"explain CNNs because I have an exam", "studying for my quiz") → user_intent="learning", question_type="definition" or "how_to"\n'
                '- COMMAND: Student directly requests to be tested ("give me a quiz", "test me on this", '
                '"quiz time", "can you examine me", "give me practice questions") → user_intent="testing", question_type="quiz"\n'
                'The key signal is imperative/action language ("give me", "test me", "start") vs explanatory context ("because", "for", "since", "I have").\n'
                'and take care not to misclassify a student saying "I have an exam tomorrow, can you explain X for my exam?" as a quiz request. This is a learning intent, not a testing intent.\n\n'
                'and also doesn not mean when a student says "explain X because for example TA will give me exam tomorrow", it is not a quiz request, it is a learning request.\n\n'
                '"Explain X for my exam" is NOT a quiz request. "Give me an exam on X" IS.\n\n'
                'JSON keys:\n'
                '- topics: list[string] — technical topics in the message (lowercase_with_underscores)\n'
                '- confusion_level: float 0..1 — how confused the student seems\n'
                '- uncertainty_markers: int — count of uncertainty phrases\n'
                '- misconception_detected: bool — see rules above\n'
                '- misconception_detail: string|null — what is wrong and what is correct\n'
                '- emotional_state: "confident"|"curious"|"confused"|"frustrated"|"neutral"\n'
                '- suggested_approach: "explain_simply"|"provide_examples"|"use_analogy"|"show_code"|"ask_questions"|"correct_misconception"\n'
                '- mode_suggestion: string|null — "socratic" if misconception or confusion detected\n'
                '- confidence: float 0..1 — your confidence in this analysis\n'
                '- question_type: "definition"|"how_to"|"why"|"comparison"|"debugging"|"code_request"|"quiz"|"general"\n'
                '- user_intent: "learning"|"testing"'
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
