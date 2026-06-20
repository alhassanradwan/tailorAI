"""
Builds the personalised system prompt sent to Groq.
Imports AGENTS directly from agent definitions to avoid circular imports.
"""

import logging
from services.adaptive_mode_service import AdaptiveModeService

# ── Import agents directly from their modules (NOT from __init__)
# ── This breaks the circular import:
# ──   __init__ → prompt_builder → __init__ (CIRCULAR)
# ── Instead:
# ──   __init__ → prompt_builder → data_science_agent (SAFE)
from services.agents.data_science_agent import DataScienceAgent
from services.agents.machine_learning_agent import MachineLearningAgent
from services.agents.deep_learning_agent import DeepLearningAgent

logger = logging.getLogger(__name__)

# Build AGENTS dict locally — same structure as __init__ exports
_AGENTS = {
    'data_science':     DataScienceAgent.to_dict(),
    'machine_learning': MachineLearningAgent.to_dict(),
    'deep_learning':    DeepLearningAgent.to_dict(),
}


# ────────────────────────────────────────────────────────────
# Normalizers
# ────────────────────────────────────────────────────────────
def normalize_forced_mode(value: str) -> str:
    raw = (value or '').strip().lower()
    if raw in ('', 'auto', 'automatic'):
        return ''
    if raw == 'guided':
        return 'socratic'
    if raw in ('direct', 'supportive', 'socratic', 'supportive_socratic'):
        return raw
    return ''


def normalize_forced_tone(value: str) -> str:
    raw = (value or '').strip().lower()
    if raw in ('', 'auto', 'automatic'):
        return ''
    if raw in ('friendly', 'professional', 'socratic', 'concise'):
        return raw
    return ''


# ────────────────────────────────────────────────────────────
# Main builder
# ────────────────────────────────────────────────────────────
def build_system_prompt(
    agent_key: str,
    profile: dict,
    knowledge_state: dict,
    analysis: dict = None,
    forced_mode: str = None,
    forced_reason: str = None,
    rag_context: str = None,
) -> str:
    agent_cfg     = _AGENTS.get(agent_key, _AGENTS['machine_learning'])
    ks            = knowledge_state or {}
    ba            = ks.get('behavioral', {})
    prefs         = ks.get('conversation_preferences', {})
    adaptations   = ks.get('current_adaptations', {})
    analysis_recs = (analysis or {}).get('recommendations', {})
    topics_map    = ks.get('topics', {})
    misconceptions = ks.get('misconceptions', {})
    strong        = ks.get('strong_topics', [])
    weak          = ks.get('weak_topics', [])

    # ── effective level ──────────────────────────────────────
    cd      = ba.get('complexity_distribution', {})
    total_q = sum(cd.values()) if cd else 0
    if total_q >= 5:
        adv_r = cd.get('advanced', 0) / total_q
        beg_r = cd.get('beginner', 0) / total_q
        effective_level = (
            'Advanced' if adv_r > 0.5
            else 'Beginner' if beg_r > 0.5
            else 'Intermediate'
        )
    else:
        effective_level = profile.get('skill_level', profile.get('python', 'Intermediate'))

    # filter historical topics to ONLY those relevant to the current message topics
    # to avoid contaminating the current chat with unrelated historical topics
    curr_topics = analysis.get('topics', []) if isinstance(analysis, dict) else []

    # filter strong/weak topics based on curr_topics
    if curr_topics:
        strong = [t for t in strong if any(c.lower() in t.lower() or t.lower() in c.lower() for c in curr_topics)]
        weak   = [t for t in weak if any(c.lower() in t.lower() or t.lower() in c.lower() for c in curr_topics)]
    else:
        strong = []
        weak = []

    # ── mastery lines ────────────────────────────────────────
    mastery_lines = []
    if curr_topics:
        for topic, td in topics_map.items():
            if isinstance(td, dict) and td.get('count', 0) >= 2:
                # Only include if it's broadly related to the current chat
                if any(curr_t.lower() in topic.lower() or topic.lower() in curr_t.lower() for curr_t in curr_topics):
                    m = td.get('mastery_level', 0)
                    mastery_lines.append(
                        f"  - {topic}: {m:.0%} mastery ({td['count']} interactions)"
                    )

    # ── misconception lines ──────────────────────────────────
    misconception_lines = []
    if curr_topics:
        for topic, md in misconceptions.items():
            if isinstance(md, dict) and not md.get('corrected'):
                # Same for misconceptions
                if any(curr_t.lower() in topic.lower() or topic.lower() in curr_t.lower() for curr_t in curr_topics):
                    misconception_lines.append(
                        f"  - {topic}: {md.get('detail', 'unclear understanding')}"
                    )

    # ── style preferences ────────────────────────────────────
    style_notes = []
    if prefs.get('prefers_examples'):
        style_notes.append('real-world examples')
    if prefs.get('prefers_code'):
        style_notes.append('code snippets')
    if prefs.get('prefers_analogies'):
        style_notes.append('analogies')
    style_str = f"Include {', '.join(style_notes)} when possible." if style_notes else ''

    # ── tone & length overrides ──────────────────────────────
    tone_inst   = ''
    length_inst = ''
    pt          = prefs.get('preferred_tone', '')
    pl          = prefs.get('preferred_length', '')
    forced_tone = normalize_forced_tone(profile.get('force_tone'))

    if forced_tone == 'friendly':
        tone_inst = 'CRITICAL: Use a FRIENDLY, casual tone — warm, contractions, like a helpful friend.'
    elif forced_tone == 'professional':
        tone_inst = 'CRITICAL: Use a FORMAL, professional, academic tone.'
    elif forced_tone == 'socratic':
        tone_inst = 'CRITICAL: Use a Socratic teaching voice: ask guiding questions before direct conclusions.'
    elif forced_tone == 'concise':
        length_inst = 'CRITICAL: Keep responses concise and direct. Prefer short paragraphs and compact bullets.'

    if not tone_inst and pt == 'friendly':
        tone_inst = 'CRITICAL: Use a FRIENDLY, casual tone — warm, contractions, like a helpful friend.'
    elif not tone_inst and pt == 'formal':
        tone_inst = 'CRITICAL: Use a FORMAL, professional, academic tone.'
    if not length_inst and pl == 'short':
        length_inst = 'CRITICAL: Keep responses to 2-4 sentences MAX. Be brief and direct.'
    elif not length_inst and pl == 'detailed':
        length_inst = 'CRITICAL: Provide DETAILED responses. Go deep, cover edge cases.'

    # --- Live message overrides for length ---
    # Give priority if the user explicitly asks for detail or brevity in the recent chat history
    # We will just parse the last message if passed via analysis, else we just use pl.
    current_message = (analysis.get('message') or '') if isinstance(analysis, dict) else ''
    msg_lower = current_message.lower()
    if any(k in msg_lower for k in ['in detail', 'detailed', 'in depth', 'elaborate', 'comprehensively']):
        length_inst = 'CRITICAL: The user explicitly requested a DETAILED answer. You MUST provide a comprehensive, deeply thorough, and rich explanation. Do not shorten it.'
    elif any(k in msg_lower for k in ['short', 'brief', 'concise', 'summarize', 'in a few words', 'quick']):
        length_inst = 'CRITICAL: The user explicitly requested a SHORT answer. Keep responses to 2-4 sentences MAX. Be brief and direct.'

    # ── adaptation directives ────────────────────────────────
    active_mode = (
        forced_mode
        or analysis_recs.get('tutoring_mode')
        or adaptations.get('tutoring_mode', 'direct')
    )
    mode_reason = (
        forced_reason
        or analysis_recs.get('mode_reason')
        or adaptations.get('mode_reason', 'stable understanding detected')
    )

    adapt = [AdaptiveModeService.mode_prompt_instruction(active_mode)]
    adapt.append(f"MODE REASON: {mode_reason}.")

    if AdaptiveModeService.is_socratic(active_mode):
        adapt.append("SOCRATIC SIGNAL: Ask probing questions before giving final direct answer.")

    emo = adaptations.get('emotional_state', 'neutral')
    if emo == 'frustrated':
        adapt.append("SUPPORT MODE: Be extra warm, break into tiny steps.")
    elif emo == 'curious':
        adapt.append("EXPLORATION MODE: Go deeper, share insights.")

    chk = adaptations.get('comprehension_check')
    if chk and AdaptiveModeService.is_socratic(active_mode):
        adapt.append(
            f"After answering, ask: 'Can you explain {chk} in your own words?' "
            f"(NOTE: If the user explicitly asks NOT to be asked questions, skip this check.)"
        )

    learning_tone      = profile.get('learning_tone', profile.get('tone', 'Friendly')).lower()
    conversation_count = profile.get('conversation_count', 0)
    name               = profile.get('user_name') or profile.get('name', 'Student')

    # ── preference header ────────────────────────────────────
    pref_header = ''
    if tone_inst or length_inst:
        pref_header = (
            f"⚡ STUDENT'S EXPLICIT PREFERENCES (MUST FOLLOW):\n"
            f"{tone_inst}\n"
            f"{length_inst}\n"
            f"---\n"
        )

    # ── assemble prompt ──────────────────────────────────────
    prompt = f"""{pref_header}{agent_cfg['system']}

You are AdaptiveAI, an intelligent tutoring assistant that truly knows this student.

=== LEARNER INTELLIGENCE PROFILE ===
Name: {name}
Effective Skill Level: {effective_level} (from {total_q} analysed interactions)
Learning Tone: {learning_tone}
Tutoring Mode: {active_mode}
Domain: {agent_cfg['label']}
Conversations: {conversation_count}
{'MASTERED: ' + ', '.join(strong) if strong else ''}
{'STILL LEARNING: ' + ', '.join(weak) if weak else ''}

{'TOPIC MASTERY MAP:' + chr(10) + chr(10).join(mastery_lines) if mastery_lines else ''}
{'ACTIVE MISCONCEPTIONS:' + chr(10) + chr(10).join(misconception_lines) if misconception_lines else ''}

=== ADAPTATION RULES ===
1. Level {effective_level}: {'Simple analogies, step-by-step, avoid jargon' if effective_level == 'Beginner' else 'Balance theory + practice' if effective_level == 'Intermediate' else 'Deep technical depth, maths, research-level'}
2. {style_str}
{chr(10).join(adapt)}

{tone_inst}
{length_inst}

{'Keep responses to 2-4 sentences MAX.' if pl == 'short' else 'Keep responses concise but thorough (150-300 words unless more detail requested).'}"""

    # ── RAG context injection ────────────────────────────────
    if rag_context:
        prompt += f"""

=== RETRIEVED DOMAIN KNOWLEDGE (from knowledge graph) ===
Use the following retrieved concepts to ground your response.
Teach these concepts in YOUR tutoring voice — do not copy verbatim.
If the retrieved info contradicts your knowledge, prefer your own.
Only use what is directly relevant to the student's question.

{rag_context}
"""

    prompt += (
        "\n\nCRITICAL UI INSTRUCTION: If the user requests a quiz, assessment, or practice "
        "questions, NEVER generate the questions directly in your response text. A separate "
        "specialized UI modal will automatically handle generating and displaying the interactive "
        "quiz. Your ONLY job when a quiz is requested is to enthusiastically acknowledge it "
        "(e.g. 'I will prepare your quiz, opening it now!') and stop. Do not provide A, B, C, D "
        "options or write out any questions in the chat."
    )

    return prompt