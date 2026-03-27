"""Typed schemas for LangChain analysis outputs with safe defaults."""

from pydantic import BaseModel, Field


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
