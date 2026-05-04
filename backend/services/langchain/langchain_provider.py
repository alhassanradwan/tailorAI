"""LangChain model provider wrapper with feature-flag gating."""

import os
from config import Config

try:
    from langchain_groq import ChatGroq
except Exception:
    ChatGroq = None


class LangChainProvider:
    @staticmethod
    def is_enabled() -> bool:
        return bool(Config.USE_LANGCHAIN)

    @staticmethod
    def is_available() -> bool:
        return bool(ChatGroq) and bool(os.getenv('GROQ_API_KEY'))

    @staticmethod
    def create_chat_model(temperature: float = 0.2, max_tokens: int = 512):
        if not LangChainProvider.is_enabled() or not LangChainProvider.is_available():
            return None

        try:
            return ChatGroq(
                model='llama-3.3-70b-versatile',
                temperature=temperature,
                max_tokens=max_tokens,
                groq_api_key=os.getenv('GROQ_API_KEY'),
            )
        except Exception:
            return None
