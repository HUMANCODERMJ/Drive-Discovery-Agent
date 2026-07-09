"""Shared LangGraph state definition for the Drive Discovery agent."""

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """State container passed across graph nodes."""

    messages: Annotated[list[BaseMessage], operator.add]
    # messages: full conversation history appended across turns.
    search_results: list[dict]
    # search_results: file dicts returned by Drive API or local filesystem.
    query_string: str
    # query_string: raw q parameter or filter dict produced by llm_node.
    active_llm: str
    # active_llm: model provider selected at invocation time ("gemini"|"ollama").
    source_type: str
    # source_type: active search source ("drive"|"local").
    preferred_llm: str
    # preferred_llm: per-request LLM override sent from frontend toggle.
    #               Empty string means fall back to active_llm from settings.
    is_voice: bool
    # is_voice: True when the request originated from the voice pipeline.
    #           response_node skips markdown link formatting when True.
    error: str
    # error: non-empty value indicates node-level failure details.