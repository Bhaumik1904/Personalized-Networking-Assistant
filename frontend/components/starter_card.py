"""
frontend/components/starter_card.py
=====================================
Premium conversation starter card with copy, thumbs-up/down buttons.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import requests
import streamlit as st

from frontend.config import api_url, config

logger = logging.getLogger(__name__)


def render_starter_card(
    index: int,
    starter: Dict[str, Any],
    session_id: str,
    on_feedback: Optional[Callable[[str, str, str], None]] = None,
) -> None:
    starter_id: str = starter.get("starter_id", "")
    text: str = starter.get("text", "")

    # Card HTML — index label + starter text
    st.markdown(
        f"""
        <div class="lo-card">
          <div style="display:flex; align-items:flex-start; gap:14px;">
            <div style="font-family:'JetBrains Mono',monospace; font-size:0.625rem;
              font-weight:500; letter-spacing:0.06em; text-transform:uppercase;
              color:#7a818f; padding-top:3px; flex-shrink:0; min-width:32px;">
              {index:02d}
            </div>
            <p style="margin:0; font-size:0.9375rem; line-height:1.65;
              color:#0e1116; letter-spacing:-0.005em; flex:1;">
              {text}
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action row
    col_copy, col_up, col_down, _ = st.columns([2, 1.2, 1.2, 4])

    with col_copy:
        if st.button(
            "Copy",
            key=f"copy_{starter_id}_{index}",
            icon=":material/content_copy:",
            type="secondary",
            use_container_width=True,
        ):
            _copy_to_clipboard(text)
            st.toast("Copied to clipboard!", icon="✅")

    with col_up:
        if st.button(
            "Helpful",
            key=f"up_{starter_id}_{index}",
            icon=":material/thumb_up:",
            type="tertiary",
            use_container_width=True,
        ):
            _submit_feedback(starter_id, session_id, "up", on_feedback)

    with col_down:
        if st.button(
            "Nope",
            key=f"down_{starter_id}_{index}",
            icon=":material/thumb_down:",
            type="tertiary",
            use_container_width=True,
        ):
            _submit_feedback(starter_id, session_id, "down", on_feedback)

    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)


def _submit_feedback(
    starter_id: str,
    session_id: str,
    rating: str,
    on_feedback: Optional[Callable] = None,
) -> None:
    try:
        response = requests.post(
            api_url("/feedback"),
            json={"starter_id": starter_id, "session_id": session_id, "rating": rating},
            timeout=config.request_timeout,
        )
        if response.status_code == 201:
            label = "Helpful" if rating == "up" else "Noted"
            st.toast(f"Feedback recorded — {label}", icon="✅")
            if on_feedback:
                on_feedback(starter_id, session_id, rating)
        else:
            st.toast("Could not save feedback — try again.", icon="⚠️")
    except requests.exceptions.ConnectionError:
        st.toast("Cannot reach the API.", icon="⚠️")
    except Exception as exc:
        st.toast("An unexpected error occurred.", icon="⚠️")
        logger.error("Feedback submission error: %s", exc, exc_info=True)


def _copy_to_clipboard(text: str) -> None:
    escaped = text.replace("`", "\\`").replace("\\", "\\\\")
    js = f"""
    <script>
    (function() {{
        const el = document.createElement('textarea');
        el.value = `{escaped}`;
        el.setAttribute('readonly', '');
        el.style.position = 'absolute';
        el.style.left = '-9999px';
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
    }})();
    </script>
    """
    import streamlit.components.v1 as components
    components.html(js, height=0, scrolling=False)
