"""FastAPI entrypoint for the Drive Discovery Agent backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agent.graph import agent_graph
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
    """Invoke the LangGraph skeleton and return its generated response."""

    settings = get_settings()
    user_content = ""
    for msg in request.messages:
        if msg.get("role") == "user":
            user_content = msg.get("content", "")

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
