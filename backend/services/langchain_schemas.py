"""Typed schemas for LangChain analysis outputs with safe defaults."""

from pydantic import BaseModel, Field
from typing import Literal


class LangChainAnalysisCues(BaseModel):
    topics: list[str] = Field(default_factory=list)
    confusion_level: float = 0.0
    uncertainty_markers: int = 0
    misconception_detected: bool = False
    misconception_detail: str | None = None
    emotional_state: str = 'neutral'
    suggested_approach: str = 'explain_simply'
    mode_suggestion: str | None = None
    confidence: float = 0.5


def default_analysis_cues() -> LangChainAnalysisCues:
    return LangChainAnalysisCues()


ChatBlockType = Literal[
    'explanation',
    'steps',
    'code',
    'comparison_table',
    'quiz',
    'hint',
    'follow_up',
    'text',
]


class DynamicContentBlock(BaseModel):
    type: ChatBlockType
    title: str | None = None
    text: str | None = None
    language: str | None = None
    rows: list[dict[str, str]] = Field(default_factory=list)
    items: list[str] = Field(default_factory=list)


class DynamicResponseMetadata(BaseModel):
    intent: str = 'general_fallback'
    confidence: float = 0.0
    fallback_used: bool = False
    fallback_reason: str | None = None


class DynamicChatResponseEnvelope(BaseModel):
    response_schema_version: str = 'v1'
    message_type: str = 'dynamic_blocks'
    content_blocks: list[DynamicContentBlock] = Field(default_factory=list)
    metadata: DynamicResponseMetadata = Field(default_factory=DynamicResponseMetadata)


def build_text_only_dynamic_envelope(
    response_text: str,
    intent: str = 'general_fallback',
    confidence: float = 0.0,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
) -> DynamicChatResponseEnvelope:
    text = (response_text or '').strip()
    blocks = []
    if text:
        blocks.append(DynamicContentBlock(type='text', text=text))
    return DynamicChatResponseEnvelope(
        content_blocks=blocks,
        metadata=DynamicResponseMetadata(
            intent=intent,
            confidence=max(0.0, min(1.0, float(confidence or 0.0))),
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
        ),
    )
