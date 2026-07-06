"""
frontend/pages/history_tab.py
================================
History tab — premium dashboard layout with analytics cards,
rich session cards, and proper empty states.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
import streamlit as st

from frontend.components.history_table import render_history_table
from frontend.config import api_url, config

logger = logging.getLogger(__name__)


def render_history_tab() -> None:
    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lo-hero">
          <span class="lo-eyebrow">Session Archive</span>
          <div class="lo-hero-title">History</div>
          <p class="lo-hero-sub">
            Browse all past networking sessions — event descriptions,
            extracted themes, and every generated starter.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Controls row ──────────────────────────────────────────────────────
    col_refresh, col_limit, _ = st.columns([1.6, 1.6, 5])

    with col_refresh:
        refresh_clicked = st.button(
            "Refresh",
            key="btn_refresh_history",
            icon=":material/refresh:",
            type="secondary",
            use_container_width=True,
        )

    with col_limit:
        limit = st.selectbox(
            "Per page",
            options=[10, 25, 50],
            index=0,
            key="history_limit_select",
        )

    # ── Pagination state ──────────────────────────────────────────────────
    if "history_offset" not in st.session_state:
        st.session_state["history_offset"] = 0

    if st.session_state.get("_last_history_limit") != limit:
        st.session_state["history_offset"] = 0
        st.session_state["_last_history_limit"] = limit

    # ── Auto-load ─────────────────────────────────────────────────────────
    should_load = (
        refresh_clicked
        or "history_data" not in st.session_state
        or st.session_state.get("_history_needs_reload", False)
    )

    if should_load:
        st.session_state["_history_needs_reload"] = False
        _fetch_history(limit=limit, offset=st.session_state["history_offset"])

    # ── Data ──────────────────────────────────────────────────────────────
    if "history_data" not in st.session_state:
        return

    history_data: Dict[str, Any] = st.session_state.get("history_data", {})
    sessions: List[Dict[str, Any]] = history_data.get("sessions", [])
    total: int = history_data.get("total", 0)
    current_offset: int = history_data.get("offset", 0)

    if total == 0:
        _render_empty_state()
        return

    # ── Analytics metric cards (HTML for guaranteed styling) ──────────────
    total_starters = sum(len(s.get("starters", [])) for s in sessions)
    total_feedback = sum(s.get("feedback_count", 0) for s in sessions)
    total_facts = sum(s.get("fact_check_count", 0) for s in sessions)

    st.markdown(
        f"""
        <div class="lo-metric-grid">
          <div class="lo-metric-card">
            <span class="lo-metric-label">Total Sessions</span>
            <span class="lo-metric-value">{total}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Starters</span>
            <span class="lo-metric-value">{total_starters}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Fact Checks</span>
            <span class="lo-metric-value">{total_facts}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Feedback</span>
            <span class="lo-metric-value">{total_feedback}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Section header ────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
        "font-weight:500; letter-spacing:0.08em; text-transform:uppercase; "
        "color:#7a818f; margin-bottom:14px; "
        "padding-bottom:10px; border-bottom:1px solid rgba(14,17,22,0.06);'>"
        f"Sessions — {len(sessions)} of {total}"
        "</div>",
        unsafe_allow_html=True,
    )

    render_history_table(sessions)

    # ── Pagination ────────────────────────────────────────────────────────
    if total > limit:
        _render_pagination(total=total, limit=limit, offset=current_offset)


def _fetch_history(limit: int, offset: int) -> None:
    with st.spinner("Loading session history…"):
        try:
            response = requests.get(
                api_url("/history"),
                params={"limit": limit, "offset": offset},
                timeout=config.request_timeout,
            )
            if response.status_code == 200:
                st.session_state["history_data"] = response.json()
            else:
                st.error(f"Failed to load history ({response.status_code})")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend API.")
        except requests.exceptions.Timeout:
            st.error("Request timed out.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            logger.error("History fetch failed: %s", exc, exc_info=True)


def _render_empty_state() -> None:
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
              <path d="M3 3v18h18"/>
              <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/>
            </svg>
          </div>
          <div style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em;
            color:#0e1116; margin-bottom:8px;">No sessions yet</div>
          <div style="font-size:0.875rem; color:#7a818f; max-width:42ch; margin:0 auto;">
            Generate your first conversation starters to see your history here.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_pagination(total: int, limit: int, offset: int) -> None:
    total_pages = (total + limit - 1) // limit
    current_page = (offset // limit) + 1

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if offset > 0:
            if st.button(
                "Previous",
                key="btn_prev_page",
                icon=":material/arrow_back:",
                use_container_width=True,
            ):
                st.session_state["history_offset"] = max(0, offset - limit)
                st.session_state["_history_needs_reload"] = True
                st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align:center; padding:8px 0; "
            f"font-family:\"JetBrains Mono\",monospace; font-size:0.75rem; "
            f"font-weight:500; letter-spacing:0.04em; color:#7a818f;'>"
            f"Page {current_page} of {total_pages}</div>",
            unsafe_allow_html=True,
        )

    with col_next:
        if offset + limit < total:
            if st.button(
                "Next",
                key="btn_next_page",
                icon=":material/arrow_forward:",
                use_container_width=True,
            ):
                st.session_state["history_offset"] = offset + limit
                st.session_state["_history_needs_reload"] = True
                st.rerun()
