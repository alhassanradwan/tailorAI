import os
import logging
import re
from typing import Optional

from groq import Groq
from database import Database
from services.knowledge_state import KnowledgeStateService
from services.rag.rag_router import RAGRouter
from services.quiz.rag_resolver import topic_to_agent_key
from services.quiz.wrong_answer_store import WrongAnswerStore
from services.quiz.generation_agent import QuizGenerationAgent

logger = logging.getLogger(__name__)


class QuizService:
    # ── context ──────────────────────────────────────────────────────────────

    @staticmethod
    def gather_quiz_context(user_id: str, limit: int = 20) -> dict:
        interactions = Database.get_collection("interactions")
        history_cursor = (
            interactions
            .find(
                {"user_id": user_id},
                {"_id": 0, "user_message": 1, "ai_response": 1, "analysis": 1},
            )
            .sort("timestamp", -1)
            .limit(limit)
        )
        chat_history = list(history_cursor)[::-1]   # chronological order

        ks            = KnowledgeStateService.get(user_id)
        weak_topics   = ks.get("weak_topics",   [])
        recent_topics = ks.get("recent_topics", [])

        return {
            "chat_history":  chat_history,
            "weak_topics":   weak_topics,
            "recent_topics": recent_topics,
        }

    # ── count extraction ──────────────────────────────────────────────────────

    @staticmethod
    def extract_requested_count(user_prompt: str) -> Optional[int]:
        if not user_prompt:
            return None
        patterns = [
            r'\b(\d+)\s+questions?\b',
            r'\bquiz\s+of\s+(\d+)\b',
            r'\b(\d+)[- ]question\b',
            r'\bgive\s+me\s+(\d+)\b',
            r'\bmake\s+(\d+)\b',
            r'\bcreate\s+(\d+)\b',
            r'\bgenerate\s+(\d+)\b',
            r'\bwant\s+(\d+)\b',
            r'\b(\d+)\s+mcq\b',
        ]
        for pat in patterns:
            m = re.search(pat, user_prompt, re.IGNORECASE)
            if m:
                count = int(m.group(1))
                if 1 <= count <= 50:
                    return count
        return None

    # ── topic extraction ──────────────────────────────────────────────────────

    @staticmethod
    def extract_topic_from_prompt(user_prompt: str) -> Optional[str]:
        """Use LLM to determine if the user requested a specific quiz topic."""
        if not user_prompt:
            return None

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return None

        client = Groq(api_key=api_key)
        system = (
            "You are a helpful assistant. The user is asking for a quiz. "
            "Extract the specific topic they want to be quizzed on. "
            "If they just ask for a general quiz without specifying a topic, return 'NONE'. "
            "Output ONLY the topic string, nothing else."
        )
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=50,
            )
            result = resp.choices[0].message.content.strip()
            return None if result.upper() == "NONE" else result
        except Exception as e:
            logger.error("Failed to extract topic from prompt: %s", e)
            return None

    # ── generation entry-point ────────────────────────────────────────────────

    @staticmethod
    def generate_quiz(
        user_id:        str,
        topic:          str  = None,
        trigger_reason: str  = "direct_request",
        profile:        dict = None,
        user_prompt:    str  = "",
    ) -> dict:
        
        # ── 1. Extract explicit count from user message ───────────────────────
        user_requested_count = QuizService.extract_requested_count(user_prompt)
        if user_requested_count:
            logger.info("[QuizService] User requested exactly %d questions.", user_requested_count)

        # ── 2. Extract explicit topic from user message ───────────────────────
        if not topic and user_prompt:
            extracted = QuizService.extract_topic_from_prompt(user_prompt)
            if extracted:
                topic = extracted
                logger.info("[QuizService] Extracted explicit topic '%s'.", topic)

        # ── 3. Gather chat context ────────────────────────────────────────────
        context       = QuizService.gather_quiz_context(user_id)
        chat_history  = context["chat_history"]
        weak_topics   = context["weak_topics"]
        recent_topics = context["recent_topics"]

        unique_history_topics: list[str] = []
        for msg in reversed(chat_history):
            for t in msg.get("analysis", {}).get("topics", []):
                if t not in unique_history_topics:
                    unique_history_topics.append(t)

        # ── 4. Resolve primary topic & source_topics ─────────────────────────
        if topic:
            source_topics: list[str] = []
        else:
            candidate_pool: list[str] = []
            for t in unique_history_topics:
                if t not in candidate_pool:
                    candidate_pool.append(t)
            for t in weak_topics:
                if t not in candidate_pool:
                    candidate_pool.append(t)
            for t in recent_topics:
                if t not in candidate_pool:
                    candidate_pool.append(t)

            if candidate_pool:
                topic         = candidate_pool[0]
                source_topics = candidate_pool[1:8]
            else:
                topic         = "General Machine Learning"
                source_topics = []

        # ── 5. RAG similarity search for all topics ───────────────────────────
        all_topics   = list(dict.fromkeys([topic] + source_topics))
        rag_contexts: dict = {}
        student_ctx  = {"weak_topics": [wt.lower() for wt in weak_topics]}

        for t in all_topics:
            agent_key = topic_to_agent_key(t)
            rag_query = f"key concepts, techniques, and definitions in {t}"
            try:
                rag_result = RAGRouter.retrieve(
                    agent_key       = agent_key,
                    query           = rag_query,
                    student_context = student_ctx,
                )
                if rag_result:
                    rag_contexts[t] = rag_result
                    logger.info(
                        "[QuizService] RAG retrieved %d concepts for topic='%s' (agent=%s)",
                        len(rag_result.get("concepts", [])), t, agent_key,
                    )
            except Exception as e:
                logger.warning("[QuizService] RAG lookup failed for topic='%s': %s", t, e)

        # ── 6. Fetch past quizzes for repeat-prevention ───────────────────────
        quizzes_coll = Database.get_collection("quizzes")
        past_quizzes = list(
            quizzes_coll
            .find({"user_id": user_id, "status": "completed"})
            .sort("created_at", -1)
            .limit(10)
        )
        past_correct: list[str] = []
        for pq in past_quizzes:
            answers = pq.get("answers_submitted") or {}
            for q in pq.get("questions", []):
                q_id        = q.get("question_id", "")
                correct_ans = q.get("correct_answer", "")
                user_ans    = answers.get(q_id, "")
                if not user_ans or user_ans.strip().upper() == correct_ans:
                    past_correct.append(q.get("question", ""))

        # ── 7. Load persistent wrong-answer records ───────────────────────────
        wrong_answer_records = WrongAnswerStore.get_for_user(user_id, limit=15)
        logger.info(
            "[QuizService] %d pending wrong-answer records for user=%s",
            len(wrong_answer_records), user_id,
        )

        # ── 8. Delegate to generation agent ──────────────────────────────────
        is_explicit_topic = (len(source_topics) == 0 and topic != "General Machine Learning")

        agent = QuizGenerationAgent()
        quiz  = agent.generate(
            user_id              = user_id,
            topic                = topic,
            trigger              = trigger_reason,
            profile              = profile or {},
            chat_history         = chat_history,
            weak_topics          = weak_topics,
            source_topics        = source_topics,
            past_correct         = past_correct,
            wrong_answer_records = wrong_answer_records,
            rag_contexts         = rag_contexts,
            user_requested_count = user_requested_count,
            is_explicit_topic    = is_explicit_topic,
        )

        logger.info(
            "[QuizService] Quiz '%s' generated for user '%s' "
            "(trigger=%s, questions=%d, rag_topics=%d)",
            quiz["quiz_id"], user_id, trigger_reason,
            quiz["total_questions"], len(rag_contexts),
        )
        return quiz
