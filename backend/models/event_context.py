"""
backend/models/event_context.py
================================
SQLAlchemy ORM model for the `event_contexts` table.

An EventContext captures the raw event description submitted by the user and
the JSON-encoded list of themes that DistilBERT extracted from it.
Storing themes separately from the session makes it straightforward to
analyse theme popularity across many events without re-running inference.
"""

from __future__ import annotations

import json
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


class EventContext(Base):
    """
    Stores the event description and extracted themes for a networking event.

    Attributes
    ----------
    event_id : str
        UUID primary key.
    event_description : str
        The raw text the user entered describing the event (conference name,
        agenda, themes, etc.).
    analyzed_themes : str
        JSON-encoded list of theme strings extracted by DistilBERT.
        Example: '["AI", "sustainability", "urban planning"]'
    created_at : datetime
        UTC timestamp when the record was created.
    sessions : list[NetworkingSession]
        Back-populated list of networking sessions that reference this event.
    """

    __tablename__ = "event_contexts"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    event_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        comment="UUID primary key",
    )

    event_description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Raw event description entered by the user",
    )

    analyzed_themes: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="[]",
        comment="JSON-encoded list of extracted theme strings",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        comment="Record creation timestamp (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    sessions: Mapped[List["NetworkingSession"]] = relationship(
        "NetworkingSession",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def get_themes(self) -> List[str]:
        """
        Deserialise the stored JSON themes string into a Python list.

        Returns
        -------
        list[str]
            The list of theme strings, or an empty list if parsing fails.
        """
        try:
            return json.loads(self.analyzed_themes)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_themes(self, themes: List[str]) -> None:
        """
        Serialise a Python list of theme strings into the stored JSON column.

        Parameters
        ----------
        themes : list[str]
            The list of theme strings to store.
        """
        self.analyzed_themes = json.dumps(themes, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<EventContext event_id={self.event_id!r} "
            f"themes={self.get_themes()!r}>"
        )
