"""FastAPI entrypoint for the Drive Discovery Agent backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import get_settings
from services.llm_factory import get_llm


class ChatRequest(BaseModel):
    """Incoming chat payload for a client session."""

    messages: list[dict] = Field(default_factory=list)
    session_id: str


class ChatResponse(BaseModel):
    """Static chat response used for scaffold validation."""

    reply: str
    sources: list = Field(default_factory=list)


app = FastAPI(title="Drive Discovery Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mask_folder_id(folder_id: str) -> str:
    """Return a redacted Drive folder id to avoid exposing full value."""

    return f"{folder_id[:8]}..."


@app.on_event("startup")
async def startup_event() -> None:
    """Warm up app configuration and attempt to initialize the active LLM."""

    settings = get_settings()
    print(f"[startup] active LLM: {settings.active_llm}")
    try:
        get_llm(settings)
        print("[startup] LLM loaded OK")
    except Exception as exc:  # pylint: disable=broad-exception-caught  # pragma: no cover
        print(f"[startup] warning: failed to load LLM: {exc}")


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health and a small subset of runtime configuration."""

    settings = get_settings()
    return {
        "status": "ok",
        "active_llm": settings.active_llm,
        "ollama_url": settings.ollama_base_url,
        "drive_folder_id": _mask_folder_id(settings.drive_folder_id),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Return a placeholder chat response until agent wiring is implemented."""

    _ = request
    return ChatResponse(
        reply="Agent not yet connected. Step 1 complete.",
        sources=[],
    )
