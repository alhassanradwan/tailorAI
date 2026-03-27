"""LangChain tutor response generation with strict fallback behavior."""

import logging

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

            usage = getattr(result, 'response_metadata', {}) or {}
            token_usage = usage.get('token_usage', {}) if isinstance(usage, dict) else {}
            tokens_used = token_usage.get('total_tokens', 0) if isinstance(token_usage, dict) else 0

            return {'used': True, 'response': response_text, 'tokens_used': int(tokens_used or 0), 'error': None}
        except Exception as e:
            logger.warning('LangChain generator failed: %s', e)
            return {'used': False, 'response': '', 'tokens_used': 0, 'error': 'invoke_failed'}
