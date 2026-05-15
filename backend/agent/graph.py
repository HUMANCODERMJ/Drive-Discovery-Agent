"""LangGraph construction for the Drive Discovery agent skeleton."""

from langgraph.graph import END, StateGraph

from agent.nodes import input_node, llm_node, response_node, tool_node
from agent.state import AgentState


def build_graph() -> StateGraph:
    """Create and compile the step-2 linear LangGraph workflow."""

    graph = StateGraph(AgentState)

    graph.add_node("input", input_node)
    graph.add_node("llm", llm_node)
    graph.add_node("tool", tool_node)
    graph.add_node("response", response_node)

    graph.set_entry_point("input")
    graph.add_edge("input", "llm")
    graph.add_edge("llm", "tool")
    graph.add_edge("tool", "response")
    graph.add_edge("response", END)

    return graph.compile()


agent_graph = build_graph()
