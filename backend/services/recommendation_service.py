"""
AdaptiveAI — Recommendation Service
Generates personalized topic recommendations based on:
  - Recent topics the student has asked about (recency-weighted)
  - Student mastery data (weak areas, misconceptions)
  - Knowledge graph relationships (Neo4j primary, fallback dict)
  - LLM-based topic expansion for topics outside the knowledge graph

Uses the existing Neo4j knowledge graph for topic relationships,
with a hardcoded fallback for when Neo4j is unavailable, and
an LLM fallback for topics not in either graph.
"""

import logging
import os
import json
from typing import Dict, List, Optional

from services.knowledge_state import KnowledgeStateService

logger = logging.getLogger(__name__)

# ── In-memory cache for LLM-generated topic relationships ───
# Avoids repeated API calls for the same topics within a server session.
_llm_topic_cache: Dict[str, List[str]] = {}

# ── Hardcoded fallback graph ────────────────────────────────
# Used when Neo4j is unavailable. Maps topic → related topics.
# Covers the core DS/ML/DL curriculum.
FALLBACK_GRAPH: Dict[str, List[str]] = {
    # Deep Learning
    "lstm": ["rnn", "gru", "transformers", "sequence_models", "vanishing_gradients", "time_series"],
    "rnn": ["lstm", "gru", "sequence_models", "backpropagation_through_time", "vanishing_gradients"],
    "gru": ["lstm", "rnn", "sequence_models", "gated_recurrent_units"],
    "transformers": ["attention_mechanism", "self_attention", "bert", "gpt", "positional_encoding", "lstm"],
    "attention_mechanism": ["transformers", "self_attention", "seq2seq", "encoder_decoder"],
    "self_attention": ["transformers", "attention_mechanism", "multi_head_attention"],
    "bert": ["transformers", "nlp", "word_embeddings", "transfer_learning", "fine_tuning"],
    "gpt": ["transformers", "language_models", "text_generation", "fine_tuning"],
    "cnn": ["convolution", "pooling", "image_classification", "transfer_learning", "feature_maps"],
    "convolution": ["cnn", "feature_maps", "kernel", "stride", "padding"],
    "pooling": ["cnn", "max_pooling", "average_pooling", "dimensionality_reduction"],
    "backpropagation": ["gradient_descent", "chain_rule", "loss_functions", "neural_networks", "vanishing_gradients"],
    "vanishing_gradients": ["lstm", "rnn", "batch_normalization", "residual_connections", "relu"],
    "transfer_learning": ["fine_tuning", "pretrained_models", "cnn", "bert", "feature_extraction"],
    "dropout": ["regularization", "overfitting", "batch_normalization"],
    "batch_normalization": ["dropout", "training_stability", "vanishing_gradients", "deep_networks"],
    "autoencoders": ["variational_autoencoders", "dimensionality_reduction", "generative_models", "representation_learning"],
    "gan": ["generative_models", "discriminator", "generator", "image_synthesis", "variational_autoencoders"],
    "neural_networks": ["perceptron", "activation_functions", "backpropagation", "loss_functions", "deep_learning"],
    "activation_functions": ["relu", "sigmoid", "softmax", "neural_networks"],

    # Machine Learning
    "gradient_descent": ["learning_rate", "sgd", "adam_optimizer", "backpropagation", "loss_functions", "convergence"],
    "overfitting": ["regularization", "dropout", "cross_validation", "bias_variance_tradeoff", "early_stopping"],
    "underfitting": ["model_complexity", "feature_engineering", "bias_variance_tradeoff"],
    "regularization": ["l1_regularization", "l2_regularization", "dropout", "overfitting", "elastic_net"],
    "cross_validation": ["k_fold", "train_test_split", "model_evaluation", "overfitting", "hyperparameter_tuning"],
    "decision_trees": ["random_forest", "gradient_boosting", "xgboost", "pruning", "feature_importance"],
    "random_forest": ["decision_trees", "bagging", "ensemble_methods", "feature_importance"],
    "gradient_boosting": ["xgboost", "lightgbm", "decision_trees", "ensemble_methods", "learning_rate"],
    "xgboost": ["gradient_boosting", "lightgbm", "catboost", "hyperparameter_tuning"],
    "svm": ["kernel_trick", "classification", "margin", "support_vectors", "hyperplane"],
    "knn": ["distance_metrics", "classification", "regression", "curse_of_dimensionality"],
    "clustering": ["k_means", "hierarchical_clustering", "dbscan", "unsupervised_learning", "silhouette_score"],
    "k_means": ["clustering", "elbow_method", "centroids", "unsupervised_learning"],
    "pca": ["dimensionality_reduction", "eigenvalues", "feature_extraction", "variance"],
    "linear_regression": ["polynomial_regression", "loss_functions", "gradient_descent", "ordinary_least_squares"],
    "logistic_regression": ["classification", "sigmoid", "binary_classification", "softmax"],
    "ensemble_methods": ["bagging", "boosting", "random_forest", "gradient_boosting", "stacking"],
    "hyperparameter_tuning": ["grid_search", "random_search", "bayesian_optimization", "cross_validation"],
    "feature_engineering": ["feature_selection", "one_hot_encoding", "normalization", "standardization"],
    "bias_variance_tradeoff": ["overfitting", "underfitting", "model_complexity", "generalization"],
    "loss_functions": ["mse", "cross_entropy", "gradient_descent", "backpropagation"],

    # Data Science
    "data_cleaning": ["missing_values", "outlier_detection", "data_preprocessing", "feature_engineering"],
    "missing_values": ["imputation", "data_cleaning", "mean_imputation", "knn_imputation"],
    "outlier_detection": ["iqr", "z_score", "data_cleaning", "anomaly_detection"],
    "eda": ["data_visualization", "statistics", "correlation", "distribution", "pandas"],
    "data_visualization": ["matplotlib", "seaborn", "plotly", "eda", "charts"],
    "pandas": ["dataframes", "data_manipulation", "groupby", "merge", "data_cleaning"],
    "numpy": ["arrays", "linear_algebra", "vectorization", "mathematical_operations"],
    "statistics": ["probability", "hypothesis_testing", "confidence_intervals", "distributions"],
    "probability": ["bayes_theorem", "distributions", "conditional_probability", "statistics"],
    "hypothesis_testing": ["p_value", "t_test", "chi_square", "anova", "statistics"],
    "correlation": ["pearson", "spearman", "causation", "feature_selection"],
    "normalization": ["standardization", "min_max_scaling", "feature_engineering", "preprocessing"],

    # NLP
    "nlp": ["tokenization", "word_embeddings", "sentiment_analysis", "text_classification", "transformers"],
    "word_embeddings": ["word2vec", "glove", "fasttext", "nlp", "bert"],
    "tokenization": ["nlp", "text_preprocessing", "word_embeddings"],
    "sentiment_analysis": ["nlp", "text_classification", "opinion_mining"],

    # Evaluation
    "model_evaluation": ["accuracy", "precision", "recall", "f1_score", "confusion_matrix", "roc_auc"],
    "confusion_matrix": ["precision", "recall", "model_evaluation", "classification"],
    "precision": ["recall", "f1_score", "model_evaluation", "confusion_matrix"],
    "recall": ["precision", "f1_score", "model_evaluation", "confusion_matrix"],
}


def _normalize_topic(topic: str) -> str:
    """Lowercase, strip, replace spaces with underscores."""
    return topic.strip().lower().replace(" ", "_").replace("-", "_")


def _get_neo4j_related(topics: List[str]) -> Dict[str, List[str]]:
    """
    Query Neo4j for RELATED_TO and DEPENDS_ON neighbours of *topics*.

    Returns { topic_name: [related_name, ...] } — or empty dict on failure.
    This is a lightweight Cypher query (no vector search / embeddings).
    """
    try:
        from services.rag.rag_config import RAGConfig
        if not RAGConfig.NEO4J_URI:
            return {}

        from neo4j import GraphDatabase  # type: ignore[import-not-found]
        driver = GraphDatabase.driver(
            RAGConfig.NEO4J_URI,
            auth=(RAGConfig.NEO4J_USER, RAGConfig.NEO4J_PASSWORD),
        )

        topic_names = [t.replace("_", " ") for t in topics]

        with driver.session() as session:
            result = session.run(
                """
                UNWIND $names AS name
                MATCH (c:Concept)
                WHERE toLower(c.name) = toLower(name)
                   OR toLower(replace(c.name, '_', ' ')) = toLower(name)

                OPTIONAL MATCH (c)-[:RELATED_TO]-(r:Concept)
                OPTIONAL MATCH (c)-[:DEPENDS_ON]-(d:Concept)
                OPTIONAL MATCH (child:Concept)-[:PART_OF]->(c)

                WITH c.name AS source,
                     collect(DISTINCT r.name) + collect(DISTINCT d.name) + collect(DISTINCT child.name) AS neighbours

                RETURN source, neighbours
                """,
                names=topic_names,
            )
            mapping = {}
            for record in result:
                src = _normalize_topic(record["source"])
                neighbours = [
                    _normalize_topic(n)
                    for n in record["neighbours"]
                    if n is not None
                ]
                if neighbours:
                    mapping[src] = neighbours
            return mapping

        driver.close()

    except Exception as e:
        logger.debug("Neo4j related-topic lookup skipped: %s", e)
        return {}


def _get_llm_related_topics(topics: List[str]) -> Dict[str, List[str]]:
    """
    LLM fallback: ask Groq to suggest related topics for topics not in
    the hardcoded graph or Neo4j.

    Uses an in-memory cache to avoid repeated API calls for the same topic.
    Returns { topic: [related1, related2, ...] } or empty dict on failure.
    """
    global _llm_topic_cache

    # Filter to only topics not already cached
    uncached = [t for t in topics if t not in _llm_topic_cache]
    if not uncached:
        return {t: _llm_topic_cache[t] for t in topics if t in _llm_topic_cache}

    try:
        from groq import Groq

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {}

        client = Groq(api_key=api_key)

        topics_str = ", ".join(t.replace("_", " ") for t in uncached)
        prompt = f"""For each of the following topics, suggest 4-6 closely related topics 
that a student learning about them should explore next. Focus on prerequisite concepts, 
complementary topics, and natural learning progressions.

Topics: {topics_str}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "topic_name": ["related1", "related2", "related3", "related4"],
  ...
}}

Use lowercase with underscores for topic names (e.g., "neural_networks", "gradient_descent").
Only include topics relevant to data science, machine learning, deep learning, programming, 
mathematics, or computer science."""

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )

        result = json.loads(completion.choices[0].message.content)

        # Normalize and cache the results
        for raw_topic, related_list in result.items():
            norm_topic = _normalize_topic(raw_topic)
            if isinstance(related_list, list):
                normalized_related = [_normalize_topic(r) for r in related_list if isinstance(r, str)]
                _llm_topic_cache[norm_topic] = normalized_related

        # Return only the requested topics
        return {t: _llm_topic_cache[t] for t in topics if t in _llm_topic_cache}

    except Exception as e:
        logger.debug("LLM related-topic lookup failed: %s", e)
        return {}


def _recency_boost(topic: str, recent_topics: List[str]) -> int:
    """
    Calculate a score boost based on how recently the topic was discussed.

    recent_topics is ordered most-recent-first (ring buffer from knowledge_state).
    Position 0-2: +4 boost (just discussed)
    Position 3-5: +2 boost (recently discussed)
    Position 6-9: +1 boost (discussed a while ago)
    """
    norm = _normalize_topic(topic)
    normalized_recent = [_normalize_topic(t) for t in recent_topics]

    if norm not in normalized_recent:
        return 0

    pos = normalized_recent.index(norm)
    if pos <= 2:
        return 4
    elif pos <= 5:
        return 2
    else:
        return 1


class RecommendationService:
    """Generate personalized topic recommendations for a student."""

    MAX_RECOMMENDATIONS = 6

    @staticmethod
    def generate(user_id: str) -> List[dict]:
        """
        Return up to MAX_RECOMMENDATIONS topic suggestions.

        Each item: { topic, reason, score, related_to }

        Recommendations are dynamically weighted by:
        - Recency: topics the student asked about most recently get priority
        - Weakness: weak topics and misconceptions boost related candidates
        - Exploration: frequently-asked topics suggest unexplored neighbors
        - Staleness: topics not discussed recently are deprioritized
        """
        ks = KnowledgeStateService.get(user_id)

        topics_map = ks.get("topics", {})
        weak_topics = set(ks.get("weak_topics", []))
        strong_topics = set(ks.get("strong_topics", []))
        misconceptions = ks.get("misconceptions", {})
        recent_topics = ks.get("recent_topics", [])

        # Normalise explored topic names
        explored = {
            _normalize_topic(t): td
            for t, td in topics_map.items()
            if isinstance(td, dict)
        }
        explored_names = set(explored.keys())

        if not explored_names and not weak_topics:
            return []

        # Normalise recent topics for lookups
        recent_normalized = [_normalize_topic(t) for t in recent_topics]
        recent_set = set(recent_normalized)

        # ── 1. Build relationship map (Neo4j first, fallback second) ──
        # Prioritize recent topics — query them first so their neighbors
        # appear as candidates even if the full history is large.
        all_student_topics = list(explored_names | weak_topics)
        graph_map = _get_neo4j_related(all_student_topics)

        # Merge fallback graph for any topics not found in Neo4j
        topics_without_graph: List[str] = []
        for t in all_student_topics:
            if t not in graph_map:
                fb = FALLBACK_GRAPH.get(t, [])
                if fb:
                    graph_map[t] = fb
                else:
                    topics_without_graph.append(t)

        # ── 1b. LLM fallback for topics with no graph neighbors ───────
        # Only query for recent topics that have no graph coverage
        # (avoids LLM calls for old forgotten topics).
        llm_candidates = [t for t in topics_without_graph if t in recent_set]
        if llm_candidates:
            llm_map = _get_llm_related_topics(llm_candidates)
            for t, related in llm_map.items():
                if t not in graph_map and related:
                    graph_map[t] = related

        # ── 2. Collect candidate topics and score them ──────────────
        candidates: Dict[str, dict] = {}  # topic -> { score, reasons[], related_to }

        for source_topic, related_list in graph_map.items():
            source_norm = _normalize_topic(source_topic)
            source_data = explored.get(source_norm, {})
            source_mastery = source_data.get("mastery_level", 0)
            source_count = source_data.get("count", 0)

            # Calculate how much recency boost this source topic gets
            source_recency = _recency_boost(source_norm, recent_topics)

            for related in related_list:
                related_norm = _normalize_topic(related)

                # Skip if student already has significant mastery
                if related_norm in explored_names:
                    rel_data = explored[related_norm]
                    if rel_data.get("mastery_level", 0) >= 0.6:
                        continue
                    if rel_data.get("count", 0) >= 5:
                        continue

                if related_norm in strong_topics:
                    continue

                if related_norm not in candidates:
                    candidates[related_norm] = {
                        "score": 0,
                        "reasons": [],
                        "related_to": source_norm,
                    }

                cand = candidates[related_norm]

                # ── Recency boost: related to what user is currently studying ──
                if source_recency > 0:
                    cand["score"] += source_recency
                    if source_recency >= 4:
                        cand["reasons"].insert(0,
                            f"Directly related to what you're currently studying: {source_norm.replace('_', ' ')}"
                        )
                    elif source_recency >= 2:
                        cand["reasons"].append(
                            f"Related to your recent study of {source_norm.replace('_', ' ')}"
                        )

                # Score: related to a weak topic
                if source_norm in {_normalize_topic(w) for w in weak_topics}:
                    cand["score"] += 3
                    cand["reasons"].append(
                        f"Could strengthen your understanding of {source_norm.replace('_', ' ')}"
                    )

                # Score: has a misconception in the parent topic
                if source_norm in {_normalize_topic(m) for m in misconceptions}:
                    misc = misconceptions.get(source_topic, misconceptions.get(source_norm, {}))
                    if isinstance(misc, dict) and not misc.get("corrected", False):
                        cand["score"] += 2
                        cand["reasons"].append(
                            f"May help clarify your misconception about {source_norm.replace('_', ' ')}"
                        )

                # Score: related to a frequently asked topic (but candidate is unexplored)
                if source_count >= 3 and related_norm not in explored_names:
                    cand["score"] += 2
                    cand["reasons"].append(
                        f"Related to your study of {source_norm.replace('_', ' ')}"
                    )

                # Score: parent topic has low mastery
                if source_mastery > 0 and source_mastery < 0.4:
                    cand["score"] += 1
                    cand["reasons"].append(
                        f"Could help improve your mastery of {source_norm.replace('_', ' ')}"
                    )

                # Score: candidate is lightly explored (1-2 interactions) — nudge them deeper
                if related_norm in explored_names:
                    rel_data = explored[related_norm]
                    if rel_data.get("count", 0) <= 2 and rel_data.get("mastery_level", 0) < 0.4:
                        cand["score"] += 1
                        cand["reasons"].append(
                            f"You've started exploring {related_norm.replace('_', ' ')} — keep going!"
                        )

        # ── 2b. Deprioritize stale candidates ─────────────────────────
        # Candidates whose source topic hasn't been discussed recently
        # get a small penalty so fresh recommendations rank higher.
        for topic, data in candidates.items():
            source = data.get("related_to", "")
            if source and source not in recent_set:
                data["score"] -= 1

        # ── 3. Rank and return top recommendations ──────────────────
        ranked = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)

        results = []
        seen = set()
        for topic, data in ranked:
            if topic in seen:
                continue
            if data["score"] <= 0:
                continue
            seen.add(topic)

            # Pick the best reason (highest priority = first unique)
            reason = data["reasons"][0] if data["reasons"] else "Suggested based on your learning history"

            results.append({
                "topic": topic,
                "reason": reason,
                "score": data["score"],
                "related_to": data["related_to"],
            })

            if len(results) >= RecommendationService.MAX_RECOMMENDATIONS:
                break

        return results
