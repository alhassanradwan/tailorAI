from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call
import json

def run_extract(state: ResearchState) -> dict:
    documents = state["documents"]
    print(f"[Deep Research] Extracting facts from {len(documents)} documents...")
    
    facts = []
    # Batch processing to minimize tokens
    batch_size = 3
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        docs_str = json.dumps(batch)
        
        sys_prompt = """
You are a precise fact extraction AI. You will receive a JSON array of documents.

Your job:
- Extract up to 5 concrete, specific, and non-redundant facts per document
- Prioritize facts that are numerical, definitional, or highly specific
- Ignore vague or generic statements
- Each fact must be a single self-contained sentence
- Always associate the fact with its source_url from the document

Output strictly as JSON:
{"facts": [{"fact": "...", "source_url": "..."}]}
"""
        res = llm_json_call(sys_prompt, f"Documents: {docs_str}")
        facts.extend(res.get("facts", []))
        
    return {"facts": facts}