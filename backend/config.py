"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed app configuration loaded from .env and environment."""

    gemini_api_key: str
    google_sa_json: str
    drive_folder_id: str
    ollama_base_url: str = "http://localhost:11434"
    active_llm: Literal["gemini", "ollama"] = "gemini"
    ollama_model: str = "llama3.2"
    gemini_model: str = "gemini-1.5-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance so config is parsed once."""

    return Settings()


PLACEHOLDER_PATTERNS = [
    "your_",
    "placeholder",
    "changeme",
    "xxxx",
    "example",
    "",
]


def is_placeholder(value: str) -> bool:
    """Return True if a config value looks like it was never filled in."""

    v = value.strip().lower()
    for pattern in PLACEHOLDER_PATTERNS:
        if pattern == "":
            if v == "":
                return True
            continue
        if v.startswith(pattern) or v == pattern:
            return True
    return False
