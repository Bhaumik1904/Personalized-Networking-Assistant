"""
backend/models/generated_starter.py
======================================
SQLAlchemy ORM model for the `generated_starters` table.

Each row stores one AI-generated conversation starter produced during a
networking session, along with the context prompt that was used to generate
it (enabling reproducibility and prompt analysis).
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


class GeneratedStarter(Base):
    """
    A single AI-generated conversation starter belonging to a session.

    Attributes
    ----------
    starter_id : str
        UUID primary key.
    session_id : str
        Foreign key → networking_sessions.session_id.
    starter_text : str
        The generated conversation starter text presented to the user.
    context_prompt_used : str | None
        The full prompt string sent to the generation model. Stored for
        reproducibility, debugging, and future prompt-optimisation work.
    created_at : datetime
        UTC timestamp when the starter was generated.
    session : NetworkingSession
        Many-to-one relationship back to the owning session.
    """

    __tablename__ = "generated_starters"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    starter_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=_new_uuid,
        comment="UUID primary key",
    )

    session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("networking_sessions.session_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK → networking_sessions.session_id",
    )

    starter_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The generated conversation starter text",
    )

    context_prompt_used: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="Full prompt string used to generate this starter",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        comment="UTC timestamp when the starter was generated",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    session: Mapped["NetworkingSession"] = relationship(
        "NetworkingSession",
        back_populates="starters",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        preview = (self.starter_text[:60] + "...") if len(self.starter_text) > 60 else self.starter_text
        return (
            f"<GeneratedStarter starter_id={self.starter_id!r} "
            f"text={preview!r}>"
        )
