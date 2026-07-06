"""
backend/models/user_profile.py
================================
SQLAlchemy ORM model for the `user_profiles` table.

A UserProfile stores the user's bio text and an optional cache of their most
recently described event. In this project, users are anonymous sessions
identified by a UUID that is generated server-side and persisted to the
browser via Streamlit session state.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, String, Text, func
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


class UserProfile(Base):
    """
    Represents a user's persistent profile in the networking assistant.

    Attributes
    ----------
    user_id : str
        UUID primary key.
    bio_text : str
        Free-text biography the user provides. Used as personalisation
        context when generating conversation starters.
    current_event_cache : str | None
        Optional cached copy of the event description from the most recent
        networking session. Allows the UI to pre-populate the event field.
    created_at : datetime
        UTC timestamp when the profile was first created.
    updated_at : datetime
        UTC timestamp auto-updated whenever the row is modified.
    sessions : list[NetworkingSession]
        Back-populated list of all networking sessions belonging to this user.
    """

    __tablename__ = "user_profiles"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    user_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        comment="UUID primary key",
    )

    bio_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="User-provided bio for personalisation context",
    )

    current_event_cache: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Cached event description from the most recent session",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        comment="Record creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=func.now(),
        comment="Record last-modified timestamp (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    sessions: Mapped[List["NetworkingSession"]] = relationship(
        "NetworkingSession",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<UserProfile user_id={self.user_id!r} "
            f"bio_len={len(self.bio_text) if self.bio_text else 0}>"
        )
