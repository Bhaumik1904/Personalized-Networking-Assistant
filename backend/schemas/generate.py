"""
backend/schemas/generate.py
=============================
Pydantic v2 request and response schemas for the POST /api/v1/generate
endpoint (conversation starter generation).

All schemas use strict typing, field-level validation, and JSON examples
so that the FastAPI OpenAPI docs at /docs are fully self-documenting.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    """
    Request body for POST /api/v1/generate.

    The caller must supply a user bio and an event description.
    The number of starters is optional (defaults to 3, capped at 5).
    An optional user_id allows the frontend to link the request to an
    existing user profile — if omitted a new profile is created.
    """

    user_bio: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description=(
            "Free-text biography of the user. Provides personalisation "
            "context for the conversation starter generation."
        ),
        examples=["I'm a data scientist focused on climate tech and AI."],
    )

    event_description: str = Field(
        ...,
        min_length=10,
        max_length=3000,
        description=(
            "Description of the networking event. May include the event "
            "name, agenda topics, speaker themes, and target audience."
        ),
        examples=[
            "AI for Sustainable Cities 2026 — a conference exploring how "
            "machine learning can accelerate urban decarbonisation."
        ],
    )

    num_starters: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Number of conversation starters to generate (1–5).",
    )

    user_id: Optional[str] = Field(
        default=None,
        description=(
            "Optional UUID of an existing user profile. If absent, a new "
            "profile is created automatically."
        ),
    )

    @field_validator("user_bio", "event_description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading/trailing whitespace from text fields."""
        if isinstance(v, str):
            return v.strip()
        return v


# ---------------------------------------------------------------------------
# Nested response schemas
# ---------------------------------------------------------------------------

class StarterOut(BaseModel):
    """
    A single generated conversation starter included in GenerateResponse.

    Attributes
    ----------
    starter_id : str
        UUID of the stored GeneratedStarter record.
    text : str
        The generated conversation starter text.
    context_prompt_used : str | None
        The prompt sent to the generative model. Included for transparency.
    """

    starter_id: str = Field(description="UUID of the GeneratedStarter record.")
    text: str = Field(description="Generated conversation starter text.")
    context_prompt_used: Optional[str] = Field(
        default=None,
        description="Full prompt used to generate this starter.",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class GenerateResponse(BaseModel):
    """
    Response body for POST /api/v1/generate.

    Contains the session and event IDs for downstream linking (e.g. when
    the user later submits a fact-check or feedback), the extracted themes,
    and the list of generated starters.
    """

    session_id: str = Field(description="UUID of the created NetworkingSession.")
    event_id: str = Field(description="UUID of the created EventContext.")
    user_id: str = Field(description="UUID of the UserProfile (new or existing).")
    themes: List[str] = Field(
        description="Themes extracted from the event description by DistilBERT."
    )
    starters: List[StarterOut] = Field(
        description="Generated conversation starters."
    )
    generated_at: datetime = Field(
        description="UTC timestamp when the response was produced."
    )

    model_config = {"from_attributes": True}
