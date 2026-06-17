from services.deepresearch.state import ResearchState

def run_cite(state: ResearchState) -> dict:
    report = state["report"]
    facts = state["facts"]
    
    print("[Deep Research] Attaching citations...")
    
    # Simple citation appending for consistency and safety (can be augmented with LLM later if needed)
    sources_set = set()
    for f in facts:
        if "source_url" in f:
            sources_set.add(f["source_url"])
            
    sources = list(sources_set)
    
    citation_section = "\n\n## References\n"
    for i, src in enumerate(sources, 1):
        citation_section += f"[{i}] {src}\n"
        
    final_report = report + citation_section
    
    return {"report": final_report, "sources": sources}