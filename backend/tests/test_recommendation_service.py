import pytest
import types
from services.recommendation_service import RecommendationService, _recency_boost, _normalize_topic

def test_recency_boost():
    recent = ["lstm", "rnn", "pandas", "numpy", "eda", "data_cleaning", "pca", "knn", "svm", "logistic_regression"]
    # pos 0-2 (lstm, rnn, pandas) -> +4
    assert _recency_boost("lstm", recent) == 4
    assert _recency_boost("rnn", recent) == 4
    assert _recency_boost("pandas", recent) == 4
    
    # pos 3-5 (numpy, eda, data_cleaning) -> +2
    assert _recency_boost("numpy", recent) == 2
    assert _recency_boost("data_cleaning", recent) == 2
    
    # pos 6-9 (pca, knn, svm, logistic_regression) -> +1
    assert _recency_boost("pca", recent) == 1
    assert _recency_boost("logistic_regression", recent) == 1
    
    # not in recent -> 0
    assert _recency_boost("random_topic", recent) == 0

def test_recommendation_generation_with_recency(monkeypatch):
    # Mock KnowledgeStateService.get
    fake_state = {
        "user_id": "test_user",
        "topics": {
            "lstm": {"count": 1, "mastery_level": 0.2},
        },
        "recent_topics": ["lstm"],
        "weak_topics": [],
        "strong_topics": [],
        "misconceptions": {},
    }
    monkeypatch.setattr(
        "services.recommendation_service.KnowledgeStateService.get",
        lambda user_id: fake_state
    )
    
    # Mock Neo4j to avoid DB calls
    monkeypatch.setattr(
        "services.recommendation_service._get_neo4j_related",
        lambda topics: {}
    )
    
    recs = RecommendationService.generate("test_user")
    
    assert len(recs) > 0
    topics = [r["topic"] for r in recs]
    assert "rnn" in topics or "gru" in topics
    
    for r in recs:
        assert r["score"] == 5

def test_recommendation_stale_penalty(monkeypatch):
    fake_state_weak = {
        "user_id": "test_user",
        "topics": {
            "svm": {"count": 1, "mastery_level": 0.2},
        },
        "recent_topics": ["lstm"], # svm is not recent
        "weak_topics": ["svm"], # svm is weak
        "strong_topics": [],
        "misconceptions": {},
    }
    monkeypatch.setattr(
        "services.recommendation_service.KnowledgeStateService.get",
        lambda user_id: fake_state_weak
    )
    monkeypatch.setattr(
        "services.recommendation_service._get_neo4j_related",
        lambda topics: {}
    )
    
    recs = RecommendationService.generate("test_user")
    print("STALE PENALTY RECS:", recs)
    assert len(recs) > 0
    for r in recs:
        if r["related_to"] == "svm":
            # score should be 3 (weak topic) + 1 (low mastery) - 1 (stale penalty) = 3
            assert r["score"] == 3

def test_recommendation_llm_fallback(monkeypatch):
    fake_state = {
        "user_id": "test_user",
        "topics": {
            "federated_learning": {"count": 1, "mastery_level": 0.2},
        },
        "recent_topics": ["federated_learning"],
        "weak_topics": [],
        "strong_topics": [],
        "misconceptions": {},
    }
    monkeypatch.setattr(
        "services.recommendation_service.KnowledgeStateService.get",
        lambda user_id: fake_state
    )
    monkeypatch.setattr(
        "services.recommendation_service._get_neo4j_related",
        lambda topics: {}
    )
    
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    
    class _FakeCompletions:
        def create(self, **kwargs):
            return types.SimpleNamespace(
                choices=[
                    types.SimpleNamespace(
                        message=types.SimpleNamespace(
                            content='{"federated_learning": ["differential_privacy", "secure_multi_party_computation", "client_selection", "local_training"]}'
                        )
                    )
                ]
            )

    class _FakeGroq:
        def __init__(self, api_key):
            self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setattr("groq.Groq", _FakeGroq)
    
    recs = RecommendationService.generate("test_user")
    assert len(recs) > 0
    topics = [r["topic"] for r in recs]
    assert "differential_privacy" in topics
