"""
frontend/pages/feedback_tab.py
================================
Feedback tab — premium dashboard with analytics metrics,
feedback cards with SVG icons, and rich empty state.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests
import streamlit as st

from frontend.config import api_url, config

logger = logging.getLogger(__name__)


def render_feedback_tab() -> None:
    # ── Hero ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lo-hero">
          <span class="lo-eyebrow">Model Improvement</span>
          <div class="lo-hero-title">Feedback History</div>
          <p class="lo-hero-sub">
            Review thumbs-up and thumbs-down ratings submitted on generated
            conversation starters. This data helps track what resonates most.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Refresh control ──────────────────────────────────────────────────────
    col_refresh, _ = st.columns([1.6, 6.4])
    with col_refresh:
        refresh_clicked = st.button(
            "Refresh",
            key="btn_refresh_feedback",
            icon=":material/refresh:",
            type="secondary",
            use_container_width=True,
        )

    # ── Auto-load ─────────────────────────────────────────────────────────
    if refresh_clicked or "feedback_history_data" not in st.session_state:
        _fetch_feedback_history()

    if "feedback_history_data" not in st.session_state:
        return

    data: Dict[str, Any] = st.session_state.get("feedback_history_data", {})
    feedback_entries: List[Dict[str, Any]] = data.get("feedback", [])
    total: int = data.get("total", 0)

    if total == 0 or not feedback_entries:
        _render_empty_state()
        return

    # ── Analytics metric cards (HTML for guaranteed styling) ──────────────
    up_count = sum(1 for e in feedback_entries if e.get("rating") == "up")
    down_count = sum(1 for e in feedback_entries if e.get("rating") == "down")
    rate = f"{round(up_count / total * 100)}%" if total > 0 else "—"

    st.markdown(
        f"""
        <div class="lo-metric-grid">
          <div class="lo-metric-card">
            <span class="lo-metric-label">Total Feedback</span>
            <span class="lo-metric-value">{total}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Helpful</span>
            <span class="lo-metric-value" style="color:#15803d;">{up_count}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Needs Work</span>
            <span class="lo-metric-value" style="color:#b91c1c;">{down_count}</span>
          </div>
          <div class="lo-metric-card">
            <span class="lo-metric-label">Approval Rate</span>
            <span class="lo-metric-value" style="color:#5e6ad2;">{rate}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Section header ────────────────────────────────────────────────────
    st.markdown(
        "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
        "font-weight:500; letter-spacing:0.08em; text-transform:uppercase; "
        "color:#7a818f; margin-bottom:16px; "
        "padding-bottom:12px; border-bottom:1px solid rgba(14,17,22,0.06);'>"
        "All entries — most recent first"
        "</div>",
        unsafe_allow_html=True,
    )

    _render_feedback_table(feedback_entries)


def _fetch_feedback_history() -> None:
    with st.spinner("Loading feedback history…"):
        try:
            response = requests.get(
                api_url("/feedback-history"),
                params={"limit": config.feedback_page_size, "offset": 0},
                timeout=config.request_timeout,
            )
            if response.status_code == 200:
                st.session_state["feedback_history_data"] = response.json()
            else:
                st.error(f"Failed to load feedback ({response.status_code})")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend API.")
        except requests.exceptions.Timeout:
            st.error("Request timed out.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            logger.error("Feedback history fetch failed: %s", exc, exc_info=True)


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
              <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7
                8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8
                8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
            </svg>
          </div>
          <div style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em;
            color:#0e1116; margin-bottom:8px;">No feedback yet</div>
          <div style="font-size:0.875rem; color:#7a818f; max-width:44ch; margin:0 auto;">
            Use the thumbs-up / thumbs-down buttons on generated starters to record feedback.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_feedback_table(entries: List[Dict[str, Any]]) -> None:
    ICON_UP = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>'
        '</svg>'
    )
    ICON_DOWN = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/>'
        '</svg>'
    )

    for entry in entries:
        rating: str = entry.get("rating", "")
        starter_text: str = entry.get("starter_text", "(unavailable)")
        session_id: str = entry.get("session_id") or ""
        timestamp: str = entry.get("timestamp", "")

        is_up = rating == "up"
        icon_svg = ICON_UP if is_up else ICON_DOWN
        badge_class = "lo-badge-found" if is_up else "lo-badge-not-found"
        badge_label = "Helpful" if is_up else "Needs Work"
        icon_color = "#15803d" if is_up else "#b91c1c"
        session_short = session_id[:8] if session_id else "unknown"
        display_ts = _format_timestamp(timestamp)

        st.markdown(
            f"""
            <div class="lo-card-compact">
              <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
                <div style="display:flex; align-items:center; gap:8px;">
                  <span style="display:flex; align-items:center; color:{icon_color};">{icon_svg}</span>
                  <span class="lo-badge {badge_class}">{badge_label}</span>
                </div>
                <div style="display:flex; align-items:center; gap:16px;">
                  <span style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
                    font-weight:500; letter-spacing:0.04em; text-transform:uppercase;
                    color:#7a818f;">···{session_short}</span>
                  <span style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
                    font-weight:500; color:#7a818f;">{display_ts}</span>
                </div>
              </div>
              <p style="margin:0; font-size:0.875rem; color:#5a6273; line-height:1.55;">
                {starter_text}
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _format_timestamp(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        from datetime import datetime, timezone
        clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean).astimezone(timezone.utc)
        return dt.strftime("%b %d · %H:%M")
    except Exception:
        return iso_str
