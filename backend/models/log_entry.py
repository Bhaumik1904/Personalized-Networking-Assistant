"""
backend/models/log_entry.py
=============================
SQLAlchemy ORM model for the `log_entries` table.

The log_entries table is the system-wide audit trail. Every significant
action (starter generation, fact-check request, user feedback submission)
generates a log entry. Entries optionally link back to a session.

This design enables:
- Full action replay for debugging
- Feedback aggregation for model-improvement analysis
- Usage analytics without scanning domain tables
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


# Recognised action type constants — use these to avoid raw strings
ACTION_GENERATE_STARTER = "generate_starter"
ACTION_FACT_CHECK = "fact_check"
ACTION_FEEDBACK = "feedback"
ACTION_SESSION_START = "session_start"
ACTION_ERROR = "error"


class LogEntry(Base):
    """
    Audit log entry for any system action.

    Attributes
    ----------
    log_id : str
        UUID primary key.
    session_id : str | None
        Optional foreign key → networking_sessions.session_id.
    action_type : str
        Discriminator string describing the action.
        Use the ACTION_* constants from this module.
    payload_json : str | None
        JSON-encoded blob containing action-specific data.
        For "feedback": {"starter_id": "...", "rating": "up"}.
        For "generate_starter": {"num_starters": 3, "themes": [...]}.
        For "fact_check": {"query": "...", "status": "found"}.
    timestamp : datetime
        UTC timestamp when the action was recorded.
    session : NetworkingSession | None
        Many-to-one relationship back to the owning session (if any).
    """

    __tablename__ = "log_entries"

    # ------------------------------------------------------------------
    # Columns
    # ------------------------------------------------------------------
    log_id: Mapped[str] = mapped_column(
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

    action_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            "Action discriminator: 'generate_starter' | 'fact_check' "
            "| 'feedback' | 'session_start' | 'error'"
        ),
    )

    payload_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="JSON blob with action-specific data",
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        index=True,
        comment="UTC timestamp when the action was recorded",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    session: Mapped["NetworkingSession | None"] = relationship(
        "NetworkingSession",
        back_populates="log_entries",
        lazy="select",
    )

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<LogEntry log_id={self.log_id!r} "
            f"action={self.action_type!r} "
            f"ts={self.timestamp.isoformat() if self.timestamp else None!r}>"
        )
