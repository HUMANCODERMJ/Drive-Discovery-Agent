"""LangGraph node implementations for Drive discovery and local filesystem search."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.prompts import QUERY_REMINDER, SYSTEM_PROMPT
from agent.state import AgentState
from config import get_settings
from services.llm_factory import get_llm
from tools.drive_tool import drive_search_tool
from tools.fs_tool import local_search_tool


def input_node(state: AgentState) -> dict:
    """Pass-through node. Validates state shape."""

    _ = state
    print("[node] input_node called")
    return {}


def llm_node(state: AgentState) -> dict:
    """Send conversation history and prompt to the LLM and parse JSON output.

    Respects preferred_llm from state for per-request LLM switching.
    Falls back to active_llm from settings if preferred_llm is empty.
    """

    print("[node] llm_node called")
    settings = get_settings()

    preferred = state.get("preferred_llm", "").strip()
    if preferred in ("gemini", "ollama"):
        from copy import copy as _copy
        effective_settings = _copy(settings)
        object.__setattr__(effective_settings, "active_llm", preferred)
        llm = get_llm(effective_settings)
        print(f"[node] using preferred LLM: {preferred}")
    else:
        llm = get_llm(settings)
        print(f"[node] using default LLM: {settings.active_llm}")

    system_msg = SystemMessage(content=SYSTEM_PROMPT)
    reminder = HumanMessage(content=QUERY_REMINDER)
    messages_to_send = [system_msg] + list(state["messages"]) + [reminder]

    response = llm.invoke(messages_to_send)
    raw_text = response.content.strip()
    print(f"[node] LLM raw response: {raw_text}")

    clean = raw_text
    if clean.startswith("```"):
        parts = clean.split("```")
        if len(parts) > 1:
            clean = parts[1]
            if clean.startswith("json"):
                clean = clean[4:]
    clean = clean.strip()

    try:
        parsed = json.loads(clean)
    except json.JSONDecodeError:
        print("[node] WARNING: LLM did not return valid JSON, treating as chat")
        parsed = {"action": "chat", "q": "", "explanation": raw_text}

    action = parsed.get("action", "chat")
    q_string = parsed.get("q", "")
    print(f"[node] action={action}, q={q_string}")

    return {
        "query_string": q_string,
        "messages": [AIMessage(content=json.dumps(parsed))],
    }


def tool_node(state: AgentState) -> dict:
    """Route to DriveSearchTool or LocalSearchTool based on source_type in state."""

    print("[node] tool_node called")
    source = state.get("source_type", "drive")
    print(f"[node] source_type={source}")

    if source == "local":
        return _run_local_search(state)
    return _run_drive_search(state)


def _run_drive_search(state: AgentState) -> dict:
    """Execute Drive search using q string from state."""

    q = state.get("query_string", "")
    print(f"[node] searching Drive with q: {q}")

    try:
        results = drive_search_tool.run({"q": q})
        print(f"[node] Drive returned {len(results)} file(s)")
    except (RuntimeError, ValueError, TypeError) as exc:
        print(f"[node] Drive search error: {exc}")
        return {"search_results": [], "error": str(exc)}

    return {"search_results": results}


def _run_local_search(state: AgentState) -> dict:
    """Execute local filesystem search by parsing the LLM query_string as JSON filters."""

    raw_q = state.get("query_string", "")
    print(f"[node] searching local FS with filters: {raw_q}")

    # llm_node stores filters as a JSON string for local searches.
    # Expected shape: {"name_contains": "...", "extensions": [...],
    #                  "modified_after": "...", "modified_before": "..."}
    try:
        filters: dict = json.loads(raw_q) if raw_q.strip().startswith("{") else {}
    except json.JSONDecodeError:
        filters = {}

    try:
        results = local_search_tool.run(filters)
        print(f"[node] local FS returned {len(results)} file(s)")
    except (RuntimeError, ValueError, TypeError) as exc:
        print(f"[node] local FS search error: {exc}")
        return {"search_results": [], "error": str(exc)}

    return {"search_results": results}


def response_node(state: AgentState) -> dict:
    """Format search results or chat reply into a readable response.

    When is_voice=True, strips markdown link syntax so TTS reads cleanly.
    """

    print("[node] response_node called")

    last_ai_content = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            last_ai_content = msg.content
            break

    try:
        parsed = json.loads(last_ai_content)
        action = parsed.get("action", "chat")
        explanation = parsed.get("explanation", "")
    except (json.JSONDecodeError, TypeError):
        action = "chat"
        explanation = last_ai_content

    is_voice: bool = state.get("is_voice", False)
    source: str = state.get("source_type", "drive")

    if state.get("error"):
        source_label = "local filesystem" if source == "local" else "Google Drive"
        reply = (
            f"⚠️ Something went wrong while searching {source_label}:\n"
            f"{state['error']}\n\n"
            f"Please check your configuration."
        )
    elif action == "search":
        results = state.get("search_results", [])
        if results:
            lines = [f"{explanation}\n"]
            lines.append(f"Found **{len(results)}** file(s):\n")
            for file_item in results:
                name = file_item.get("name", "Unknown")
                mime = file_item.get("mimeType", "")
                modified = (file_item.get("modifiedTime", "") or "")[:10]

                type_map = {
                    "application/pdf": "PDF",
                    "application/vnd.google-apps.document": "Google Doc",
                    "application/vnd.google-apps.spreadsheet": "Sheet",
                    "application/vnd.google-apps.presentation": "Slides",
                    "application/vnd.google-apps.folder": "Folder",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word Doc",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel",
                    "text/csv": "CSV",
                    "text/plain": "Text",
                    "text/markdown": "Markdown",
                    "text/x-python": "Python",
                }
                type_label = type_map.get(mime, mime.split("/")[-1] if mime else "File")

                if source == "local":
                    path = file_item.get("path", "")
                    size_bytes = file_item.get("size", 0)
                    size_kb = round(size_bytes / 1024, 1)
                    if is_voice:
                        lines.append(f"• {name} — {type_label}, modified {modified}")
                    else:
                        lines.append(
                            f"• **{name}** — {type_label}, modified {modified}, "
                            f"{size_kb} KB  \n  `{path}`"
                        )
                else:
                    link = file_item.get("webViewLink", "#")
                    if is_voice:
                        lines.append(f"• {name} — {type_label}, modified {modified}")
                    else:
                        lines.append(
                            f"• [{name}]({link}) — {type_label}, modified {modified}"
                        )

            reply = "\n".join(lines)
        else:
            reply = (
                f"{explanation}\n\n"
                "No files found matching your request. "
                "Try a different search term or file type."
            )
    else:
        reply = explanation

    return {"messages": [AIMessage(content=reply)]}