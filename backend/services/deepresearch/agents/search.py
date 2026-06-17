import os
import requests
from concurrent.futures import ThreadPoolExecutor
from services.deepresearch.state import ResearchState

def perform_search(query: str):
    tavily_key = os.getenv("TAVILY_API_KEY")

    if not tavily_key:
        raise ValueError("TAVILY_API_KEY is not set")

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "query": query,
                "api_key": tavily_key,
                "search_depth": "advanced",
                "max_results": 3
            },
            timeout=10
        )

        resp.raise_for_status()
        data = resp.json()

        return [
            {"url": r.get("url"), "content": r.get("content")}
            for r in data.get("results", [])
        ]

    except Exception as e:
        print(f"[Search Error] Query: {query} | Error: {e}")
        return []  # return empty instead of fake data


def run_search(state: ResearchState) -> dict:
    plan = state.get("plan", [])

    print(f"[Deep Research] Searching for {len(plan)} subtopics...")

    documents = []

    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(perform_search, plan))

    for res in results:
        documents.extend(res)

    return {"documents": documents}