"""
backend/schemas/history.py
===========================
Pydantic v2 schemas for the GET /api/v1/history endpoint.

Returns a paginated list of past networking sessions, each including the
event description, extracted themes, generated starters, and feedback counts.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Nested schemas
# ---------------------------------------------------------------------------

class StarterHistoryOut(BaseModel):
    """
    Slim representation of a generated starter for the history view.

    Attributes
    ----------
    starter_id : str
        UUID of the GeneratedStarter record.
    text : str
        The generated starter text.
    created_at : datetime
        UTC timestamp when the starter was generated.
    """

    starter_id: str = Field(description="UUID of the GeneratedStarter record.")
    text: str = Field(description="Generated conversation starter text.")
    created_at: datetime = Field(description="UTC timestamp of generation.")

    model_config = {"from_attributes": True}


class SessionHistoryOut(BaseModel):
    """
    Summary of a single networking session for the history view.

    Attributes
    ----------
    session_id : str
        UUID of the NetworkingSession.
    event_description : str
        The event description entered by the user.
    themes : list[str]
        Themes extracted from the event description.
    starters : list[StarterHistoryOut]
        The starters generated in this session.
    fact_check_count : int
        Number of Wikipedia fact-checks performed during the session.
    feedback_count : int
        Number of feedback entries (thumbs-up/down) linked to this session.
    created_at : datetime
        UTC timestamp when the session was created.
    """

    session_id: str = Field(description="UUID of the NetworkingSession.")
    event_description: str = Field(
        description="Raw event description entered by the user."
    )
    themes: List[str] = Field(
        default_factory=list,
        description="Themes extracted from the event description.",
    )
    starters: List[StarterHistoryOut] = Field(
        default_factory=list,
        description="Starters generated in this session.",
    )
    fact_check_count: int = Field(
        default=0,
        description="Number of Wikipedia fact-checks in this session.",
    )
    feedback_count: int = Field(
        default=0,
        description="Number of thumbs-up/down feedback entries.",
    )
    created_at: datetime = Field(
        description="UTC timestamp when the session was created."
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Top-level response schema
# ---------------------------------------------------------------------------

class HistoryResponse(BaseModel):
    """
    Paginated response body for GET /api/v1/history.

    Attributes
    ----------
    total : int
        Total number of sessions stored in the database.
    limit : int
        Number of sessions returned in this page.
    offset : int
        Zero-based offset of the first session in this page.
    sessions : list[SessionHistoryOut]
        The sessions for the current page.
    """

    total: int = Field(description="Total number of sessions in the database.")
    limit: int = Field(description="Number of sessions in this page.")
    offset: int = Field(description="Zero-based offset of the first session.")
    sessions: List[SessionHistoryOut] = Field(
        description="Sessions for the current page."
    )

    model_config = {"from_attributes": True}
