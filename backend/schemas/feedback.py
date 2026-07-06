"""
backend/schemas/feedback.py
=============================
Pydantic v2 schemas for the feedback endpoints:
  POST /api/v1/feedback          → FeedbackRequest / FeedbackResponse
  GET  /api/v1/feedback-history  → FeedbackHistoryResponse
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# POST /api/v1/feedback — Request
# ---------------------------------------------------------------------------

class FeedbackRequest(BaseModel):
    """
    Request body for POST /api/v1/feedback.

    Attributes
    ----------
    starter_id : str
        UUID of the GeneratedStarter being rated.
    session_id : str
        UUID of the NetworkingSession that produced the starter.
    rating : Literal["up", "down"]
        The user's thumbs-up or thumbs-down rating.
    """

    starter_id: str = Field(
        description="UUID of the GeneratedStarter being rated."
    )
    session_id: str = Field(
        description="UUID of the NetworkingSession that produced the starter."
    )
    rating: Literal["up", "down"] = Field(
        description="'up' for thumbs-up, 'down' for thumbs-down."
    )


# ---------------------------------------------------------------------------
# POST /api/v1/feedback — Response
# ---------------------------------------------------------------------------

class FeedbackResponse(BaseModel):
    """
    Response body for POST /api/v1/feedback.

    Attributes
    ----------
    log_id : str
        UUID of the created LogEntry record.
    message : str
        Human-readable confirmation message.
    """

    log_id: str = Field(description="UUID of the created LogEntry record.")
    message: str = Field(description="Confirmation message.")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GET /api/v1/feedback-history — nested schema
# ---------------------------------------------------------------------------

class FeedbackEntryOut(BaseModel):
    """
    A single feedback entry for the feedback history view.

    Attributes
    ----------
    log_id : str
        UUID of the LogEntry record.
    session_id : str | None
        UUID of the associated session (if available).
    starter_id : str
        UUID of the rated starter.
    starter_text : str
        The text of the rated starter (denormalized for display convenience).
    rating : str
        "up" or "down".
    timestamp : datetime
        UTC timestamp when the feedback was recorded.
    """

    log_id: str = Field(description="UUID of the LogEntry record.")
    session_id: Optional[str] = Field(
        default=None,
        description="UUID of the associated session.",
    )
    starter_id: str = Field(description="UUID of the rated GeneratedStarter.")
    starter_text: str = Field(description="Text of the rated starter.")
    rating: str = Field(description="'up' or 'down'.")
    timestamp: datetime = Field(description="UTC timestamp of the feedback.")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GET /api/v1/feedback-history — Response
# ---------------------------------------------------------------------------

class FeedbackHistoryResponse(BaseModel):
    """
    Response body for GET /api/v1/feedback-history.

    Attributes
    ----------
    total : int
        Total number of feedback entries stored.
    feedback : list[FeedbackEntryOut]
        All feedback entries, ordered by most recent first.
    """

    total: int = Field(description="Total number of feedback entries.")
    feedback: List[FeedbackEntryOut] = Field(
        description="Feedback entries ordered by most recent first."
    )

    model_config = {"from_attributes": True}
