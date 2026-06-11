"""Streamlit review panel (M8).

Shows the episode script (editable), image gallery with per-image re-roll,
final.mp4 player, QC report, and the auto-caption. Approve → tiktok_stub.

Run: uv run streamlit run src/ui/app.py
"""

from __future__ import annotations

import streamlit as st


def main() -> None:
    st.set_page_config(page_title="video-gen review", layout="wide")
    st.title("video-gen — review panel")
    st.info("Review UI lands in M8. Nothing to show yet.")


main()
