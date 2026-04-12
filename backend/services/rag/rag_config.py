"""
RAG configuration — all values from environment variables.
No hardcoded credentials.
"""

import os


class RAGConfig:
    NEO4J_URI = os.getenv("NEO4J_URI", "")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
    EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
