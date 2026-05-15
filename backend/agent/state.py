"""Shared LangGraph state definition for the Drive Discovery agent."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State container passed across graph nodes."""

    messages: Annotated[list[BaseMessage], operator.add]
    # messages: full conversation history appended across turns.
    search_results: list[dict]
    # search_results: file dictionaries returned by Drive API.
    query_string: str
    # query_string: raw Drive q parameter produced by LLM node.
    active_llm: str
    # active_llm: model provider selected at invocation time.
    error: str
    # error: non-empty value indicates node-level failure details.
