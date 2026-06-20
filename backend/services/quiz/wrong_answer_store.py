import logging
from datetime import datetime

from database import Database

logger = logging.getLogger(__name__)


class WrongAnswerStore:

    COLLECTION = "wrong_answers"

    @classmethod
    def _col(cls):
        return Database.get_collection(cls.COLLECTION)

    @classmethod
    def upsert(cls, user_id: str, quiz_id: str, question: dict, user_answer: str) -> None:
        doc = {
            "user_id":        user_id,
            "quiz_id":        quiz_id,
            "question_id":    question.get("question_id", ""),
            "question":       question.get("question", ""),
            "options":        question.get("options", []),
            "correct_answer": question.get("correct_answer", ""),
            "user_answer":    user_answer,
            "explanation":    question.get("explanation", ""),
            "domain":         question.get("domain", ""),
            "concept_ref":    question.get("concept_ref", ""),
            "source_topic":   question.get("source_topic", ""),
            "recorded_at":    datetime.utcnow().isoformat(),
        }
        cls._col().replace_one(
            {"user_id": user_id, "question": question.get("question", "")},
            doc,
            upsert=True,
        )
        logger.debug("[WrongAnswerStore] Upserted wrong answer for user=%s q=%s",
                    user_id, question.get("question_id"))

    @classmethod
    def delete_if_now_correct(cls, user_id: str, question_text: str) -> None:
        """Remove a previously wrong question that the student now answered correctly."""
        result = cls._col().delete_one({"user_id": user_id, "question": question_text})
        if result.deleted_count:
            logger.info("[WrongAnswerStore] Cleared mastered question for user=%s", user_id)

    @classmethod
    def get_for_user(cls, user_id: str, limit: int = 20) -> list[dict]:
        """Return up to `limit` pending wrong-answer records for this user."""
        return list(
            cls._col()
            .find({"user_id": user_id}, {"_id": 0})
            .sort("recorded_at", -1)
            .limit(limit)
        )

    @classmethod
    def format_for_prompt(cls, records: list[dict]) -> str:
        """Render wrong-answer records into the LLM prompt block."""
        if not records:
            return ""
        lines = [
            "YOU MAY REPHRASE AND REUSE THESE PREVIOUSLY MISSED QUESTIONS "
            "(student answered them incorrectly — test if they've learned):"
        ]
        for r in records:
            lines.append(
                f"  • Q: {r['question']}\n"
                f"    Correct: {r['correct_answer']}  |  Student chose: {r['user_answer']}\n"
                f"    Concept: {r.get('concept_ref') or r.get('source_topic', '')}"
            )
        return "\n".join(lines)



logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)