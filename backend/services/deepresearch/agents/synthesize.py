from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_text_call
import json

def run_synthesize(state: ResearchState) -> dict:
    facts = state["facts"]
    topic = state["topic"]
    
    print("[Deep Research] Synthesizing final report...")
    
    sys_prompt = """
    You are an expert academic researcher. Synthesize the provided facts into a comprehensive, structured Markdown report.
    Use clear headings (##), logical flow, and paragraphs.
    Do NOT include a 'References' section yet, we will add that later.
    Be thorough, readable, and highly informative.
    """
    
    facts_str = json.dumps(facts, indent=2)
    report = llm_text_call(sys_prompt, f"Topic: {topic}\n\nFacts:\n{facts_str}")
    
    return {"report": report}