"""Factory helpers for constructing chat models from runtime settings."""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from config import Settings


def get_llm(settings: Settings) -> BaseChatModel:
    """Return the configured chat model implementation."""

    if settings.active_llm == "gemini":
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.2,
            convert_system_message_to_human=True,
        )
    if settings.active_llm == "ollama":
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.2,
        )
    raise ValueError(f"Unknown LLM provider: {settings.active_llm}")
