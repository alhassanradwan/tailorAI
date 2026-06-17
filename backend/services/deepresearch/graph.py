from langgraph.graph import StateGraph, END
from services.deepresearch.state import ResearchState

from services.deepresearch.agents.planner import run_planner
from services.deepresearch.agents.search import run_search
from services.deepresearch.agents.extract import run_extract
from services.deepresearch.agents.synthesize import run_synthesize
from services.deepresearch.agents.cite import run_cite
from services.deepresearch.agents.critic import run_critic

def build_research_graph():
    workflow = StateGraph(ResearchState)
    
    workflow.add_node("planner", run_planner)
    workflow.add_node("search", run_search)
    workflow.add_node("extract", run_extract)
    workflow.add_node("synthesize", run_synthesize)
    workflow.add_node("cite", run_cite)
    workflow.add_node("critic", run_critic)

    # Define edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "search")
    workflow.add_edge("search", "extract")
    workflow.add_edge("extract", "synthesize")
    workflow.add_edge("synthesize", "cite")
    workflow.add_edge("cite", "critic")

    # Conditional feedback loop from critic
    def quality_check(state: ResearchState):
        critique = state.get("critique", {})
        passed = critique.get("pass", False)
        rev_count = state.get("revision_count", 0)
        
        if passed or rev_count >= 1:
            return "end"
        return "retry"

    workflow.add_conditional_edges(
        "critic",
        quality_check,
        {
            "end": END,
            "retry": "synthesize"
        }
    )

    return workflow.compile()