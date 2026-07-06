"""
backend/models/wikipedia_fact_check.py
========================================
SQLAlchemy ORM model for the `wikipedia_fact_checks` table.

Stores the result of every Wikipedia fact-check lookup, including the
user's query, the verification status, a trimmed summary, and the source URL.
The session_id link is nullable because a fact-check may be performed
outside the context of a starter-generation session.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


if TYPE_CHECKING:
    from backend.models.networking_session import NetworkingSession


def _new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# Allowed values for the verification_status column
STATUS_FOUND = "found"
STATUS_NOT_FOUND = "not_found"


class WikipediaFactCheck(Base):
    """
    Records the outcome of a Wikipedia fact-verification request.

    Attributes
    ----------
    fact_check_id : str
        UUID primary key.
    session_id : str | None
        Optional foreign key → networking_sessions.session_id.
        Null when a fact-check is performed outside a generation session.
    verified_query_text : str
        The exact search string submitted to the Wikipedia API.
    verification_status : str
        Either "found" or "not_found".
    wikipedia_source_url : str | None
        Full URL to the matched Wikipedia page (None if not found).
    summary_text : str | None
        Trimmed summary extracted from the Wikipedia page (None if not found).
    created_at : datetime
        UTC timestamp when the fact-check was performed.
    session : NetworkingSession | None
        Many-to-one relationship back to the owning session (if any).
    """

    __tablename__ = "wikipedia_fact_checks"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    fact_check_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        comment="UUID primary key",
    )

    session_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("networking_sessions.session_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK → networking_sessions.session_id (nullable)",
    )

    verified_query_text: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Search query string submitted to the Wikipedia API",
    )

    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=STATUS_NOT_FOUND,
        comment="'found' | 'not_found'",
    )

    wikipedia_source_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        default=None,
        comment="Full URL to the matched Wikipedia page",
    )

    summary_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Trimmed summary extracted from the Wikipedia page",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        comment="UTC timestamp when the fact-check was performed",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    session: Mapped["NetworkingSession | None"] = relationship(
        "NetworkingSession",
        back_populates="fact_checks",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<WikipediaFactCheck fact_check_id={self.fact_check_id!r} "
            f"query={self.verified_query_text!r} "
            f"status={self.verification_status!r}>"
        )
