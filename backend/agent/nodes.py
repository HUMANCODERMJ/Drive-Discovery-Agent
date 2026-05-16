"""LangGraph node implementations for Drive discovery."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.prompts import QUERY_REMINDER, SYSTEM_PROMPT
from agent.state import AgentState
from config import get_settings
from services.llm_factory import get_llm
from tools.drive_tool import drive_search_tool


def input_node(state: AgentState) -> dict:
    """Pass-through node. Validates state shape."""

    _ = state
    print("[node] input_node called")
    return {}


def llm_node(state: AgentState) -> dict:
    """Send conversation history and prompt to the LLM and parse JSON output."""

    print("[node] llm_node called")
    settings = get_settings()
    llm = get_llm(settings)

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
    """Call DriveSearchTool with the q string from state."""

    print("[node] tool_node called")
    q = state.get("query_string", "")
    print(f"[node] searching Drive with q: {q}")

    try:
        results = drive_search_tool.run({"q": q})
        print(f"[node] Drive returned {len(results)} file(s)")
    except (RuntimeError, ValueError, TypeError) as exc:
        print(f"[node] Drive search error: {exc}")
        return {"search_results": [], "error": str(exc)}

    return {"search_results": results}


def response_node(state: AgentState) -> dict:
    """Format search results or chat reply into a readable response."""

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

    if state.get("error"):
        reply = (
            f"⚠️ Something went wrong while searching Drive:\n"
            f"{state['error']}\n\n"
            f"Please check your Google Drive configuration."
        )
    elif action == "search":
        results = state.get("search_results", [])
        if results:
            lines = [f"🔍 {explanation}\n"]
            lines.append(f"Found **{len(results)}** file(s):\n")
            for file_item in results:
                name = file_item.get("name", "Unknown")
                mime = file_item.get("mimeType", "")
                modified = file_item.get("modifiedTime", "")[:10]
                link = file_item.get("webViewLink", "#")
                type_map = {
                    "application/pdf": "PDF",
                    "application/vnd.google-apps.document": "Google Doc",
                    "application/vnd.google-apps.spreadsheet": "Sheet",
                    "application/vnd.google-apps.presentation": "Slides",
                    "application/vnd.google-apps.folder": "Folder",
                }
                type_label = type_map.get(mime, mime.split("/")[-1] if mime else "file")
                lines.append(f"• [{name}]({link}) — {type_label}, modified {modified}")
            reply = "\n".join(lines)
        else:
            reply = (
                f"🔍 {explanation}\n\n"
                f"No files found matching your request. Try a different search term or file type."
            )
    else:
        reply = explanation

    return {"messages": [AIMessage(content=reply)]}
