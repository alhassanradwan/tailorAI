"""
Response formatting utilities.
Structures raw LLM text into dynamic content blocks for the frontend.
"""

import re
from services.langchain.langchain_schemas import DynamicContentBlock, build_text_only_dynamic_envelope


# ────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────
def _looks_structured_response(text: str) -> bool:
    content = (text or '').strip()
    if not content:
        return False
    has_heading    = bool(re.search(r'(?im)^\s{0,3}(?:#{1,6}\s+|[A-Za-z][A-Za-z ]{2,}:\s*$)', content))
    bullet_lines   = re.findall(r'(?im)^\s*[-*]\s+', content)
    numbered_lines = re.findall(r'(?im)^\s*\d+\.\s+', content)
    return has_heading or len(bullet_lines) >= 2 or len(numbered_lines) >= 2


def _split_sentences_local(text: str) -> list[str]:
    chunks = re.split(r'(?<=[.!?])\s+', (text or '').strip())
    return [c.strip() for c in chunks if c.strip()]


# ────────────────────────────────────────────────────────────
# Formatters
# ────────────────────────────────────────────────────────────
def format_general_response(text: str) -> tuple[str, bool, str | None]:
    content = (text or '').strip()
    if not content:
        return content, False, None
    if _looks_structured_response(content):
        return content, False, None

    sentences = _split_sentences_local(content)
    if len(sentences) <= 2:
        return f"Explanation\n{content}", True, 'general_structure'

    intro       = sentences[0]
    bullets     = sentences[1:4]
    bullet_text = '\n'.join([f"- {s}" for s in bullets])
    formatted   = (
        "Explanation\n"
        f"{intro}\n\n"
        "Key Points\n"
        f"{bullet_text}"
    )
    return formatted, True, 'general_structure'


def format_structured_fallback(text: str, structured_intent: str | None) -> tuple[str, bool, str | None]:
    content = (text or '').strip()
    if not content:
        return content, False, None

    lower = content.lower()
    if structured_intent == 'comparison' and 'comparison' not in lower:
        return (
            f"Explanation\n{content}\n\nComparison\n"
            "- Option A vs Option B: compare by accuracy, speed, complexity, and data requirements.",
            True, 'comparison_structure',
        )
    if structured_intent == 'examples' and 'examples' not in lower:
        return (
            f"Explanation\n{content}\n\nExamples\n"
            "- Example 1: Apply this on a simple dataset.\n"
            "- Example 2: Apply this on noisy real-world data.",
            True, 'examples_structure',
        )
    if structured_intent == 'use_cases' and ('when to use' not in lower or 'when not to use' not in lower):
        return (
            f"Explanation\n{content}\n\nWhen to Use\n"
            "- Use when assumptions and data conditions fit.\n\n"
            "When Not to Use\n"
            "- Avoid when assumptions break or simpler baselines perform similarly.",
            True, 'use_cases_structure',
        )
    if structured_intent == 'multi_idea' and ('options' not in lower and 'approaches' not in lower):
        return (
            f"Explanation\n{content}\n\nOptions\n"
            "- Option 1: Fast to implement\n"
            "- Option 2: Balanced tradeoff\n"
            "- Option 3: Highest potential performance\n\n"
            "Recommendation\n"
            "Choose based on your latency, accuracy, and maintenance constraints.",
            True, 'multi_idea_structure',
        )
    return content, False, None


# ────────────────────────────────────────────────────────────
# Dynamic block builder
# ────────────────────────────────────────────────────────────
def _dynamic_block_type_from_title(title: str | None, content: str) -> str:
    title_norm   = (title or '').strip().lower()
    content_norm = (content or '').lower()
    if title_norm in {'comparison', 'comparison table'}:
        return 'comparison_table'
    if title_norm in {'steps', 'key points', 'options'}:
        return 'steps'
    if title_norm in {'quiz', 'practice', 'questions'}:
        return 'quiz'
    if title_norm in {'hint', 'hints'}:
        return 'hint'
    if '```' in content_norm:
        return 'code'
    if '?' in content_norm and len(content_norm) < 280:
        return 'follow_up'
    if title_norm in {'explanation', 'summary', 'recommendation'}:
        return 'explanation'
    return 'text'


def build_dynamic_response_payload(
    response_text: str,
    intent: str,
    confidence: float,
    fallback_used: bool,
    fallback_reason: str | None,
) -> dict:
    heading_pattern = re.compile(r'^(?:#{1,6}\s*)?([A-Za-z][A-Za-z ]{2,40})\s*:?$')
    lines         = (response_text or '').splitlines()
    blocks        = []
    current_title = None
    current_lines = []

    for line in lines:
        stripped      = line.strip()
        heading_match = heading_pattern.match(stripped) if stripped else None
        if heading_match:
            if current_lines:
                content = '\n'.join(current_lines).strip()
                if content:
                    blocks.append(
                        DynamicContentBlock(
                            type=_dynamic_block_type_from_title(current_title, content),
                            title=current_title,
                            text=content,
                            language=None,
                            rows=[],
                            items=[],
                        )
                    )
                current_lines = []
            current_title = heading_match.group(1).strip()
            continue
        current_lines.append(line)

    if current_lines:
        content = '\n'.join(current_lines).strip()
        if content:
            blocks.append(
                DynamicContentBlock(
                    type=_dynamic_block_type_from_title(current_title, content),
                    title=current_title,
                    text=content,
                    language=None,
                    rows=[],
                    items=[],
                )
            )

    if not blocks:
        return build_text_only_dynamic_envelope(
            response_text=response_text,
            intent=intent,
            confidence=confidence,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ).model_dump()

    payload = build_text_only_dynamic_envelope(
        response_text='',
        intent=intent,
        confidence=confidence,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
    )
    payload.content_blocks = blocks
    return payload.model_dump()
