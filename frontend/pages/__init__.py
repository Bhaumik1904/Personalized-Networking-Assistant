"""
frontend/pages/__init__.py
===========================
Re-exports all tab renderers for use in frontend/app.py.
"""

from frontend.pages.fact_check_tab import render_fact_check_tab
from frontend.pages.feedback_tab import render_feedback_tab
from frontend.pages.generate_tab import render_generate_tab
from frontend.pages.history_tab import render_history_tab

__all__ = [
    "render_generate_tab",
    "render_fact_check_tab",
    "render_history_tab",
    "render_feedback_tab",
]
