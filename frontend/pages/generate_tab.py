"""
frontend/pages/generate_tab.py
================================
Generate Starters tab — premium redesign with hero section,
elevated input card, and premium result cards.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests
import streamlit as st

from frontend.components.starter_card import render_starter_card
from frontend.config import api_url, config

logger = logging.getLogger(__name__)


def render_generate_tab() -> None:
    # ── Hero section ──────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="lo-hero">
          <span class="lo-eyebrow">AI Generation</span>
          <div class="lo-hero-title">Conversation Starters</div>
          <p class="lo-hero-sub">
            Describe a networking event and receive personalised, contextually
            relevant openers powered by Google Gemini and DistilBERT.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    user_bio: str = st.session_state.get("user_bio", "").strip()

    # ── Bio status banner ─────────────────────────────────────────────────
    if not user_bio:
        st.markdown(
            """
            <div class="lo-card-error">
              <strong style="display:block; margin-bottom:4px; font-size:0.875rem;">
                Profile bio not set
              </strong>
              <span style="font-size:0.8125rem; color:#7a818f;">
                Enter your bio in the sidebar — it personalises every starter we generate.
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        preview = user_bio[:140] + ("…" if len(user_bio) > 140 else "")
        st.markdown(
            f"""
            <div class="lo-card-info" style="display:flex; align-items:flex-start; gap:10px;">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24"
                fill="none" stroke="#5e6ad2" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" style="margin-top:2px; flex-shrink:0;">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <div>
                <div style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
                  font-weight:500; letter-spacing:0.06em; text-transform:uppercase;
                  color:#5e6ad2; margin-bottom:4px;">Active Profile</div>
                <div style="font-size:0.8125rem; color:#5a6273; line-height:1.5;">{preview}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

    # ── Input card ──────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(
            """
            <div style="margin-bottom:16px;">
              <div style="font-size:0.875rem; font-weight:600; letter-spacing:-0.005em;
                color:#0e1116; margin-bottom:3px;">Event Details</div>
              <div style="font-size:0.8125rem; color:#7a818f; line-height:1.5;">
                Describe the event — the more detail, the better the starters.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        event_description: str = st.text_area(
            "Event Description",
            key="event_description_input",
            placeholder=(
                "e.g. AI for Sustainable Cities 2026 — a conference exploring how machine "
                "learning can accelerate urban decarbonisation. Speakers include researchers "
                "from MIT, Stanford, and leading climate tech startups."
            ),
            height=130,
            label_visibility="collapsed",
            help="Describe the event in as much detail as possible.",
        )

        col_slider, col_count = st.columns([5, 1])
        with col_slider:
            num_starters: int = st.slider(
                "Number of starters",
                min_value=1,
                max_value=config.max_num_starters,
                value=config.default_num_starters,
                step=1,
                key="num_starters_slider",
            )
        with col_count:
            st.markdown(
                f"<div style='font-family:\"JetBrains Mono\",monospace; font-size:1.75rem; "
                f"font-weight:500; letter-spacing:-0.03em; color:#0e1116; "
                f"padding-top:24px; text-align:center;'>{num_starters}</div>",
                unsafe_allow_html=True,
            )

    # ── Action buttons ────────────────────────────────────────────────────────────
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    col_gen, col_clear, _ = st.columns([2.5, 1.2, 4.3])

    with col_gen:
        generate_clicked = st.button(
            "Generate Starters",
            key="btn_generate",
            icon=":material/auto_awesome:",
            type="primary",
            use_container_width=True,
            disabled=not user_bio or not event_description.strip(),
        )

    with col_clear:
        if st.button(
            "Clear",
            key="btn_clear_generate",
            icon=":material/refresh:",
            type="secondary",
            use_container_width=True,
        ):
            for k in ("last_starters", "last_session_id", "last_themes"):
                st.session_state.pop(k, None)
            st.rerun()

    # ── Generate ──────────────────────────────────────────────────────────
    if generate_clicked:
        if not user_bio:
            st.error("Please enter your Profile Bio in the sidebar first.")
            return
        if not event_description.strip():
            st.error("Please enter an Event Description.")
            return
        _call_generate_api(user_bio, event_description.strip(), num_starters)

    _render_results()


def _call_generate_api(user_bio: str, event_description: str, num_starters: int) -> None:
    with st.spinner("Generating conversation starters…"):
        try:
            response = requests.post(
                api_url("/generate"),
                json={
                    "user_bio": user_bio,
                    "event_description": event_description,
                    "num_starters": num_starters,
                    "user_id": st.session_state.get("user_id"),
                },
                timeout=config.generation_timeout,
            )

            if response.status_code == 200:
                data: Dict[str, Any] = response.json()
                st.session_state["last_starters"] = data.get("starters", [])
                st.session_state["last_session_id"] = data.get("session_id", "")
                st.session_state["last_themes"] = data.get("themes", [])
                st.session_state["user_id"] = data.get("user_id", "")
                st.rerun()
            elif response.status_code == 422:
                st.error(f"Validation error: {response.json().get('detail', 'Unknown')}")
            else:
                st.error(f"API error ({response.status_code}): {response.json().get('detail', 'Unknown')}")

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend API. Is the FastAPI server running?")
        except requests.exceptions.Timeout:
            st.error("Request timed out — the AI model may still be loading. Try again in 30s.")
        except Exception as exc:
            st.error(f"Unexpected error: {exc}")
            logger.error("Generate API call failed: %s", exc, exc_info=True)


def _render_results() -> None:
    starters: List[Dict[str, Any]] = st.session_state.get("last_starters", [])
    session_id: str = st.session_state.get("last_session_id", "")
    themes: List[str] = st.session_state.get("last_themes", [])

    if not starters:
        return

    # ── Results header ────────────────────────────────────────────────────
    st.markdown("<hr class='lo-divider'>", unsafe_allow_html=True)

    count = len(starters)
    session_short = session_id[-8:] if session_id else ""
    st.markdown(
        f"""
        <div style="display:flex; align-items:baseline; justify-content:space-between; margin-bottom:16px;">
          <div>
            <div style="font-size:1.0625rem; font-weight:600; letter-spacing:-0.01em; color:#0e1116;">
              {count} Starter{"s" if count != 1 else ""} Generated
            </div>
          </div>
          <div style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
            font-weight:500; letter-spacing:0.04em; text-transform:uppercase; color:#7a818f;">
            Session ···{session_short}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Theme badges ──────────────────────────────────────────────────────
    if themes:
        theme_html = "".join(
            f"<span class='lo-badge lo-badge-theme'>{t}</span>" for t in themes
        )
        st.markdown(
            f"<div style='display:flex; flex-wrap:wrap; align-items:center; gap:4px; margin-bottom:20px;'>"
            f"<span style='font-family:\"JetBrains Mono\",monospace; font-size:0.625rem; "
            f"font-weight:500; letter-spacing:0.06em; text-transform:uppercase; "
            f"color:#7a818f; margin-right:4px;'>Topics</span>"
            f"{theme_html}</div>",
            unsafe_allow_html=True,
        )

    # ── Starter cards ─────────────────────────────────────────────────────
    for i, starter in enumerate(starters, start=1):
        render_starter_card(index=i, starter=starter, session_id=session_id)
