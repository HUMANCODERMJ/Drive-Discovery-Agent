"""FastAPI entrypoint for the Drive Discovery Agent backend."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
import httpx
from pydantic import BaseModel, Field

from agent.graph import agent_graph
from config import get_settings, is_placeholder
from services.llm_factory import validate_llm


class MessageItem(BaseModel):
    """Single chat message item."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Incoming chat payload for a client session."""

    messages: list[MessageItem]
    session_id: str = ""


class ChatResponse(BaseModel):
    """Static chat response used for scaffold validation."""

    reply: str
    sources: list = Field(default_factory=list)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    """Application lifespan for startup validation and shutdown logging."""

    _ = fastapi_app
    settings = get_settings()
    print(f"[startup] active LLM: {settings.active_llm}")

    if settings.active_llm == "gemini" and is_placeholder(settings.gemini_api_key):
        print(
            "[startup] WARNING: GEMINI_API_KEY looks like a placeholder. "
            "Set a real key in .env or switch ACTIVE_LLM=ollama."
        )
        try:
            base = settings.ollama_base_url.rstrip("/")
            resp = httpx.get(f"{base}/api/tags", timeout=5)
            if resp.status_code == 200:
                print("[startup] Ollama is reachable, but ACTIVE_LLM is still gemini.")
            else:
                print(
                    f"[startup] WARNING: Ollama is not reachable (status {resp.status_code}). "
                    "Server will start, but /chat will fail until Gemini is configured or Ollama is reachable."
                )
        except httpx.HTTPError as exc:  # pragma: no cover - network probe warning path
            print(
                f"[startup] WARNING: Ollama is not reachable: {exc}. "
                "Server will start, but /chat will fail until Gemini is configured or Ollama is reachable."
            )
    else:
        ok, reason = validate_llm(settings)
        if ok:
            print(f"[startup] LLM '{settings.active_llm}' validated OK")
        else:
            print(f"[startup] WARNING: LLM '{settings.active_llm}' validation FAILED: {reason}")
            print(
                "[startup] Server will still start, but /chat will fail until the LLM issue is resolved."
            )

    yield

    print("[shutdown] Drive Discovery Agent shutting down.")


app = FastAPI(title="Drive Discovery Agent API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _mask_folder_id(folder_id: str) -> str:
    """Return a redacted Drive folder id to avoid exposing full value."""

    return f"{folder_id[:8]}..."


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
    """Invoke the LangGraph skeleton and return its generated response."""

    settings = get_settings()
    user_content = ""
    user_messages = [message for message in request.messages if message.role == "user"]
    if user_messages:
        user_content = user_messages[-1].content

    initial_state: dict = {
        "messages": [HumanMessage(content=user_content)],
        "search_results": [],
        "query_string": "",
        "active_llm": settings.active_llm,
        "error": "",
    }

    result = agent_graph.invoke(initial_state)

    reply = ""
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and msg.__class__.__name__ == "AIMessage":
            reply = msg.content
            break

    return ChatResponse(
        reply=reply,
        sources=result.get("search_results", []),
    )
