"""
frontend/components/history_table.py
======================================
Premium session history cards with expandable details.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import streamlit as st

logger = logging.getLogger(__name__)


def render_history_table(sessions: List[Dict[str, Any]]) -> None:
    if not sessions:
        return  # Empty state is handled by the parent tab

    for i, session in enumerate(sessions):
        _render_session_card(session, row_index=i)


def _render_session_card(session: Dict[str, Any], row_index: int) -> None:
    session_id: str = session.get("session_id", "")
    event_desc: str = session.get("event_description", "No event description")
    themes: List[str] = session.get("themes", [])
    starters: List[Dict[str, Any]] = session.get("starters", [])
    fact_check_count: int = session.get("fact_check_count", 0)
    feedback_count: int = session.get("feedback_count", 0)
    created_at: str = session.get("created_at", "")

    display_ts = _format_timestamp(created_at)
    event_preview = (event_desc[:90] + "…") if len(event_desc) > 90 else event_desc
    session_short = session_id[:8] if session_id else "—"

    # ── Expander header ───────────────────────────────────────────────────
    header = f"{display_ts}  —  {event_preview}"

    with st.expander(header, expanded=(row_index == 0)):
        # Meta row
        col_id, col_s, col_f, col_fb = st.columns([3, 1, 1, 1])

        with col_id:
            st.markdown(
                f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                f"font-weight:500; letter-spacing:0.04em; text-transform:uppercase; "
                f"color:#7a818f; margin-bottom:4px;'>Session ID</div>"
                f"<code style='font-size:0.75rem; background:rgba(14,17,22,0.05); "
                f"padding:2px 8px; border-radius:4px; color:#0e1116;'>{session_id}</code>",
                unsafe_allow_html=True,
            )

        with col_s:
            st.metric("Starters", len(starters))

        with col_f:
            st.metric("Fact Checks", fact_check_count)

        with col_fb:
            st.metric("Feedback", feedback_count)

        # Themes
        if themes:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                "font-weight:500; letter-spacing:0.06em; text-transform:uppercase; "
                "color:#7a818f; margin:16px 0 8px 0;'>Topics</div>",
                unsafe_allow_html=True,
            )
            theme_html = "".join(
                f"<span class='lo-badge lo-badge-theme'>{t}</span>" for t in themes
            )
            st.markdown(
                f"<div style='display:flex; flex-wrap:wrap; gap:4px;'>{theme_html}</div>",
                unsafe_allow_html=True,
            )

        # Event description
        st.markdown(
            "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
            "font-weight:500; letter-spacing:0.06em; text-transform:uppercase; "
            "color:#7a818f; margin:16px 0 8px 0;'>Event</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style='font-size:0.875rem; color:#5a6273; line-height:1.6; margin:0;'>{event_desc}</p>",
            unsafe_allow_html=True,
        )

        # Starters
        if starters:
            st.markdown(
                "<div style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
                "font-weight:500; letter-spacing:0.06em; text-transform:uppercase; "
                "color:#7a818f; margin:16px 0 12px 0;'>Starters</div>",
                unsafe_allow_html=True,
            )
            for j, s in enumerate(starters, start=1):
                text = s.get("text", "")
                ts = _format_timestamp(s.get("created_at", ""))
                st.markdown(
                    f"""
                    <div class="lo-card-compact">
                      <div style="display:flex; align-items:flex-start; gap:12px;">
                        <div style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
                          font-weight:500; letter-spacing:0.04em; text-transform:uppercase;
                          color:#7a818f; padding-top:3px; flex-shrink:0;">#{j:02d}</div>
                        <p style="margin:0; font-size:0.875rem; color:#0e1116; line-height:1.6; flex:1;">{text}</p>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                "<p style='font-size:0.8125rem; color:#7a818f; font-style:italic; margin:12px 0 0;'>"
                "No starters for this session.</p>",
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
