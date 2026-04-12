"""
RAG Router — maps DeepAgentRouter agent keys to Neo4j graph domains.

Manages singleton SharedGraphRAG instances (one per domain) and a single
shared embedding model.  All initialization is lazy: nothing loads until
the first call to retrieve().
"""

import logging
from typing import Optional

from services.rag.rag_config import RAGConfig

logger = logging.getLogger(__name__)

# agent_key (from DeepAgentRouter.route()) → SharedGraphRAG domain code
_DOMAIN_MAP = {
    "data_science": "DS",
    "machine_learning": "ML",
    "deep_learning": "DL",
}

# Singletons — created on first use, reused thereafter
_instances: dict = {}
_embedding_model = None


def _get_embedding_model():
    """Lazy-load the HuggingFace embedding model exactly once."""
    global _embedding_model
    if _embedding_model is None:
        from langchain_huggingface import HuggingFaceEmbeddings

        _embedding_model = HuggingFaceEmbeddings(
            model_name=RAGConfig.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
        )
        logger.info("RAG embedding model loaded: %s", RAGConfig.EMBEDDING_MODEL)
    return _embedding_model


class RAGRouter:
    """Stateless router — call retrieve() with an agent key and a query."""

    @staticmethod
    def retrieve(
        agent_key: str,
        query: str,
        student_context: Optional[dict] = None,
        k: int = None,
    ) -> Optional[dict]:
        """
        Retrieve graph context for *query* in the domain implied by *agent_key*.

        Returns the dict produced by SharedGraphRAG.query() on success,
        or None if the domain is unknown or retrieval fails.
        """
        domain = _DOMAIN_MAP.get(agent_key)
        if not domain:
            logger.debug("RAGRouter: unknown agent_key '%s', skipping RAG", agent_key)
            return None

        if k is None:
            k = RAGConfig.DEFAULT_TOP_K

        try:
            if domain not in _instances:
                from services.rag.graph_rag import SharedGraphRAG

                _instances[domain] = SharedGraphRAG(
                    embedding_model=_get_embedding_model(),
                    domain=domain,
                )
                logger.info("RAGRouter: initialised SharedGraphRAG for domain=%s", domain)

            return _instances[domain].query(query, student_context, k)

        except Exception as e:
            logger.warning("RAGRouter.retrieve failed (domain=%s): %s", domain, e)
            return None
