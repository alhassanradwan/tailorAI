"""
services/quiz/prompts.py
LLM system prompt and user-prompt builder for quiz generation.
"""

from typing import Optional
from services.quiz.wrong_answer_store import WrongAnswerStore

SYSTEM_PROMPT = """You are TailorAI's Quiz Generation Agent. Act as an intelligent quiz generation engine with strict rule-based behavior.

========================
QUIZ SOURCE LOGIC (STRICT PRIORITY ORDER)
========================

1. If the user explicitly specifies a topic:
    - Generate ALL questions strictly from that topic only.
    - Do NOT include questions from any other topic under any circumstances.

2. If NO topic is specified, determine the quiz source using this priority:
    a) Current Chat Context: Extract topics discussed in the CURRENT conversation only.
    b) Weak Topics from the learner profile: Topics the student is struggling with.
    c) Recent Topics: Topics from the student's learning history.

========================
QUESTION COUNT RULE
========================

- If the user explicitly specifies the number of questions: STRICTLY generate EXACTLY that number — no more, no less.
- If the user does NOT specify a number: Use the count given in the prompt (pre-calculated).

========================
QUESTION REUSE POLICY (VERY IMPORTANT)
========================

- NEVER repeat a question that appeared in previous quizzes AND was answered correctly.
- EXCEPTION: You MAY rephrase questions the student answered INCORRECTLY in a previous quiz.
  When rephrasing, keep the same core concept but change the wording/scenario.
  If the student now answers it correctly, it signals mastery — do not repeat again.

========================
QUIZ FORMAT
========================

Output ONLY a valid JSON array of MCQ question objects. No text outside the array.

Each object MUST follow this exact schema:
{
  "type": "mcq",
  "question": "Clear, specific question string",
  "options": ["A) option text", "B) option text", "C) option text", "D) option text"],
  "correct_answer": "A",
  "explanation": "Why this answer is correct and others are wrong",
  "domain": "data_science" | "machine_learning" | "deep_learning",
  "concept_ref": "exact KG concept name tested, or empty string",
  "source_topic": "which topic inspired this question",
  "is_retry": true | false
}

Rules:
- correct_answer MUST be exactly "A", "B", "C", or "D"
- explanation MUST be educational and explain why the correct answer is right AND why the wrong options are wrong.
- correct answer must vary in position across questions (do not always put it as "A")
- is_retry = true only for questions rephrased from previously incorrect ones
- All 4 options must be plausible (avoid obviously wrong distractors)
- Ground every question in the KG concepts and facts provided
- Questions must test UNDERSTANDING, not just definitions
- Output ONLY the JSON array
- NEVER mix unrelated topics if a topic is specified
- ABSOLUTE BAN: NEVER generate a question about difficulty levels, skill levels,
  learner profiles, or learning/teaching metadata of any kind. Every single question
  must be about the actual subject matter — concepts, math, code, techniques,
  applications, definitions. Ask yourself: "Does this question test knowledge of
  Neural Networks (or whatever the topic is)?" If the answer is no, discard it.
  BANNED example: "What is the primary characteristic of an intermediate-level topic?"
  GOOD example: "What is the role of an activation function in a neural network?"
"""


def build_user_prompt(
    primary_topic:        str,
    source_topics:        list,
    question_count:       int,
    user_requested_count: Optional[int],
    difficulty:           str,
    profile:              dict,
    weak_topics:          list,
    trigger:              str,
    kg_contexts:          dict,
    rag_contexts:         dict,
    past_correct:         list,
    wrong_answer_records: list,
    is_explicit_topic:    bool = False,
) -> str:
    name             = profile.get("name", "Student")
    skill_level      = profile.get("skill_level", difficulty)
    strongest_domain = profile.get("strongest_domain", "Machine Learning")
    python_skill     = profile.get("python", "intermediate")
    math_skill       = profile.get("math", "intermediate")
    weak_str         = ", ".join(weak_topics) if weak_topics else "none identified"

    trigger_map = {
        "manual":            f"Student manually requested a quiz on '{primary_topic}'.",
        "direct_request":    f"Student directly requested a quiz on '{primary_topic}'.",
        "topic_completed":   f"Student just finished '{primary_topic}'. Consolidate learning.",
        "weak_performance":  f"Student struggled with '{primary_topic}'. Focus on fundamentals.",
        "repetitive_asking": f"Student keeps revisiting '{primary_topic}'. Reinforce understanding.",
        "random_prompt":     "Surprise quiz to reinforce past learning across topics.",
    }
    trigger_note = trigger_map.get(trigger, f"Quiz triggered by: {trigger}.")

    # ── KG (legacy KnowledgeGraphService) context blocks ────────────────────
    kg_blocks = []
    for topic_name, ctx in kg_contexts.items():
        concepts_str = ""
        if ctx.get("concepts"):
            lines = []
            for c in ctx["concepts"]:
                facts_str = "\n        ".join(c.get("facts", []))
                lines.append(
                    f"    Concept: {c['name']}\n"
                    f"    Definition: {c.get('definition', '')}\n"
                    f"    Facts:\n        {facts_str}"
                )
            concepts_str = "\n\n".join(lines)

        rels_str = "\n  ".join(
            f"{r['from']} --[{r['relation']}]--> {r['to']}"
            for r in ctx.get("relationships", [])
        )
        prereqs = ", ".join(ctx.get("prerequisites", [])) or "none"

        kg_blocks.append(
            f"\n── TOPIC: {topic_name.upper()} ──────────────────────────\n"
            f"Domain: {ctx['domain']}\n"
            f"Summary: {ctx.get('summary', '')}\n"
            f"Prerequisites: {prereqs}\n"
            f"Concepts to test:\n"
            f"{concepts_str if concepts_str else '  (no structured concepts — use topic knowledge)'}\n"
            f"Graph relationships:\n"
            f"  {rels_str if rels_str else '(none)'}\n"
        )

    # ── RAG (Neo4j / SharedGraphRAG) context blocks ──────────────────────────
    rag_blocks = []
    for topic_name, rag_ctx in rag_contexts.items():
        fc = rag_ctx.get("formatted_context", "")
        if fc:
            rag_blocks.append(
                f"\n── RAG RETRIEVED CONTEXT FOR: {topic_name.upper()} ──\n{fc}\n"
            )
        cross = rag_ctx.get("cross_domain_connections", [])
        if cross:
            lines = [f"  {cx['source']} → {cx['target']} ({cx['domain']})" for cx in cross]
            rag_blocks.append("Cross-domain links:\n" + "\n".join(lines))

    kg_section  = "\n".join(kg_blocks)
    rag_section = "\n".join(rag_blocks)

    # ── Question count instruction ───────────────────────────────────────────
    if user_requested_count is not None:
        count_instruction = (
            f"⚠️  CRITICAL: The student explicitly requested EXACTLY "
            f"{user_requested_count} questions. "
            f"You MUST generate EXACTLY {user_requested_count} questions — "
            f"not one more, not one less."
        )
        q_count = user_requested_count
    else:
        count_instruction = f"Generate exactly {question_count} questions."
        q_count = question_count

    # ── Distribution / topic restriction ────────────────────────────────────
    if len(source_topics) > 1:
        per_topic = q_count // len(source_topics)
        remainder = q_count % len(source_topics)
        dist_lines = [
            f"  {t}: {per_topic + (1 if i < remainder else 0)} questions"
            for i, t in enumerate(source_topics)
        ]
        distribution = "Distribute questions:\n" + "\n".join(dist_lines)
        weak_rule = (
            f"  - INCLUDE at least 2 questions on weak areas: {weak_str}"
            if weak_topics else ""
        )
    else:
        distribution = (
            f"All {q_count} questions MUST BE EXACTLY AND ONLY ON '{primary_topic}'."
        )
        weak_rule = (
            f"  - STRICT RESTRICTION: EVERY QUESTION MUST BE EXCLUSIVELY "
            f"ABOUT '{primary_topic}'."
        )

    # ── Past correct (do not repeat) ────────────────────────────────────────
    past_correct_str = ""
    if past_correct:
        seen = list(dict.fromkeys(past_correct))[:40]
        past_correct_str = (
            "\nDO NOT REPEAT THESE QUESTIONS (already answered correctly):\n"
            + "\n".join(f"  - {q}" for q in seen)
        )

    # ── Wrong-answer retry block ─────────────────────────────────────────────
    wrong_answer_str = WrongAnswerStore.format_for_prompt(wrong_answer_records)

    # ── Learner profile block ────────────────────────────────────────────────
    # Omitted entirely when a specific topic was named so the LLM cannot
    # accidentally write questions about skill levels / difficulty.
    if is_explicit_topic:
        profile_block = (
            f"# QUIZ DIFFICULTY LEVEL: {difficulty}\n"
            f"# (Use this only to calibrate question depth — "
            f"do NOT generate any question about difficulty levels, "
            f"skill levels, learner profiles, or learning metadata.)"
        )
    else:
        profile_block = (
            f"LEARNER PROFILE (metadata only — "
            f"NEVER generate questions about any of these facts):\n"
            f"- Name: {name}\n"
            f"- Difficulty: {difficulty} | Skill level: {skill_level}\n"
            f"- Strongest domain: {strongest_domain}\n"
            f"- Python proficiency: {python_skill}\n"
            f"- Math proficiency: {math_skill}\n"
            f"- Known weak areas: {weak_str}"
        )

    return f"""Target Subject for Quiz Generation: {primary_topic}

THE ACTUAL QUIZ TOPICS:
  {', '.join(source_topics) if source_topics else primary_topic}

{count_instruction}

{distribution}
{past_correct_str}

{wrong_answer_str}

{profile_block}

TRIGGER REASON: {trigger_note}

══════════════════ KNOWLEDGE GRAPH CONTEXT (Legacy KG) ══════════════════
{kg_section if kg_section else "(none)"}
═════════════════════════════════════════════════════════════════════════

══════════════════ KNOWLEDGE GRAPH CONTEXT (Neo4j RAG) ══════════════════
{rag_section if rag_section else "(none — use your training knowledge for these topics)"}
═════════════════════════════════════════════════════════════════════════

REQUIREMENTS:
  - {count_instruction}
  - Every question must be strictly about the subject matter itself — concepts, math, code, techniques — NEVER about learner profiles, difficulty levels, or metadata
  - Every question must map to a KG/RAG concept (if available) or squarely match the requested topic
  - Set source_topic to which chat topic inspired each question
  - Set is_retry=true for any question rephrased from a previously wrong answer
{weak_rule}
  - All 4 options must be plausible (no obvious trick answers)
  - Explanations must be educational (explain why wrong options are wrong too)
  - Output ONLY the JSON array
"""
