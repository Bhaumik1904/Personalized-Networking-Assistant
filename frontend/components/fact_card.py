"""
frontend/components/fact_card.py
==================================
Premium fact-check result card with SVG status icons.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st


def render_fact_card(result: Dict[str, Any]) -> None:
    status: str = result.get("status", "not_found")
    query: str = result.get("query", "")
    summary: Optional[str] = result.get("summary")
    source_url: Optional[str] = result.get("source_url")
    verified_at: str = result.get("verified_at", "")

    is_found = status == "found"
    display_ts = _format_timestamp(verified_at)

    if is_found:
        _render_found(query, summary, source_url, display_ts)
    else:
        _render_not_found(query, display_ts)


def _render_found(
    query: str,
    summary: Optional[str],
    source_url: Optional[str],
    display_ts: str,
) -> None:
    check_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="20 6 9 17 4 12"/>'
        '</svg>'
    )

    st.markdown(
        f"""
        <div class="lo-fact-card">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:14px;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="lo-badge lo-badge-found" style="display:inline-flex; align-items:center; gap:4px;">
                {check_icon} Verified
              </span>
            </div>
            <span style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
              font-weight:500; letter-spacing:0.04em; color:#7a818f;">{display_ts}</span>
          </div>
          <h3 style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em;
            color:#0e1116; margin:0 0 10px 0;">{query}</h3>
          <p style="margin:0; font-size:0.875rem; line-height:1.65; color:#5a6273;">
            {summary or "No summary available."}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if source_url:
        external_icon = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" '
            'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>'
            '<polyline points="15 3 21 3 21 9"/>'
            '<line x1="10" y1="14" x2="21" y2="3"/>'
            '</svg>'
        )
        st.markdown(
            f"<div style='margin-top:-4px;'>"
            f"<a href='{source_url}' target='_blank' "
            f"style='font-family:\"JetBrains Mono\",monospace; font-size:0.6875rem; "
            f"font-weight:500; letter-spacing:0.04em; color:#5e6ad2; text-decoration:none; "
            f"display:inline-flex; align-items:center; gap:5px;'>"
            f"{external_icon} View on Wikipedia</a></div>",
            unsafe_allow_html=True,
        )


def _render_not_found(query: str, display_ts: str) -> None:
    x_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">'
        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'
        '</svg>'
    )

    st.markdown(
        f"""
        <div class="lo-card-error" style="margin-bottom:16px;">
          <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px;">
            <span class="lo-badge lo-badge-not-found" style="display:inline-flex; align-items:center; gap:4px;">
              {x_icon} Not Found
            </span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
              font-weight:500; color:#7a818f;">{display_ts}</span>
          </div>
          <p style="margin:0; font-size:0.875rem; color:#7a818f; line-height:1.55;">
            Wikipedia did not return a matching article for
            <strong style="color:#0e1116;">"{query}"</strong>.
            Try a more specific or differently-worded search term.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_timestamp(iso_str: str) -> str:
    if not iso_str:
        return ""
    try:
        from datetime import datetime, timezone
        clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean).astimezone(timezone.utc)
        return dt.strftime("%b %d, %Y · %H:%M UTC")
    except Exception:
        return iso_str
