"""LangChain-based analyzer with schema-safe parsing and hard fallback."""

import json
import logging
from pydantic import ValidationError

from services.langchain_provider import LangChainProvider
from services.langchain_prompts import get_analysis_prompt_template
from services.langchain_schemas import LangChainAnalysisCues, default_analysis_cues

logger = logging.getLogger(__name__)


def _extract_json_object(text: str):
    if not text:
        return None

    candidate = text.strip()
    if candidate.startswith('```'):
        candidate = candidate.strip('`')
        candidate = candidate.replace('json', '', 1).strip()

    try:
        return json.loads(candidate)
    except Exception:
        pass

    start = candidate.find('{')
    end = candidate.rfind('}')
    if start != -1 and end != -1 and end > start:
        snippet = candidate[start:end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            return None
    return None


class LangChainAnalyzer:
    @staticmethod
    def analyze_message(
        user_message: str,
        keyword_topics: list[str],
        keyword_complexity: str,
        keyword_question_type: str,
        message_meta: dict,
        knowledge_state: dict,
    ) -> dict:
        if not LangChainProvider.is_enabled():
            return {'used': False, 'cues': default_analysis_cues(), 'error': 'feature_flag_disabled'}

        model = LangChainProvider.create_chat_model(temperature=0.1, max_tokens=320)
        prompt = get_analysis_prompt_template()
        if not model or not prompt:
            return {'used': False, 'cues': default_analysis_cues(), 'error': 'provider_or_prompt_unavailable'}

        knowledge_summary = {
            'skill_level': knowledge_state.get('skill_level', 'intermediate'),
            'strong_topics': knowledge_state.get('strong_topics', []),
            'weak_topics': knowledge_state.get('weak_topics', []),
        }

        try:
            messages = prompt.format_messages(
                user_message=user_message,
                keyword_topics=keyword_topics,
                keyword_complexity=keyword_complexity,
                keyword_question_type=keyword_question_type,
                message_meta=message_meta,
                knowledge_summary=knowledge_summary,
            )
            response = model.invoke(messages)
            content = getattr(response, 'content', '') or ''

            raw_json = _extract_json_object(content)
            if raw_json is None:
                logger.warning('LangChain analyzer parse failed: no JSON object')
                return {'used': False, 'cues': default_analysis_cues(), 'error': 'parse_failed'}

            cues = LangChainAnalysisCues.model_validate(raw_json)
            return {'used': True, 'cues': cues, 'error': None}
        except ValidationError as e:
            logger.warning('LangChain analyzer schema validation failed: %s', e)
            return {'used': False, 'cues': default_analysis_cues(), 'error': 'schema_validation_failed'}
        except Exception as e:
            logger.warning('LangChain analyzer failed: %s', e)
            return {'used': False, 'cues': default_analysis_cues(), 'error': 'invoke_failed'}
