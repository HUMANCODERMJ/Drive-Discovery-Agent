"""HTTP client for communicating with the FastAPI backend."""

import os
import uuid

import httpx
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def get_health() -> dict:
    """Fetch the backend health payload."""

    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"status": "unreachable", "active_llm": "unknown"}


def send_message(messages: list[dict], session_id: str) -> dict:
    """Send a chat payload to the backend and return the JSON response."""

    try:
        response = httpx.post(
            f"{BACKEND_URL}/chat",
            json={"messages": messages, "session_id": session_id},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        return {
            "reply": payload.get("reply", ""),
            "sources": payload.get("sources", []),
        }
    except httpx.HTTPStatusError as exc:
        return {
            "reply": f"⚠️ Backend error {exc.response.status_code}: {exc.response.text}",
            "sources": [],
        }
    except Exception as exc:
        return {
            "reply": (
                f"⚠️ Could not reach the backend: {str(exc)}\n\n"
                f"Make sure the FastAPI server is running at {BACKEND_URL}"
            ),
            "sources": [],
        }


def new_session_id() -> str:
    """Return a fresh session identifier."""

    return str(uuid.uuid4())
