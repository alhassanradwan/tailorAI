"""
AdaptiveAI — Agent Router
Single entry point for:
  1. Topic routing  → DS / ML / DL agent
  2. Personalised system prompt construction
  3. Groq API call
  4. Inline analysis (no extra HTTP round-trip)
"""

import os
import time
import logging
from groq import Groq
from config import Config

from services.agents import AGENTS
from services.agents.analyzer import (
    extract_topics,
    detect_complexity,
    detect_question_type,
    message_meta,
    build_recommendations,
    finalize_tutoring_mode,
    analyze_with_llm,
)
from services.agents.prompt_builder import build_system_prompt, normalize_forced_mode
from services.agents.formatter import (
    format_general_response,
    format_structured_fallback,
    build_dynamic_response_payload,
)
from services.langchain.langchain_analyzer import LangChainAnalyzer
from services.langchain.langchain_generator import LangChainGenerator
from services.langchain.langchain_prompts import select_output_plan

logger = logging.getLogger(__name__)


class DeepAgentRouter:
    """
    Single entry-point for the AI tutoring pipeline:
        analyse → route → build prompt → call Groq → return
    """

    # ── routing ─────────────────────────────────────────────
    @staticmethod
    def route(query: str, knowledge_state: dict) -> str:
        """Return the best agent key for *query*."""
        lower  = query.lower()
        scores = {
            key: sum(1 for kw in cfg['keywords'] if kw in lower)
            for key, cfg in AGENTS.items()
        }
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
        strongest = knowledge_state.get('strongest_domain', 'machine_learning')
        return strongest.lower().replace(' ', '_') if strongest else 'machine_learning'

    # ── analysis ─────────────────────────────────────────────
    @staticmethod
    def analyze(client, message: str, knowledge_state: dict) -> dict:
        """
        Fast keyword analysis + LangChain/LLM fallback.
        Returns the unified analysis dict consumed downstream.
        """
        topics_kw     = extract_topics(message)
        complexity_kw = detect_complexity(message)
        qtype_kw      = detect_question_type(message)
        meta          = message_meta(message)

        method      = 'keywords'
        topics      = topics_kw
        complexity  = complexity_kw
        qtype       = qtype_kw
        llm_data    = None
        langchain_used            = False
        langchain_fallback_reason = None

        word_count  = meta.get('word_count', 0)
        uncertainty = meta.get('uncertainty_markers', 0)

        should_llm = (
            len(topics_kw) == 0
            or (word_count > 50 and len(topics_kw) < 2)
            or len(meta.get('misconception_signals', [])) > 0
            or (len(topics_kw) > 0 and meta.get('is_assertion', False))
            or (len(topics_kw) > 0 and uncertainty >= 1)
        )

        # Force LLM whenever quiz/exam/test appears — keyword matching cannot
        # distinguish "I have an exam" (context) from "give me an exam" (command).
        _AMBIGUOUS_INTENT_WORDS = {'quiz', 'exam', 'test', 'examine', 'assess', 'assessment'}
        if any(w in message.lower().split() for w in _AMBIGUOUS_INTENT_WORDS):
            should_llm = True

        print('USE_LANGCHAIN:', Config.USE_LANGCHAIN)
        print('should_llm:', should_llm)

        # ── LangChain analysis path ──────────────────────────
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
                    cues           = lc_result['cues']
                    langchain_used = True
                    method         = 'langchain_hybrid'
                    llm_data = {
                        'emotional_state':    cues.emotional_state,
                        'suggested_approach': cues.suggested_approach,
                        'is_misconception':   cues.misconception_detected,
                        'misconception_detail': cues.misconception_detail,
                        'question_type':  cues.question_type,
                        'user_intent':    cues.user_intent,
                    }
                    topics = list(set(topics_kw + (cues.topics or [])))
                    # Override qtype with LLM's more nuanced decision
                    qtype = cues.question_type
                    logger.info('analysis_path=langchain_hybrid intent=%s qtype=%s', cues.user_intent, cues.question_type)
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

        # ── Groq LLM fallback analysis ───────────────────────
        if should_llm and client and not langchain_used:
            llm_result = analyze_with_llm(client, message, knowledge_state)
            if llm_result:
                method     = 'hybrid'
                llm_data   = llm_result
                topics     = list(set(topics_kw + llm_result.get('topics', [])))
                complexity = llm_result.get('complexity', complexity_kw)
                qtype      = llm_result.get('question_type', qtype_kw)

        recs = build_recommendations(topics, complexity, qtype, knowledge_state, meta)

        if llm_data:
            recs['emotional_state']    = llm_data.get('emotional_state', 'neutral')
            recs['suggested_approach'] = llm_data.get('suggested_approach', 'explain_simply')
            if llm_data.get('is_misconception'):
                recs['misconception_detected'] = True
                recs['misconception_detail']   = llm_data.get('misconception_detail')
                recs['trigger_socratic_mode']  = True
            if llm_data.get('emotional_state') == 'confused' and topics:
                recs['trigger_socratic_mode'] = True
                if not recs.get('misconception_detected'):
                    recs['misconception_detected'] = True
                    recs['misconception_topic']    = topics[0]
                    recs['misconception_detail']   = (
                        f'LLM detected student confusion about {topics[0]}'
                    )

        recs = finalize_tutoring_mode(recs, knowledge_state, topics, meta)

        return {
            'topics':           topics,
            'complexity':       complexity,
            'question_type':    qtype,
            'user_intent':      llm_data.get('user_intent', 'learning') if llm_data else 'learning',  # ← NEW
            'analysis_method':  method,
            'message_analysis': meta,
            'recommendations':  recs,
            'confidence':       0.9 if method == 'hybrid' else 0.7,
            'langchain': {
                'used':            langchain_used,
                'fallback_reason': langchain_fallback_reason,
            },
        }
    

    # ── system prompt (thin wrapper kept for API compatibility) ─
    @staticmethod
    def build_system_prompt(
        agent_key: str,
        profile: dict,
        knowledge_state: dict,
        analysis: dict = None,
        forced_mode: str = None,
        forced_reason: str = None,
        rag_context: str = None,
    ) -> str:
        return build_system_prompt(
            agent_key, profile, knowledge_state, analysis,
            forced_mode, forced_reason, rag_context,
        )

    # ── orchestrator ─────────────────────────────────────────
    @staticmethod
    def generate(
        message: str,
        profile: dict,
        knowledge_state: dict,
        chat_history: list,
        user_id: str = None,
    ) -> dict:
        """
        Full pipeline:
            analyse → route → prompt → Groq API → format → return
        """
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {'success': False, 'error': 'Groq API key not configured'}

        client = Groq(api_key=api_key)
        t0     = time.time()

        # 1. analyse
        analysis  = DeepAgentRouter.analyze(client, message, knowledge_state)

        # 2. route
        agent_key = DeepAgentRouter.route(message, knowledge_state)

        # 2b. RAG retrieval (feature-flagged, fail-safe)
        rag_context          = None
        rag_used             = False
        rag_primary_concepts = []
        if Config.USE_RAG:
            try:
                from services.rag.rag_router import RAGRouter
                rag_result = RAGRouter.retrieve(
                    agent_key, message,
                    {'weak_topics': knowledge_state.get('weak_topics', [])},
                )
                if rag_result:
                    rag_context          = rag_result.get('formatted_context', '') or None
                    rag_primary_concepts = rag_result.get('primary_concepts', []) or []
                    if rag_context:
                        rag_used = True
                        logger.info(
                            'RAG context retrieved domain=%s concepts=%s',
                            agent_key, rag_result.get('primary_concepts', []),
                        )
            except Exception as e:
                logger.warning('RAG retrieval failed, continuing without: %s', e)

        # 3. resolve tutoring mode
        recs            = analysis.get('recommendations', {})
        response_mode   = (
            recs.get('tutoring_mode')
            or knowledge_state.get('current_adaptations', {}).get('tutoring_mode', 'direct')
        )
        response_reason = (
            recs.get('mode_reason')
            or knowledge_state.get('current_adaptations', {}).get('mode_reason', 'stable understanding detected')
        )

        forced_mode = normalize_forced_mode(
            profile.get('force_tutoring_mode')
            or profile.get('adaptive_preference')
            or (profile.get('conversation_preferences', {}) or {}).get('adaptive_preference')
        )
        if forced_mode:
            response_mode           = forced_mode
            response_reason         = 'user selected tutoring mode'
            recs['tutoring_mode']   = response_mode
            recs['mode_reason']     = response_reason

        logger.debug(
            'DeepAgentRouter.generate pre-prompt mode=%s reason=%s analysis_mode=%s',
            response_mode, response_reason, recs.get('tutoring_mode'),
        )

        # 4. build system prompt
        system_prompt = build_system_prompt(
            agent_key, profile, knowledge_state, analysis,
            forced_mode=response_mode,
            forced_reason=response_reason,
            rag_context=rag_context,
        )

        # 5. build messages list
        messages = [{'role': 'system', 'content': system_prompt}]
        for m in (chat_history or [])[-10:]:
            messages.append({
                'role':    m.get('role', 'user'),
                'content': m.get('content', ''),
            })
        messages.append({'role': 'user', 'content': message})

        recent_context  = ' | '.join(
            f"{m.get('role', 'user')}: {m.get('content', '')}"
            for m in (chat_history or [])[-4:]
        )
        topic_context   = ', '.join(analysis.get('topics', [])) or 'general'
        generation_plan = select_output_plan(
            question_type=analysis.get('question_type', 'general'),
            complexity=analysis.get('complexity', 'intermediate'),
            uncertainty_markers=(analysis.get('message_analysis', {}) or {}).get('uncertainty_markers', 0),
            has_code=(analysis.get('message_analysis', {}) or {}).get('has_code', False),
            topic_context=topic_context,
            recent_context=recent_context,
            user_message=message,
        )

        structured_intents       = {'comparison', 'examples', 'use_cases', 'multi_idea'}
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

        # 6. LangChain generation path (feature-flagged)
        print('attempting_langchain_generation:', bool(use_langchain_generation))
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
                    print('generation_path: langchain')
                    print('generation_fallback_reason:', None)
                    logger.info('generation_path=langchain mode=%s', response_mode)
                    return {
                        'success':          True,
                        'response':         lc_result['response'],
                        'agent':            agent_key,
                        'agent_name':       AGENTS[agent_key]['label'],
                        'tokens_used':      lc_result.get('tokens_used', 0),
                        'response_time_ms': elapsed,
                        'analysis':         analysis,
                        'tutoring_mode':    response_mode,
                        'mode_reason':      response_reason,
                        'generation': {
                            'path':               'langchain',
                            'langchain_used':      True,
                            'rag_used':            rag_used,
                            'rag_primary_concepts': rag_primary_concepts,
                            'structured_required': bool(generation_plan.get('structured_response_required', False)),
                            'structured_intent':   generation_plan.get('structured_intent'),
                            'intent':              generation_plan.get('intent'),
                            'sections':            lc_result.get('sections', []),
                            'formatter_applied':   bool(lc_result.get('formatter_applied', False)),
                            'formatter_reason':    lc_result.get('formatter_reason'),
                            'fallback_reason':     None,
                        },
                        'dynamic_response': lc_result.get('dynamic_response') or build_dynamic_response_payload(
                            response_text=lc_result['response'],
                            intent=(
                                generation_plan.get('intent')
                                or generation_plan.get('structured_intent')
                                or 'general_fallback'
                            ),
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

        # 7. Groq native fallback path
        try:
            completion = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=messages,
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
            )
            response_text = completion.choices[0].message.content
            tokens_used   = completion.usage.total_tokens if completion.usage else 0
        except Exception as e:
            logger.error('Groq API call failed: %s', e)
            return {'success': False, 'error': str(e)}

        # 8. format response
        formatter_applied = False
        formatter_reason  = None
        structured_intent = generation_plan.get('structured_intent')

        if not Config.DYNAMIC_CHAT_SCHEMA_ENABLED and generation_plan.get('structured_response_required', False):
            response_text, formatter_applied, formatter_reason = format_structured_fallback(
                response_text, structured_intent,
            )
        if not Config.DYNAMIC_CHAT_SCHEMA_ENABLED and not formatter_applied:
            response_text, formatter_applied, formatter_reason = format_general_response(response_text)

        dynamic_response = build_dynamic_response_payload(
            response_text=response_text,
            intent=(generation_plan.get('intent') or structured_intent or 'general_fallback'),
            confidence=float(generation_plan.get('confidence', 0.0) or 0.0),
            fallback_used=bool(generation_fallback_reason),
            fallback_reason=generation_fallback_reason,
        )

        elapsed = round((time.time() - t0) * 1000)
        print('generation_path: fallback')
        print('generation_fallback_reason:', generation_fallback_reason)
        logger.info('generation_path=fallback_native_groq mode=%s', response_mode)

        return {
            'success':          True,
            'response':         response_text,
            'agent':            agent_key,
            'agent_name':       AGENTS[agent_key]['label'],
            'tokens_used':      tokens_used,
            'response_time_ms': elapsed,
            'analysis':         analysis,
            'tutoring_mode':    response_mode,
            'mode_reason':      response_reason,
            'generation': {
                'path':               'native_groq',
                'langchain_used':      False,
                'rag_used':            rag_used,
                'rag_primary_concepts': rag_primary_concepts,
                'structured_required': bool(generation_plan.get('structured_response_required', False)),
                'structured_intent':   generation_plan.get('structured_intent'),
                'intent':              generation_plan.get('intent'),
                'sections':            generation_plan.get('sections', []),
                'formatter_applied':   formatter_applied,
                'formatter_reason':    formatter_reason,
                'fallback_reason':     generation_fallback_reason,
            },
            'dynamic_response': dynamic_response,
        }
