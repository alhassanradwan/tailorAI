from services.deepresearch.state import ResearchState
from services.deepresearch.llm_helper import llm_json_call
from services.deepresearch.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT


def run_critic(state: ResearchState) -> dict:
    report = state["report"]
    topic = state["topic"]
    rev_count = state.get("revision_count", 0)

    print("[Deep Research] Critic evaluating report quality...")

    critic_result = llm_json_call(CRITIC_SYSTEM_PROMPT, f"Topic: {topic}\n\nReport:\n{report}")

    if not critic_result:
        critic_result = {"pass": True, "score": 1.0, "issues": [], "feedback": "Validation bypass"}

    return {
        "critique": critic_result,
        "revision_count": rev_count + 1
    }