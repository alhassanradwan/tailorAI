def build_wrong_answer_explanation_context(graded_quiz: dict) -> str:
    wrong   = graded_quiz.get("wrong_details", [])
    score   = graded_quiz.get("score", {})
    if not wrong:
        return ""

    pct     = score.get("percentage", 0)
    total   = score.get("total", 0)
    correct = score.get("correct", 0)

    lines = [
        "## POST-QUIZ CONTEXT (inject into next chat turn)",
        f"The student just completed a quiz: {correct}/{total} correct ({pct}%).",
        f"They got {len(wrong)} question(s) wrong. "
        "Be ready to explain any of these if they ask — do NOT volunteer all "
        "explanations unprompted, wait for the student to ask about a specific one "
        "or ask you to explain their mistakes.\n",
    ]
    for i, w in enumerate(wrong, 1):
        lines.append(
            f"[Wrong Q{i}]\n"
            f"  Question    : {w['question']}\n"
            f"  Options     : {' | '.join(w['options'])}\n"
            f"  Correct     : {w['correct_answer']}\n"
            f"  Student said: {w['user_answer']}\n"
            f"  Explanation : {w['explanation']}\n"
            f"  Concept     : {w.get('concept_ref') or w.get('source_topic', '')}"
        )
    return "\n".join(lines)


def get_quiz_generation_summary(quiz: dict) -> str:
    return (
        f"## GENERATED QUIZ CONTEXT\n"
        f"quiz_id      : {quiz['quiz_id']}\n"
        f"topic        : {quiz['topic']}\n"
        f"source_topics: {', '.join(quiz.get('source_topics', []))}\n"
        f"questions    : {quiz['total_questions']}\n"
        f"difficulty   : {quiz['difficulty']}\n"
        f"kg_grounded  : {quiz['kg_grounded']}\n"
        f"time_limit   : {quiz['time_limit_minutes']} min\n"
        f"The quiz has been sent to the student. "
        f"Do not reveal correct answers until they submit."
    )
