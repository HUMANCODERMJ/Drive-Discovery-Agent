"""LangGraph node skeletons for step 2 graph wiring."""

from langchain_core.messages import AIMessage

from agent.state import AgentState


def input_node(state: AgentState) -> dict:
    """Input passthrough node for initial graph entry."""

    _ = state
    print("[node] input_node called")
    return {}


def llm_node(state: AgentState) -> dict:
    """Placeholder LLM node that returns a hardcoded Drive query."""

    print("[node] llm_node called")
    last = state["messages"][-1]
    print(f"[node] last message: {last.content}")
    return {"query_string": "name contains 'test'"}


def tool_node(state: AgentState) -> dict:
    """Placeholder tool node that returns a fake Drive search result."""

    print("[node] tool_node called")
    print(f"[node] would search Drive with q: {state['query_string']}")
    return {
        "search_results": [
            {
                "id": "fake-id-1",
                "name": "Test File.pdf",
                "mimeType": "application/pdf",
                "modifiedTime": "2024-01-01T00:00:00Z",
                "webViewLink": "https://drive.google.com/fake",
            }
        ]
    }


def response_node(state: AgentState) -> dict:
    """Build a plain-text AI response summarizing found files."""

    print("[node] response_node called")
    if state["search_results"]:
        lines = ["I found the following files:"]
        for file_item in state["search_results"]:
            lines.append(f"• {file_item['name']} ({file_item['mimeType']})")
        reply = "\n".join(lines)
    else:
        reply = "I couldn't find any files matching your request."

    return {"messages": [AIMessage(content=reply)]}
