"""LangGraph construction for the Drive Discovery agent."""

import json

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph

from agent.nodes import input_node, llm_node, response_node, tool_node
from agent.state import AgentState


def route_after_llm(state: AgentState) -> str:
    """Route to the tool node only when the LLM requests a search."""

    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            try:
                parsed = json.loads(msg.content)
                if parsed.get("action") == "search":
                    return "tool"
            except (json.JSONDecodeError, TypeError):
                pass
            break
    return "response"


def build_graph() -> StateGraph:
    """Create and compile the LangGraph workflow."""

    graph = StateGraph(AgentState)

    graph.add_node("input", input_node)
    graph.add_node("llm", llm_node)
    graph.add_node("tool", tool_node)
    graph.add_node("response", response_node)

    graph.set_entry_point("input")
    graph.add_edge("input", "llm")
    graph.add_conditional_edges(
        "llm",
        route_after_llm,
        {
            "tool": "tool",
            "response": "response",
        },
    )
    graph.add_edge("tool", "response")
    graph.add_edge("response", END)

    return graph.compile()


agent_graph = build_graph()
