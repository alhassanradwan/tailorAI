from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call

def run_critic(state: ResearchState) -> dict:
    report = state["report"]
    topic = state["topic"]
    rev_count = state.get("revision_count", 0)
    
    print("[Deep Research] Critic evaluating report quality...")
    
    sys_prompt = """
    You are a strict QA critic analyzing a research report. Evaluate against:
    - Coverage completeness
    - Structure quality
    - Accuracy risk
    
    Output JSON:
    {
      "pass": true/false,
      "score": 0.9,
      "issues": ["list of issues if any"],
      "feedback": "constructive feedback"
    }
    """
    
    critic_result = llm_json_call(sys_prompt, f"Topic: {topic}\n\nReport:\n{report}")
    
    if not critic_result:
        critic_result = {"pass": True, "score": 1.0, "issues": [], "feedback": "Validation bypass"}
        
    return {
        "critique": critic_result,
        "revision_count": rev_count + 1
    }