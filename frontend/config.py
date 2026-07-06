"""
frontend/config.py
===================
Frontend configuration: API base URL, request timeouts, and shared defaults.

All frontend modules import from this module rather than reading environment
variables or hardcoding values directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FrontendConfig:
    """
    Immutable configuration for the Streamlit frontend.

    Attributes
    ----------
    api_base_url : str
        Base URL of the FastAPI backend, without trailing slash.
    request_timeout : int
        HTTP request timeout in seconds for regular calls.
        Generation can take longer — use generation_timeout.
    generation_timeout : int
        HTTP request timeout for POST /generate (AI inference may be slow).
    default_num_starters : int
        Default value for the number-of-starters slider.
    max_num_starters : int
        Maximum selectable value for the number-of-starters slider.
    history_page_size : int
        Default number of sessions to load in the history tab.
    feedback_page_size : int
        Default number of feedback entries to load.
    css_path : Path
        Absolute path to the Linear Orbit CSS file.
    app_title : str
        Page title shown in the browser tab.
    app_icon : str
        Emoji icon for the browser tab.
    """

    api_base_url: str = field(
        default_factory=lambda: os.getenv(
            "API_BASE_URL", "http://localhost:8000/api/v1"
        )
    )
    request_timeout: int = 10
    generation_timeout: int = 60      # Gemini + DistilBERT can take up to 30s
    default_num_starters: int = 3
    max_num_starters: int = 5
    history_page_size: int = 20
    feedback_page_size: int = 50

    css_path: Path = field(
        default_factory=lambda: Path(__file__).parent / "styles" / "linear_orbit.css"
    )

    app_title: str = "Personalized Networking Assistant"
    app_icon: str = "🤝"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

config = FrontendConfig()


# ---------------------------------------------------------------------------
# API URL helpers
# ---------------------------------------------------------------------------

def api_url(path: str) -> str:
    """
    Build a full API URL by appending `path` to the base URL.

    Parameters
    ----------
    path : str
        Endpoint path, e.g. "/generate" or "/fact-check".

    Returns
    -------
    str
        Full URL, e.g. "http://localhost:8000/api/v1/generate".

    Examples
    --------
    >>> api_url("/generate")
    'http://localhost:8000/api/v1/generate'
    """
    base = config.api_base_url.rstrip("/")
    path_clean = "/" + path.lstrip("/")
    return f"{base}{path_clean}"


def load_css() -> str:
    """
    Read and return the Linear Orbit CSS file contents.

    Returns
    -------
    str
        Full CSS string, or an empty string if the file cannot be read.
    """
    try:
        return config.css_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""
    except Exception:
        return ""
