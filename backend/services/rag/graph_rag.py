"""
SharedGraphRAG — Neo4j knowledge graph retrieval for domain-specific tutoring.

Extracted and cleaned from teammates' Colab notebooks:
  - ds_agent_with_auto_viz.py
  - ml_agent_with_auto_viz.py
  - dl_agent_with_auto_viz.py

All three notebooks contained an identical SharedGraphRAG class.
This is the single, cleaned copy.  Changes from the originals:
  - Removed hardcoded credentials (reads from RAGConfig / env)
  - Removed notebook artifacts (!pip install, os.environ[]=)
  - Added error handling around all Neo4j operations
  - Added lazy index validation
  - Added close() for clean shutdown
  - No HuggingFace LLM, no matplotlib, no agent wrappers
"""

import logging
from typing import Dict, List, Optional

from neo4j import GraphDatabase
from services.rag.rag_config import RAGConfig

logger = logging.getLogger(__name__)


class SharedGraphRAG:
    """
    Domain-filtered vector search over a shared Neo4j knowledge graph.

    The graph contains Concept nodes with vector embeddings, linked to
    Subject nodes (datascience, machinelearning, deeplearning).
    Retrieval pipeline:
        embed query → vector search → domain filter → expand context
        → find cross-domain connections → format for prompt injection.
    """

    DOMAIN_SUBJECTS = {
        "ML": "machinelearning",
        "DS": "datascience",
        "DL": "deeplearning",
    }

    VECTOR_INDEX = "concept_embedding_index"

    def __init__(self, embedding_model, domain: str):
        self.driver = GraphDatabase.driver(
            RAGConfig.NEO4J_URI,
            auth=(RAGConfig.NEO4J_USER, RAGConfig.NEO4J_PASSWORD),
        )
        self.embedding_model = embedding_model
        self.domain = domain
        subject = self.DOMAIN_SUBJECTS.get(domain, domain)
        self.subject_ids = subject if isinstance(subject, list) else [subject]
        self._index_validated = False

    # ── public API ──────────────────────────────────────────

    def query(self, question: str, student_context: Optional[dict] = None,
              k: int = 5) -> dict:
        """
        Retrieve knowledge-graph context for *question*.

        Parameters
        ----------
        question : str
            The student's message.
        student_context : dict, optional
            Must contain ``weak_topics`` (list[str]) for score boosting.
        k : int
            Number of seed concepts to retrieve.

        Returns
        -------
        dict with keys:
            primary_concepts, concepts, cross_domain_connections,
            formatted_context  (ready for prompt injection)
        """
        try:
            if not self._index_validated:
                self._validate_index()
                self._index_validated = True

            embedding = self.embedding_model.embed_query(question)
            weak_topics = (student_context or {}).get("weak_topics", [])

            seeds = self._domain_vector_search(embedding, k, weak_topics)
            expanded = self._expand_context(seeds)
            cross = self._find_cross_domain_connections(seeds)
            formatted = self._format_context(expanded, cross)

            return {
                "primary_concepts": [c["name"] for c in seeds],
                "concepts": expanded,
                "cross_domain_connections": cross,
                "formatted_context": formatted,
            }
        except Exception as e:
            logger.warning("GraphRAG query failed (domain=%s): %s", self.domain, e)
            return self._empty_result()

    def close(self):
        """Shut down the Neo4j driver cleanly."""
        if self.driver:
            try:
                self.driver.close()
            except Exception:
                pass

    # ── internals (Cypher queries identical to teammates' code) ──

    def _validate_index(self):
        with self.driver.session() as session:
            result = session.run(
                """SHOW INDEXES
                YIELD name
                WHERE name = $index
                RETURN name""",
                index=self.VECTOR_INDEX,
            )
            if not result.single():
                raise RuntimeError(
                    f"Vector index '{self.VECTOR_INDEX}' not found in Neo4j."
                )

    def _domain_vector_search(self, embedding, k, weak_topics=None):
        fetch_k = k * 4
        with self.driver.session() as session:
            result = session.run(
                """CALL db.index.vector.queryNodes($index, $fetch_k, $embedding)
                YIELD node AS c, score

                OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Subject)
                WHERE s.id IN $subjects OR toLower(s.name) IN $subjects_lower

                WITH c, score,
                CASE
                    WHEN any(w IN $weak_topics WHERE
                        replace(toLower(c.name),"_"," ") CONTAINS w OR
                        w CONTAINS replace(toLower(c.name),"_"," "))
                    THEN score * 1.15
                    ELSE score
                END AS adjusted_score

                RETURN DISTINCT
                       c.id   AS id,
                       c.name AS name,
                       elementId(c) AS eid,
                       adjusted_score AS score
                ORDER BY score DESC
                LIMIT $k""",
                index=self.VECTOR_INDEX,
                fetch_k=fetch_k,
                embedding=embedding,
                subjects=self.subject_ids,
                subjects_lower=[s.lower() for s in self.subject_ids],
                weak_topics=weak_topics or [],
                k=k,
            )
            return [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "element_id": r["eid"],
                    "adjusted_score": round(r["score"], 3),
                }
                for r in result
            ]

    def _expand_context(self, seeds):
        if not seeds:
            return []
        eids = [c["element_id"] for c in seeds]
        with self.driver.session() as session:
            result = session.run(
                """UNWIND $eids AS eid
                MATCH (c:Concept) WHERE elementId(c) = eid

                OPTIONAL MATCH (c)-[:BELONGS_TO]->(s:Subject)
                OPTIONAL MATCH (p:Concept)-[:DEPENDS_ON]->(c)
                OPTIONAL MATCH (c)-[:RELATED_TO]-(r:Concept)
                OPTIONAL MATCH (c)-[:PART_OF]->(parent:Concept)

                RETURN
                    c.id AS id,
                    c.name AS name,
                    coalesce(c.description,"") AS description,
                    collect(DISTINCT s.id) AS subjects,
                    collect(DISTINCT p.name) AS prerequisites,
                    collect(DISTINCT r.name) AS related,
                    collect(DISTINCT parent.name) AS parents""",
                eids=eids,
            )
            return [dict(r) for r in result]

    def _find_cross_domain_connections(self, seeds):
        if not seeds:
            return []
        eids = [c["element_id"] for c in seeds]
        with self.driver.session() as session:
            result = session.run(
                """UNWIND $eids AS eid
                MATCH (src:Concept) WHERE elementId(src) = eid

                MATCH (src)-[:RELATED_TO|DEPENDS_ON]->(t:Concept)
                WITH src, t

                MATCH (t)-[:BELONGS_TO]->(s:Subject)
                WHERE NOT s.id IN $subjects

                RETURN DISTINCT
                      src.name AS source,
                      t.name   AS target,
                      s.id     AS domain
                LIMIT 5""",
                eids=eids,
                subjects=self.subject_ids,
            )
            return [dict(r) for r in result]

    def _format_context(self, concepts, cross):
        if not concepts:
            return ""
        parts = [f"=== {self.domain} KNOWLEDGE GRAPH CONTEXT ==="]
        for i, c in enumerate(concepts, 1):
            parts.append(
                f"\n[{i}] {c['name']}"
                f"\nDescription: {c['description']}"
                f"\nPrerequisites: {', '.join(c['prerequisites']) or 'None'}"
                f"\nRelated: {', '.join(c['related'][:4])}"
            )
        if cross:
            parts.append("\n--- Cross-domain connections ---")
            for cx in cross:
                parts.append(f"  {cx['source']} → {cx['target']} ({cx['domain']})")
        return "\n".join(parts)

    @staticmethod
    def _empty_result():
        return {
            "primary_concepts": [],
            "concepts": [],
            "cross_domain_connections": [],
            "formatted_context": "",
        }
