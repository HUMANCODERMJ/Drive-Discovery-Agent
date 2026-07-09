"""Renders a single Google Drive file result as a styled card."""

import streamlit as st

MIME_LABELS = {
    "application/pdf": ("PDF", "🔴"),
    "application/vnd.google-apps.document": ("Google Doc", "🔵"),
    "application/vnd.google-apps.spreadsheet": ("Sheet", "🟢"),
    "application/vnd.google-apps.presentation": ("Slides", "🟡"),
    "application/vnd.google-apps.folder": ("Folder", "📁"),
}


def render_file_card(file: dict) -> None:
    """Render one Drive file as a compact info card."""

    name = file.get("name", "Unknown")
    mime = file.get("mimeType", "")
    modified = file.get("modifiedTime", "")[:10]
    link = file.get("webViewLink", "#")

    label, icon = MIME_LABELS.get(mime, ("File", "📄"))

    with st.container():
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            st.markdown(
                f"{icon} **[{name}]({link})**  \n"
                f"<sub>{label} &nbsp;·&nbsp; Modified {modified}</sub>",
                unsafe_allow_html=True,
            )
        with col2:
            st.link_button("Open", link)
        st.divider()
