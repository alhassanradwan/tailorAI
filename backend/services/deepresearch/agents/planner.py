from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call

def run_planner(state: ResearchState) -> dict:
    topic = state["topic"]
    print(f"[Deep Research] Planning research for topic: {topic}")
    
    system_prompt = """
    You are an expert research planner. Given a topic, break it down into 3-5 high-level research subtopics.
    Output JSON in this format: {"plan": ["subtopic 1", "subtopic 2", ...]}
    """
    
    result = llm_json_call(system_prompt, f"Topic: {topic}")
    plan = result.get("plan", [f"General overview of {topic}", f"Impact of {topic}", f"Future trends in {topic}"])
    
    return {"plan": plan, "revision_count": state.get("revision_count", 0)}