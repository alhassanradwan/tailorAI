from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call
from services.deepresearch.prompts.extract_prompt import EXTRACT_SYSTEM_PROMPT
import json


def run_extract(state: ResearchState) -> dict:
    documents = state["documents"]
    print(f"[Deep Research] Extracting facts from {len(documents)} documents...")

    facts = []
    batch_size = 3
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        docs_str = json.dumps(batch)

        res = llm_json_call(EXTRACT_SYSTEM_PROMPT, f"Documents: {docs_str}")
        facts.extend(res.get("facts", []))

    return {"facts": facts}