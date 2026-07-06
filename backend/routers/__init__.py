"""
backend/routers/__init__.py
============================
Re-exports all FastAPI routers for registration in main.py.
"""

from backend.routers.fact_check import router as fact_check_router
from backend.routers.feedback import router as feedback_router
from backend.routers.generate import router as generate_router
from backend.routers.history import router as history_router

__all__ = [
    "generate_router",
    "fact_check_router",
    "history_router",
    "feedback_router",
]
