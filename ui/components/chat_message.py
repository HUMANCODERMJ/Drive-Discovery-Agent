"""Renders a single chat message bubble."""

import streamlit as st


def render_message(role: str, content: str) -> None:
    """Render a chat message using Streamlit's chat message container."""

    with st.chat_message(role):
        st.markdown(content)
