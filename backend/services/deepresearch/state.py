from typing import TypedDict, List, Dict, Any, Optional

class ResearchState(TypedDict):
    user_id: str
    topic: str
    plan: List[str]
    documents: List[Dict[str, Any]]
    facts: List[Dict[str, Any]]
    report: str
    sources: List[str]
    critique: Optional[Dict[str, Any]]
    revision_count: int