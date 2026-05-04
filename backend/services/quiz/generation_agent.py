"""
services/quiz/generation_agent.py
QuizGenerationAgent — LLM orchestration, validation, submission, and persistence.
"""

import os
import json
import logging
from typing import Optional
from datetime import datetime

from groq import Groq
from database import Database
from services.knowledge_state import KnowledgeStateService
from services.quiz.config import question_count as auto_question_count, time_limit
from services.quiz.schema import build_quiz_schema
from services.quiz.prompts import SYSTEM_PROMPT, build_user_prompt
from services.quiz.wrong_answer_store import WrongAnswerStore

try:
    from services.knowledge_graph import KnowledgeGraphService
except ImportError:
    class KnowledgeGraphService:
        def get_context(self, topic: str):
            return {
                "domain": "general",
                "difficulty": "intermediate",
                "summary": "Mock summary",
                "kg_available": False,
                "concepts": [],
                "relationships": [],
                "prerequisites": [],
            }

logger = logging.getLogger(__name__)


class QuizGenerationAgent:

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set.")
        self.MODEL       = "llama-3.3-70b-versatile"
        self.TEMPERATURE = 0.7
        self.MAX_TOKENS  = 4096
        self.client      = Groq(api_key=api_key)
        self.kg          = KnowledgeGraphService()


    def generate(
        self,
        user_id:              str,
        topic:                str,
        trigger:              str           = "manual",
        profile:              dict          = None,
        chat_history:         list          = None,
        weak_topics:          list          = None,
        source_topics:        list          = None,
        past_correct:         list          = None,
        wrong_answer_records: list          = None,
        rag_contexts:         dict          = None,
        user_requested_count: Optional[int] = None,
        is_explicit_topic:    bool          = False,
    ) -> dict:
        """Generate, validate, persist and return a quiz document."""
        profile              = profile              or {}
        chat_history         = chat_history         or []
        weak_topics          = weak_topics          or []
        source_topics        = source_topics        or []
        past_correct         = past_correct         or []
        wrong_answer_records = wrong_answer_records or []
        rag_contexts         = rag_contexts         or {}

        all_topics = list(dict.fromkeys([topic] + source_topics))
        difficulty = self._resolve_difficulty(profile)

        kg_contexts: dict = {}
        any_live = False
        logger.info("[QuizAgent] Fetching legacy KG for %d topic(s): %s",
                    len(all_topics), all_topics)
        for t in all_topics:
            try:
                ctx = self.kg.get_context(t)
            except Exception as e:
                logger.warning("[QuizAgent] KG lookup failed for '%s': %s", t, e)
                ctx = {
                    "domain": "general", "difficulty": difficulty,
                    "summary": f"Fallback for {t}", "kg_available": False,
                    "concepts": [], "relationships": [], "prerequisites": [],
                }
            kg_contexts[t] = ctx
            if ctx.get("kg_available"):
                any_live = True

        if rag_contexts:
            any_live = True

        if user_requested_count is not None:
            n_questions = user_requested_count
        else:
            n_questions = auto_question_count(
                trigger         = trigger,
                n_source_topics = len(all_topics),
                kg_ctx          = kg_contexts.get(topic, {}),
            )
        time_limit_mins = time_limit(n_questions)

        user_prompt = build_user_prompt(
            primary_topic        = topic,
            source_topics        = all_topics,
            question_count       = n_questions,
            user_requested_count = user_requested_count,
            difficulty           = difficulty,
            profile              = profile,
            weak_topics          = weak_topics,
            trigger              = trigger,
            kg_contexts          = kg_contexts,
            rag_contexts         = rag_contexts,
            past_correct         = past_correct,
            wrong_answer_records = wrong_answer_records,
            is_explicit_topic    = is_explicit_topic,
        )

        raw       = self._call_groq(SYSTEM_PROMPT, user_prompt)
        questions = self._validate(raw)

        if not questions:
            raise ValueError("[QuizAgent] LLM failed to generate any valid questions.")

        if user_requested_count is not None and len(questions) != user_requested_count:
            logger.warning(
                "[QuizAgent] LLM returned %d questions but user requested %d — trimming.",
                len(questions), user_requested_count,
            )
            questions = questions[:user_requested_count]

        # ── Assemble & persist ────────────────────────────────────────────────
        quiz = build_quiz_schema(
            user_id            = user_id,
            topic              = topic,
            trigger            = trigger,
            difficulty         = difficulty,
            questions          = questions,
            time_limit_minutes = time_limit_mins,
            kg_available       = any_live,
            source_topics      = all_topics,
        )
        self._save(quiz)
        return quiz

    # ── submission / grading ──────────────────────────────────────────────────

    @staticmethod
    def submit_answers(quiz_id: str, answers: dict) -> dict:
        """
        Grade submitted answers, update MongoDB, update WrongAnswerStore,
        update KnowledgeState, return enriched graded quiz.

        Parameters
        ----------
        quiz_id : The quiz UUID
        answers : {"q1": "B", "q2": "A", …}

        Returns
        -------
        Updated quiz dict with score, correct answers revealed,
        and wrong_details list for post-quiz chat explanations.
        """
        quizzes = Database.get_collection("quizzes")
        quiz    = quizzes.find_one({"quiz_id": quiz_id}, {"_id": 0})

        if not quiz:
            raise ValueError(f"Quiz '{quiz_id}' not found.")
        if quiz["status"] == "completed":
            raise ValueError(f"Quiz '{quiz_id}' already submitted.")

        user_id       = quiz["user_id"]
        wrong_details: list[dict] = []

        for q in quiz["questions"]:
            q_id        = q["question_id"]
            correct_ans = q["correct_answer"]
            user_ans    = answers.get(q_id, "").strip().upper()

            if user_ans == correct_ans:
                WrongAnswerStore.delete_if_now_correct(user_id, q["question"])
            elif user_ans:
                WrongAnswerStore.upsert(user_id, quiz_id, q, user_ans)
                wrong_details.append({
                    "question":       q["question"],
                    "options":        q["options"],
                    "correct_answer": correct_ans,
                    "user_answer":    user_ans,
                    "explanation":    q.get("explanation", ""),
                    "concept_ref":    q.get("concept_ref", ""),
                    "source_topic":   q.get("source_topic", ""),
                })

        correct    = sum(
            1 for q in quiz["questions"]
            if answers.get(q["question_id"], "").strip().upper() == q["correct_answer"]
        )
        total      = quiz["total_questions"]
        percentage = round(correct / total * 100, 1) if total else 0.0
        score      = {"correct": correct, "total": total, "percentage": percentage}

        update = {
            "status":            "completed",
            "score":             score,
            "answers_submitted": answers,
            "completed_at":      datetime.utcnow().isoformat(),
        }
        quizzes.update_one({"quiz_id": quiz_id}, {"$set": update})
        quiz.update(update)
        quiz["wrong_details"] = wrong_details

        KnowledgeStateService.update_from_quiz(user_id, quiz)

        logger.info(
            "[QuizAgent] Quiz '%s' submitted — %d/%d (%.1f%%) — %d wrong",
            quiz_id, correct, total, percentage, len(wrong_details),
        )
        return quiz

    # ── private helpers ───────────────────────────────────────────────────────

    def _call_groq(self, system: str, user: str) -> list:
        resp = self.client.chat.completions.create(
            model       = self.MODEL,
            messages    = [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature = self.TEMPERATURE,
            max_tokens  = self.MAX_TOKENS,
        )
        raw = resp.choices[0].message.content.strip()

        if raw.startswith("```"):
            parts = raw.split("```")
            raw   = parts[1] if len(parts) > 1 else raw
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"[QuizAgent] Invalid JSON from LLM: {e}\nRaw: {raw[:400]}"
            ) from e

        if not isinstance(data, list):
            raise ValueError("[QuizAgent] Expected a JSON array from LLM.")
        return data

    @staticmethod
    def _validate(raw: list) -> list:
        valid = []
        for i, q in enumerate(raw):
            question    = q.get("question",       "").strip()
            options     = q.get("options",         [])
            correct     = q.get("correct_answer",  "").strip().upper()
            explanation = q.get("explanation",     "").strip()
            domain      = q.get("domain",          "machine_learning")
            concept_ref = q.get("concept_ref",     "")
            source_t    = q.get("source_topic",    "")
            is_retry    = bool(q.get("is_retry",   False))

            if not question or not correct:
                continue
            if len(options) != 4:
                continue
            if correct not in ("A", "B", "C", "D"):
                continue

            valid.append({
                "question_id":    f"q{i + 1}",
                "type":           "mcq",
                "question":       question,
                "options":        options,
                "correct_answer": correct,
                "explanation":    explanation,
                "domain":         domain,
                "concept_ref":    concept_ref,
                "source_topic":   source_t,
                "is_retry":       is_retry,
            })
        return valid

    @staticmethod
    def _resolve_difficulty(profile: dict) -> str:
        raw = (
            profile.get("skill_level")
            or profile.get("domain_analysis", {}).get("detected_level")
            or "intermediate"
        )
        mapping = {
            "Beginner":     "beginner",
            "Intermediate": "intermediate",
            "Advanced":     "advanced",
        }
        return mapping.get(raw, raw.lower())

    @staticmethod
    def _save(quiz: dict) -> None:
        try:
            quizzes = Database.get_collection("quizzes")
            quizzes.insert_one({**quiz})
            logger.info(
                "[QuizAgent] Persisted quiz '%s' (%d questions).",
                quiz["quiz_id"], len(quiz["questions"]),
            )
        except Exception as exc:
            logger.error("[QuizAgent] Failed to save quiz '%s': %s", quiz["quiz_id"], exc)
            raise
