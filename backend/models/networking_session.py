"""
backend/models/networking_session.py
=====================================
SQLAlchemy ORM model for the `networking_sessions` table.

A NetworkingSession is the central aggregate in the data model. It joins a
UserProfile to an EventContext and anchors all downstream artefacts
(generated starters, fact checks, and log entries) to a single interaction
boundary.

Cardinality:
  UserProfile (1) ──< NetworkingSession (M)
  EventContext (1) ──< NetworkingSession (M)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


if TYPE_CHECKING:
    from backend.models.event_context import EventContext
    from backend.models.generated_starter import GeneratedStarter
    from backend.models.log_entry import LogEntry
    from backend.models.user_profile import UserProfile
    from backend.models.wikipedia_fact_check import WikipediaFactCheck


def _new_uuid() -> str:
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


class NetworkingSession(Base):
    """
    Represents one complete networking interaction initiated by the user.

    A session is created each time the user submits a bio + event description
    and requests starter generation. It serves as the foreign-key anchor for
    all results produced during that request cycle.

    Attributes
    ----------
    session_id : str
        UUID primary key.
    user_id : str
        Foreign key → user_profiles.user_id.
    event_id : str
        Foreign key → event_contexts.event_id.
    session_timestamp : datetime
        UTC timestamp when the session was created.
    user : UserProfile
        Many-to-one relationship to the owning user profile.
    event : EventContext
        Many-to-one relationship to the event context for this session.
    starters : list[GeneratedStarter]
        One-to-many: all conversation starters generated in this session.
    fact_checks : list[WikipediaFactCheck]
        One-to-many: all fact-check lookups performed in this session.
    log_entries : list[LogEntry]
        One-to-many: all audit log entries for this session.
    """

    __tablename__ = "networking_sessions"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    session_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        comment="UUID primary key",
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("user_profiles.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → user_profiles.user_id",
    )

    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("event_contexts.event_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → event_contexts.event_id",
    )

    session_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        comment="UTC timestamp when the session was created",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="sessions",
        lazy="select",
    )

    event: Mapped["EventContext"] = relationship(
        "EventContext",
        back_populates="sessions",
        lazy="select",
    )

    starters: Mapped[List["GeneratedStarter"]] = relationship(
        "GeneratedStarter",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="GeneratedStarter.created_at",
    )

    fact_checks: Mapped[List["WikipediaFactCheck"]] = relationship(
        "WikipediaFactCheck",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="WikipediaFactCheck.created_at",
    )

    log_entries: Mapped[List["LogEntry"]] = relationship(
        "LogEntry",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="LogEntry.timestamp",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<NetworkingSession session_id={self.session_id!r} "
            f"user_id={self.user_id!r} event_id={self.event_id!r}>"
        )
