import types

import pytest

import services.agent_router as agent_router


def _analysis_for_prompt(prompt: str) -> dict:
    lower = (prompt or "").lower()
    question_type = "general"
    if "compare" in lower or " vs " in lower or "versus" in lower:
        question_type = "comparison"

    return {
        "topics": ["machine_learning"],
        "complexity": "intermediate",
        "question_type": question_type,
        "analysis_method": "keywords",
        "message_analysis": {
            "uncertainty_markers": 0,
            "has_code": False,
        },
        "recommendations": {
            "tutoring_mode": "direct",
            "mode_reason": "stable understanding detected",
        },
        "confidence": 0.7,
        "langchain": {
            "used": False,
            "fallback_reason": None,
        },
    }


def _setup_common_mocks(monkeypatch, langchain_result: dict):
    calls = {"langchain": 0, "native": 0}

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(agent_router.Config, "USE_LANGCHAIN", True)

    monkeypatch.setattr(
        agent_router.DeepAgentRouter,
        "analyze",
        staticmethod(lambda client, message, knowledge_state: _analysis_for_prompt(message)),
    )
    monkeypatch.setattr(
        agent_router.DeepAgentRouter,
        "route",
        staticmethod(lambda query, knowledge_state: "machine_learning"),
    )
    monkeypatch.setattr(
        agent_router.DeepAgentRouter,
        "build_system_prompt",
        staticmethod(lambda *args, **kwargs: "system-prompt"),
    )

    def _fake_langchain_generate_response(**kwargs):
        calls["langchain"] += 1
        return langchain_result

    monkeypatch.setattr(
        agent_router.LangChainGenerator,
        "generate_response",
        staticmethod(_fake_langchain_generate_response),
    )

    class _FakeCompletions:
        def create(self, **kwargs):
            calls["native"] += 1
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="native-response"))],
                usage=types.SimpleNamespace(total_tokens=123),
            )

    class _FakeGroq:
        def __init__(self, api_key):
            self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setattr(agent_router, "Groq", _FakeGroq)

    return calls


def _run_generate(prompt: str):
    return agent_router.DeepAgentRouter.generate(
        message=prompt,
        profile={"skill_level": "beginner"},
        knowledge_state={},
        chat_history=[],
    )


def test_unstructured_prompt_routes_to_native(monkeypatch):
    calls = _setup_common_mocks(
        monkeypatch,
        {
            "used": True,
            "response": "langchain-response",
            "tokens_used": 42,
            "error": None,
        },
    )

    result = _run_generate("What is gradient descent?")

    assert calls["langchain"] == 0
    assert calls["native"] == 1
    assert result["response"] == "Explanation\nnative-response"
    assert result["generation"]["path"] == "native_groq"
    assert result["generation"]["formatter_applied"] is True
    assert result["generation"]["formatter_reason"] == "general_structure"


def test_comparison_prompt_routes_to_langchain(monkeypatch):
    calls = _setup_common_mocks(
        monkeypatch,
        {
            "used": True,
            "response": "langchain-response",
            "tokens_used": 42,
            "error": None,
        },
    )

    result = _run_generate("Compare supervised and unsupervised learning")

    assert calls["langchain"] == 1
    assert calls["native"] == 0
    assert result["response"] == "langchain-response"


def test_examples_prompt_routes_to_langchain(monkeypatch):
    calls = _setup_common_mocks(
        monkeypatch,
        {
            "used": True,
            "response": "langchain-response",
            "tokens_used": 42,
            "error": None,
        },
    )

    result = _run_generate("Explain overfitting with examples")

    assert calls["langchain"] == 1
    assert calls["native"] == 0
    assert result["response"] == "langchain-response"


def test_use_cases_prompt_routes_to_langchain(monkeypatch):
    calls = _setup_common_mocks(
        monkeypatch,
        {
            "used": True,
            "response": "langchain-response",
            "tokens_used": 42,
            "error": None,
        },
    )

    result = _run_generate("When should I use PCA and when not?")

    assert calls["langchain"] == 1
    assert calls["native"] == 0
    assert result["response"] == "langchain-response"


def test_structured_fallback_routes_to_native(monkeypatch):
    calls = _setup_common_mocks(
        monkeypatch,
        {
            "used": False,
            "response": "",
            "tokens_used": 0,
            "error": "provider_or_prompt_unavailable",
        },
    )

    result = _run_generate("Compare CNN vs RNN")

    assert calls["langchain"] == 1
    assert calls["native"] == 1
    assert "Explanation\nnative-response" in result["response"]
    assert "\n\nComparison\n" in result["response"]
    assert result["generation"]["path"] == "native_groq"
    assert result["generation"]["formatter_applied"] is True
    assert result["generation"]["formatter_reason"] == "comparison_structure"
