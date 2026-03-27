"""LangChain tutor response generation with strict fallback behavior."""

import logging
import re

from services.langchain_provider import LangChainProvider
from services.langchain_prompts import (
    get_tutor_prompt_template,
    mode_instruction,
    normalize_level,
    normalize_mode,
    response_contract,
    select_code_style_profile,
    select_output_plan,
)

logger = logging.getLogger(__name__)


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r'\n\s*\n+', text or '') if p.strip()]


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?])\s+', (text or '').strip())
    return [c.strip() for c in chunks if c.strip()]


def _has_table_shape(text: str) -> bool:
    lines = [ln for ln in (text or '').splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    table_like = sum(1 for ln in lines if '|' in ln)
    return table_like >= 2


def _has_comparison_section(text: str) -> bool:
    return bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s*)?comparison\s*:?', text or ''))


def _example_count(text: str) -> int:
    explicit = re.findall(r'(?im)^\s*(?:[-*]\s*)?example\s*\d*[:\-]?', text or '')
    if len(explicit) >= 2:
        return len(explicit)
    phrase_hits = len(re.findall(r'(?i)\bfor example\b', text or ''))
    numbered_hits = len(re.findall(r'(?i)\bexample\s*\d+\b', text or ''))
    return max(len(explicit), phrase_hits + numbered_hits)


def _has_examples_section(text: str) -> bool:
    return bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s*)?examples\s*:?', text or ''))


def _contains_examples(text: str) -> bool:
    return _has_examples_section(text) and _example_count(text) >= 2


def _contains_use_case_sections(text: str) -> bool:
    has_when_to_use = bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s*)?when to use\s*:?', text or ''))
    has_when_not = bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s*)?when not to use\s*:?', text or ''))
    return has_when_to_use and has_when_not


def _format_comparison(text: str) -> str:
    paragraphs = _split_paragraphs(text)
    explanation = paragraphs[0] if paragraphs else (text or '').strip()
    remainder = '\n\n'.join(paragraphs[1:]).strip() if len(paragraphs) > 1 else ''
    if not remainder:
        remainder = (text or '').strip()

    return (
        'Explanation\n'
        f'{explanation}\n\n'
        'Comparison\n'
        f'{remainder}'
    ).strip()


def _format_examples(text: str) -> str:
    paragraphs = _split_paragraphs(text)
    explanation = paragraphs[0] if paragraphs else (text or '').strip()
    source = '\n\n'.join(paragraphs[1:]).strip() if len(paragraphs) > 1 else (text or '').strip()
    sentences = _split_sentences(source)

    if len(sentences) >= 2:
        ex1 = sentences[0]
        ex2 = sentences[1]
    elif len(sentences) == 1:
        ex1 = sentences[0]
        ex2 = sentences[0]
    else:
        ex1 = source or explanation
        ex2 = source or explanation

    return (
        'Explanation\n'
        f'{explanation}\n\n'
        'Examples\n'
        f'- Example 1: {ex1}\n'
        f'- Example 2: {ex2}'
    ).strip()


def _format_use_cases(text: str) -> str:
    paragraphs = _split_paragraphs(text)
    explanation = paragraphs[0] if paragraphs else (text or '').strip()
    source = '\n\n'.join(paragraphs[1:]).strip() if len(paragraphs) > 1 else (text or '').strip()
    sentences = _split_sentences(source)

    midpoint = max(1, len(sentences) // 2) if sentences else 1
    when_to_use = ' '.join(sentences[:midpoint]).strip() if sentences else source
    when_not_to_use = ' '.join(sentences[midpoint:]).strip() if len(sentences) > midpoint else source

    return (
        'Explanation\n'
        f'{explanation}\n\n'
        'When to Use\n'
        f'{when_to_use}\n\n'
        'When Not to Use\n'
        f'{when_not_to_use}'
    ).strip()


def _enforce_structured_output(text: str, plan: dict) -> str:
    if not (plan or {}).get('structured_response_required'):
        return text

    structured_intent = (plan or {}).get('structured_intent')
    content = (text or '').strip()
    if not content:
        return content

    if structured_intent == 'comparison':
        if _has_table_shape(content) or _has_comparison_section(content):
            return content
        return _format_comparison(content)

    if structured_intent == 'examples':
        if _contains_examples(content):
            return content
        return _format_examples(content)

    if structured_intent == 'use_cases':
        if _contains_use_case_sections(content):
            return content
        return _format_use_cases(content)

    return content


class LangChainGenerator:
    @staticmethod
    def generate_response(
        tutoring_mode: str,
        user_message: str,
        learner_level: str,
        strong_topics: list[str],
        weak_topics: list[str],
        misconceptions: list[str],
        recent_context: str,
        topic_context: str,
        question_type: str = 'general',
        complexity: str = 'intermediate',
        uncertainty_markers: int = 0,
        has_code: bool = False,
    ) -> dict:
        if not LangChainProvider.is_enabled():
            return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'feature_flag_disabled'}

        prompt = get_tutor_prompt_template()
        if not prompt:
            return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'provider_or_prompt_unavailable'}

        try:
            safe_mode = normalize_mode(tutoring_mode)
            safe_level = normalize_level(learner_level)
            plan = select_output_plan(
                question_type=question_type,
                complexity=complexity,
                uncertainty_markers=uncertainty_markers,
                has_code=has_code,
                topic_context=topic_context,
                recent_context=recent_context,
                user_message=user_message,
            )
            code_style_profile = select_code_style_profile(
                learner_level=safe_level,
                question_type=question_type,
                has_code=has_code,
            )
            sections = plan.get('sections', ['explanation'])
            code_focused = 'code' in sections
            temperature = 0.2 if code_focused else 0.7
            model = LangChainProvider.create_chat_model(temperature=temperature, max_tokens=1024)
            if not model:
                return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'provider_or_prompt_unavailable'}

            messages = prompt.format_messages(
                mode_instruction=mode_instruction(safe_mode),
                learner_level=safe_level,
                strong_topics=', '.join(strong_topics) if strong_topics else 'None',
                weak_topics=', '.join(weak_topics) if weak_topics else 'None',
                misconceptions=', '.join(misconceptions) if misconceptions else 'None',
                recent_context=recent_context or 'None',
                topic_context=topic_context or 'None',
                output_sections=' + '.join(sections),
                output_rationale=plan.get('rationale', 'default explanation-first plan'),
                response_contract=response_contract(question_type=question_type, sections=sections),
                code_style_profile=code_style_profile,
                safe_learner_level=safe_level,
                safe_tutoring_mode=safe_mode,
                max_sections=plan.get('max_sections', 4),
                max_questions=plan.get('max_questions', 1),
                user_message=user_message,
            )
            result = model.invoke(messages)
            response_text = (getattr(result, 'content', '') or '').strip()
            if not response_text:
                return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'empty_response'}

            response_text = _enforce_structured_output(response_text, plan)

            usage = getattr(result, 'response_metadata', {}) or {}
            token_usage = usage.get('token_usage', {}) if isinstance(usage, dict) else {}
            tokens_used = token_usage.get('total_tokens', 0) if isinstance(token_usage, dict) else 0

            return {'used': True, 'response': response_text, 'tokens_used': int(tokens_used or 0), 'error': None}
        except Exception as e:
            logger.warning('LangChain generator failed: %s', e)
            return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'invoke_failed'}
