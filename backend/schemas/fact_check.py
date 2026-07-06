"""
backend/schemas/fact_check.py
==============================
Pydantic v2 schemas for the GET /api/v1/fact-check endpoint.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class FactCheckResponse(BaseModel):
    """
    Response body for GET /api/v1/fact-check.

    Attributes
    ----------
    fact_check_id : str
        UUID of the persisted WikipediaFactCheck record.
    session_id : str | None
        UUID of the associated NetworkingSession (if one was provided in the
        request query parameter). None when the lookup is standalone.
    query : str
        The exact search string the caller submitted.
    summary : str | None
        Trimmed excerpt from the Wikipedia article (up to 3 sentences).
        None when status is "not_found".
    source_url : str | None
        Full URL to the matched Wikipedia page.
        None when status is "not_found".
    status : Literal["found", "not_found"]
        Indicates whether Wikipedia returned a matching article.
    verified_at : datetime
        UTC timestamp when the lookup was performed.
    """

    fact_check_id: str = Field(
        description="UUID of the WikipediaFactCheck database record."
    )
    session_id: Optional[str] = Field(
        default=None,
        description="UUID of the associated NetworkingSession (if any).",
    )
    query: str = Field(
        description="The exact search string submitted by the caller."
    )
    summary: Optional[str] = Field(
        default=None,
        description="Trimmed Wikipedia excerpt (up to 3 sentences).",
    )
    source_url: Optional[str] = Field(
        default=None,
        description="Full URL to the matched Wikipedia article.",
    )
    status: Literal["found", "not_found"] = Field(
        description="'found' if a Wikipedia article was matched, else 'not_found'."
    )
    verified_at: datetime = Field(
        description="UTC timestamp when the Wikipedia lookup was performed."
    )

    model_config = {"from_attributes": True}
