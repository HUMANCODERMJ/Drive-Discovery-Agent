"""Drive Discovery Agent — Streamlit chat interface."""

import os

import streamlit as st
from dotenv import load_dotenv

from components.chat_message import render_message
from components.file_card import render_file_card
from utils.api_client import get_health, new_session_id, send_message

load_dotenv()

st.set_page_config(
    page_title="Drive Discovery Agent",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = new_session_id()
if "last_sources" not in st.session_state:
    st.session_state["last_sources"] = []
if "health" not in st.session_state:
    st.session_state["health"] = get_health()


def _render_sources(sources: list[dict]) -> None:
    """Render result cards below the assistant reply."""

    if sources:
        st.markdown("---")
        st.markdown(f"**📁 Files found ({len(sources)}):**")
        for file_item in sources:
            render_file_card(file_item)


with st.sidebar:
    st.title("🔍 Drive Agent")
    st.divider()

    health = st.session_state["health"]
    status = health.get("status", "unknown")
    llm = health.get("active_llm", "unknown")

    if status == "ok":
        st.success("Backend online")
    else:
        st.error(f"Backend: {status}")

    st.caption(f"Active LLM: **{llm}**")
    st.selectbox(
        "LLM Provider",
        ["gemini", "ollama"],
        index=0 if llm != "ollama" else 1,
        disabled=True,
        help="Switch the backend .env and restart the server to change providers.",
    )
    st.divider()
    st.markdown("**LLM Provider**")
    st.info(
        "To switch between Gemini and Ollama, change ACTIVE_LLM in the backend .env and restart the backend server.",
        icon="ℹ️",
    )
    st.divider()

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state["messages"] = []
        st.session_state["last_sources"] = []
        st.session_state["session_id"] = new_session_id()
        st.rerun()

    st.divider()
    st.caption("Drive Discovery Agent · MVP1")

st.title("🔍 Drive Discovery Agent")
st.caption(
    "Ask me to find files in your Google Drive. Try: *'find all PDFs'* or *'show me files named report'*"
)

for message in st.session_state["messages"]:
    render_message(message["role"], message["content"])

_render_sources(st.session_state["last_sources"])

user_input = st.chat_input("Search your Drive or ask a question...")

if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    render_message("user", user_input)

    with st.spinner("Searching..."):
        response = send_message(
            messages=st.session_state["messages"],
            session_id=st.session_state["session_id"],
        )

    reply = response.get("reply", "")
    sources = response.get("sources", [])

    st.session_state["messages"].append({"role": "assistant", "content": reply})
    st.session_state["last_sources"] = sources

    render_message("assistant", reply)
    _render_sources(sources)

    st.rerun()
