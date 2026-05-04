import uuid
from datetime import datetime


def build_quiz_schema(
    user_id:            str,
    topic:              str,
    trigger:            str,
    difficulty:         str,
    questions:          list,
    time_limit_minutes: int,
    kg_available:       bool,
    source_topics:      list,
) -> dict:
    return {
        "quiz_id":            str(uuid.uuid4()),
        "user_id":            user_id,
        "topic":              topic,
        "source_topics":      source_topics,
        "trigger":            trigger,
        "difficulty":         difficulty,
        "kg_grounded":        kg_available,
        "questions":          questions,
        "total_questions":    len(questions),
        "time_limit_minutes": time_limit_minutes,
        "status":             "pending",
        "score":              None,
        "answers_submitted":  None,
        "created_at":         datetime.utcnow().isoformat(),
        "completed_at":       None,
    }















"""
    Fields
    ------
    quiz_id             str   — uuid4
    user_id             str
    topic               str   — primary topic
    source_topics       list  — all topics from chat that influenced questions
    trigger             str   — "manual"|"topic_completed"|"weak_performance"|
                                "random_prompt"|"direct_request"|"repetitive_asking"
    difficulty          str   — "beginner"|"intermediate"|"advanced"
    kg_grounded         bool  — True = live Neo4j was reached
    questions           list  — see QuizGenerationAgent._validate for item schema
    total_questions     int
    time_limit_minutes  int
    status              str   — "pending"|"completed"
    score               null | {correct, total, percentage}
    answers_submitted   null | {"q1":"A","q2":"C",…}
    created_at          str   — ISO
    completed_at        null  | str
    """