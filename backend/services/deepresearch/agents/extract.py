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
        You are an extraction AI. Read the JSON array of documents.
        Extract up to 5 key concrete facts. Deduplicate information.
        Output JSON: {"facts": [{"fact": "extracted fact", "source_url": "associated url"}]}
        """
        res = llm_json_call(sys_prompt, f"Documents: {docs_str}")
        facts.extend(res.get("facts", []))
        
    return {"facts": facts}