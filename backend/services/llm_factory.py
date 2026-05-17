"""Factory helpers for constructing chat models from runtime settings."""

from typing import TYPE_CHECKING

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from config import Settings

if TYPE_CHECKING:
    from typing import Any


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


def validate_llm(settings: Settings) -> tuple[bool, str]:
    """Perform a minimal live probe against the configured LLM provider."""

    try:
        llm = get_llm(settings)

        if settings.active_llm == "gemini":
            response = llm.invoke([HumanMessage(content="Hi")])
            if not response or not getattr(response, "content", ""):
                return False, "Gemini returned empty response"
            return True, "ok"

        if settings.active_llm == "ollama":
            import httpx

            base = settings.ollama_base_url.rstrip("/")
            resp = httpx.get(f"{base}/api/tags", timeout=5)
            if resp.status_code != 200:
                return False, f"Ollama server returned {resp.status_code}"
            models = [model.get("name", "") for model in resp.json().get("models", [])]
            model_name = settings.ollama_model.split(":")[0]
            if not any(model_name in model for model in models):
                return (
                    False,
                    f"Model '{settings.ollama_model}' not found in Ollama. Available: {models}",
                )
            return True, "ok"

        return False, f"Unknown LLM provider: {settings.active_llm}"
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return False, str(exc)
