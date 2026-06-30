from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call
from services.deepresearch.prompts.planner_prompt import PLANNER_SYSTEM_PROMPT


def run_planner(state: ResearchState) -> dict:
    topic = state["topic"]
    print(f"[Deep Research] Planning research for topic: {topic}")

    result = llm_json_call(PLANNER_SYSTEM_PROMPT, f"Topic: {topic}")
    plan = result.get("plan", [
        f"General overview of {topic}",
        f"Impact of {topic}",
        f"Future trends in {topic}",
    ])

    return {"plan": plan, "revision_count": state.get("revision_count", 0)}