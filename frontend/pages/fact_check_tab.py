"""
frontend/pages/fact_check_tab.py
===================================
Fact Check tab — premium redesign with hero, elevated search card,
premium result cards, and rich empty state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
import streamlit as st

from frontend.components.fact_card import render_fact_card
from frontend.config import api_url, config

logger = logging.getLogger(__name__)


def render_fact_check_tab() -> None:
    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lo-hero">
          <span class="lo-eyebrow">Wikipedia Verification</span>
          <div class="lo-hero-title">Fact Check</div>
          <p class="lo-hero-sub">
            Look up any topic, concept, or technology on Wikipedia. Get a verified
            summary and source link to ground your networking conversations in facts.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Search card ───────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <div style="margin-bottom:16px;">
              <div style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em;
                color:#0e1116; margin-bottom:4px;">Search Wikipedia</div>
              <div style="font-size:0.8125rem; color:#5a6273;">
                Enter a topic as you would search for it on Wikipedia. Precise names work best.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        query: str = st.text_input(
            "Topic",
            key="fact_check_query_input",
            placeholder="e.g. blockchain in healthcare, urban heat islands, GPT-4…",
            label_visibility="collapsed",
        )

        current_session_id: str = st.session_state.get("last_session_id", "")
        link_to_session = False

        if current_session_id:
            st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
            link_to_session = st.checkbox(
                f"Link to session ···{current_session_id[-8:]}",
                value=True,
                key="fact_check_link_session",
                help="Records this fact-check in your current session history.",
            )

    # ── Action buttons ────────────────────────────────────────────────────
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)
    col_check, col_clear, _ = st.columns([3, 1.5, 3])

    with col_check:
        check_clicked = st.button(
            "Check Wikipedia",
            key="btn_fact_check",
            icon=":material/search:",
            type="primary",
            use_container_width=True,
            disabled=not query.strip(),
        )

    with col_clear:
        if st.button(
            "Clear",
            key="btn_clear_fact",
            icon=":material/refresh:",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state.pop("fact_check_results", None)
            st.rerun()

    # ── API call ──────────────────────────────────────────────────────────
    if check_clicked and query.strip():
        _call_fact_check_api(
            query=query.strip(),
            session_id=current_session_id if link_to_session else None,
        )

    _render_results()


def _call_fact_check_api(query: str, session_id: str | None) -> None:
    with st.spinner(f'Searching Wikipedia for "{query}"…'):
        try:
            params: Dict[str, Any] = {"query": query}
            if session_id:
                params["session_id"] = session_id

            response = requests.get(
                api_url("/fact-check"),
                params=params,
                timeout=config.request_timeout,
            )

            if response.status_code == 200:
                result: Dict[str, Any] = response.json()
                results: List[Dict[str, Any]] = st.session_state.get("fact_check_results", [])
                results.insert(0, result)
                st.session_state["fact_check_results"] = results[:10]
                st.rerun()
            elif response.status_code == 422:
                st.error(f"Validation error: {response.json().get('detail', 'Unknown')}")
            else:
                st.error(f"API error ({response.status_code})")

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend API.")
        except requests.exceptions.Timeout:
            st.error("Request timed out. Please try again.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            logger.error("Fact-check failed: %s", exc, exc_info=True)


def _render_results() -> None:
    results: List[Dict[str, Any]] = st.session_state.get("fact_check_results", [])

    if not results:
        # ── Empty state ───────────────────────────────────────────────
        st.markdown(
            """
            <div style="text-align:center; padding:80px 24px; margin-top:32px;
              background:#ffffff; border-radius:10px;
              border:1px solid rgba(14,17,22,0.06);
              box-shadow:rgba(14,17,22,0.06) 0 0 0 1px,rgba(14,17,22,0.03) 0 1px 2px;">
              <div style="margin-bottom:20px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 24 24"
                  fill="none" stroke="#e6e8ec" stroke-width="1.5" stroke-linecap="round"
                  stroke-linejoin="round">
                  <circle cx="11" cy="11" r="8"/>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
              </div>
              <div style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em;
                color:#0e1116; margin-bottom:8px;">No searches yet</div>
              <div style="font-size:0.875rem; color:#7a818f; max-width:40ch; margin:0 auto;">
                Enter a topic above to query Wikipedia and verify facts.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown("<hr class='lo-divider'>", unsafe_allow_html=True)

    # ── Most recent result ────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
        "font-weight:500; letter-spacing:0.06em; text-transform:uppercase; "
        "color:#7a818f; margin-bottom:12px;'>Latest Result</div>",
        unsafe_allow_html=True,
    )
    render_fact_card(results[0])

    # ── Previous results ──────────────────────────────────────────────────
    if len(results) > 1:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        with st.expander(f"Previous searches ({len(results) - 1})", expanded=False):
            for old in results[1:]:
                render_fact_card(old)
