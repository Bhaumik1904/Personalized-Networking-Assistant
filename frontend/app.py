"""
frontend/app.py
================
Main Streamlit application — Linear Orbit design system.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from frontend.config import api_url, config, load_css
from frontend.pages.fact_check_tab import render_fact_check_tab
from frontend.pages.feedback_tab import render_feedback_tab
from frontend.pages.generate_tab import render_generate_tab
from frontend.pages.history_tab import render_history_tab

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Networking Assistant",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Inject fonts + CSS design system
# ---------------------------------------------------------------------------
st.markdown(
    """<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">""",
    unsafe_allow_html=True,
)

css = load_css()
if css:
    st.html(f"<style>{css}</style>")
else:
    logger.warning("Could not load linear_orbit.css")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_session_state() -> None:
    defaults = {
        "user_bio": "",
        "user_interests": "",
        "user_goals": "",
        "user_id": None,
        "last_session_id": "",
        "last_starters": [],
        "last_themes": [],
        "fact_check_results": [],
        "history_data": {},
        "feedback_history_data": {},
        "history_offset": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


_init_session_state()


# ---------------------------------------------------------------------------
# Sidebar — Premium settings panel
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    with st.sidebar:
        # ── App wordmark ──────────────────────────────────────────────
        st.markdown(
            """
            <div style="padding:4px 0 20px 0; border-bottom:1px solid rgba(14,17,22,0.06); margin-bottom:20px;">
              <div style="font-family:'JetBrains Mono',monospace; font-size:0.6875rem;
                          font-weight:500; letter-spacing:0.08em; text-transform:uppercase;
                          color:#5e6ad2; margin-bottom:4px;">Networking Assistant</div>
              <div style="font-family:'Inter',sans-serif; font-size:1.0625rem;
                          font-weight:600; letter-spacing:-0.01em; color:#0e1116;">
                AI Conversation Builder
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Profile section ───────────────────────────────────────────
        st.markdown(
            "<span class='lo-mono' style='display:block; margin-bottom:12px;'>Profile</span>",
            unsafe_allow_html=True,
        )

        bio = st.text_area(
            "Bio",
            key="user_bio",
            placeholder="Describe your professional background, role, and expertise…",
            height=110,
            help="Used to personalise conversation starters.",
        )

        if bio.strip():
            word_count = len(bio.split())
            st.markdown(
                f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                f"font-weight:500; letter-spacing:0.04em; color:#7a818f; margin-top:4px;'>"
                f"{word_count} words · ready</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                "font-weight:500; letter-spacing:0.04em; color:#b91c1c; margin-top:4px;'>"
                "Required for generation</div>",
                unsafe_allow_html=True,
            )

        st.text_area(
            "Interests",
            key="user_interests",
            placeholder="AI, climate tech, open source, biotech…",
            height=72,
            help="Your professional or personal interests.",
        )

        st.text_area(
            "Goals",
            key="user_goals",
            placeholder="Find co-founders, explore investment, learn from experts…",
            height=72,
            help="What you hope to achieve through networking.",
        )

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Session section ───────────────────────────────────────────
        session_id = st.session_state.get("last_session_id", "")
        themes = st.session_state.get("last_themes", [])

        if session_id:
            st.markdown(
                "<span class='lo-mono' style='display:block; margin-bottom:10px;'>Active Session</span>",
                unsafe_allow_html=True,
            )
            st.markdown(
                f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                f"color:#7a818f; word-break:break-all; margin-bottom:8px;'>{session_id}</div>",
                unsafe_allow_html=True,
            )

            if themes:
                badges = "".join(
                    f"<span style='display:inline-block; font-family:\"JetBrains Mono\",monospace; "
                    f"font-size:0.5625rem; font-weight:500; letter-spacing:0.04em; "
                    f"text-transform:uppercase; padding:2px 6px; border-radius:4px; "
                    f"background:rgba(94,106,210,0.10); color:#5e6ad2; "
                    f"border:1px solid rgba(94,106,210,0.16); margin:2px;'>{t}</span>"
                    for t in themes[:5]
                )
                st.markdown(
                    f"<div style='display:flex; flex-wrap:wrap; gap:2px;'>{badges}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<hr>", unsafe_allow_html=True)

        # ── API Status ────────────────────────────────────────────────
        _render_api_status()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ── Clear session ─────────────────────────────────────────────
        if st.button(
            "Clear Session",
            key="btn_clear_session",
            icon=":material/refresh:",
            use_container_width=True,
            help="Clear all cached results and start fresh.",
        ):
            for k in [
                "last_session_id", "last_starters", "last_themes",
                "fact_check_results", "history_data", "feedback_history_data",
            ]:
                st.session_state.pop(k, None)
            st.rerun()

        # ── Footer ────────────────────────────────────────────────────
        st.markdown(
            "<div style='margin-top:24px; font-family:\"JetBrains Mono\",monospace; "
            "font-size:0.5625rem; letter-spacing:0.04em; text-transform:uppercase; "
            "color:#e6e8ec;'>v1.0 · Linear Orbit</div>",
            unsafe_allow_html=True,
        )


def _render_api_status() -> None:
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code == 200:
            data = response.json()
            engine = data.get("generation_engine", "gemini")
            st.markdown(
                f"<div style='display:flex; align-items:center; gap:8px;'>"
                f"<div style='width:6px; height:6px; border-radius:50%; background:#22c55e;'></div>"
                f"<span style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                f"font-weight:500; letter-spacing:0.04em; text-transform:uppercase; color:#5a6273;'>"
                f"API Online · {engine}</span></div>",
                unsafe_allow_html=True,
            )
        else:
            _api_offline_badge()
    except Exception:
        _api_offline_badge()


def _api_offline_badge() -> None:
    st.markdown(
        "<div style='display:flex; align-items:center; gap:8px;'>"
        "<div style='width:6px; height:6px; border-radius:50%; background:#ef4444;'></div>"
        "<span style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
        "font-weight:500; letter-spacing:0.04em; text-transform:uppercase; color:#b91c1c;'>"
        "API Offline</span></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

def main() -> None:
    _render_sidebar()

    tab_generate, tab_fact_check, tab_history, tab_feedback = st.tabs([
        ":material/auto_awesome: Generate",
        ":material/manage_search: Fact Check",
        ":material/history: History",
        ":material/forum: Feedback",
    ])

    with tab_generate:
        render_generate_tab()

    with tab_fact_check:
        render_fact_check_tab()

    with tab_history:
        render_history_tab()

    with tab_feedback:
        render_feedback_tab()


if __name__ == "__main__":
    main()
