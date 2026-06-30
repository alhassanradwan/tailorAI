from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_text_call
from services.deepresearch.prompts.synthesize_prompt import SYNTHESIZE_SYSTEM_PROMPT
import json


def run_synthesize(state: ResearchState) -> dict:
    facts = state["facts"]
    topic = state["topic"]

    print("[Deep Research] Synthesizing final report...")

    facts_str = json.dumps(facts, indent=2)
    report = llm_text_call(SYNTHESIZE_SYSTEM_PROMPT, f"Topic: {topic}\n\nFacts:\n{facts_str}")

    return {"report": report}