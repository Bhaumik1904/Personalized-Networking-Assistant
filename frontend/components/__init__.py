"""
frontend/components/__init__.py
================================
Re-exports all reusable Streamlit component renderers.
"""

from frontend.components.fact_card import render_fact_card
from frontend.components.history_table import render_history_table
from frontend.components.starter_card import render_starter_card

__all__ = [
    "render_starter_card",
    "render_fact_card",
    "render_history_table",
]
