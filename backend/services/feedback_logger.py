"""
backend/services/feedback_logger.py
======================================
FeedbackLoggerService — Persists user feedback (thumbs-up / thumbs-down)
and retrieves feedback history from the database.

Feedback is stored as a LogEntry with:
  action_type = "feedback"
  payload_json = {"starter_id": "...", "rating": "up"/"down", "starter_text": "..."}

This approach keeps feedback in the audit log rather than a separate table,
making it trivially queryable alongside all other events while still being
extractable as a distinct data set for model-improvement analysis.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.models import (
    ACTION_FEEDBACK,
    GeneratedStarter,
    LogEntry,
)
from backend.schemas.feedback import FeedbackEntryOut


logger = logging.getLogger(__name__)


class FeedbackLoggerService:
    """
    Records and retrieves user feedback on generated conversation starters.

    Methods
    -------
    record_feedback(db, starter_id, session_id, rating) -> LogEntry
        Persist one feedback action to the log_entries table.
    get_feedback_history(db, limit, offset) -> tuple[int, list[FeedbackEntryOut]]
        Return all feedback entries ordered by most recent first.
    """

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def record_feedback(
        self,
        db: Session,
        starter_id: str,
        session_id: str,
        rating: str,
    ) -> LogEntry:
        """
        Persist a thumbs-up or thumbs-down feedback entry.

        Fetches the starter text from the database to store it denormalised
        in the payload JSON — this ensures the feedback record is self-contained
        even if the starter is later deleted.

        Parameters
        ----------
        db : Session
            Active SQLAlchemy session.
        starter_id : str
            UUID of the GeneratedStarter being rated.
        session_id : str
            UUID of the NetworkingSession that produced the starter.
        rating : str
            "up" | "down"

        Returns
        -------
        LogEntry
            The newly created log entry.

        Raises
        ------
        ValueError
            If the starter_id does not exist in the database.
        """
        if rating not in ("up", "down"):
            raise ValueError(f"Invalid rating '{rating}'. Must be 'up' or 'down'.")

        # Fetch the starter text for denormalised storage in payload
        starter = db.get(GeneratedStarter, starter_id)
        if starter is None:
            raise ValueError(
                f"GeneratedStarter with id '{starter_id}' not found."
            )

        payload = {
            "starter_id": starter_id,
            "rating": rating,
            "starter_text": starter.starter_text,
        }

        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            session_id=session_id,
            action_type=ACTION_FEEDBACK,
            payload_json=json.dumps(payload),
        )
        db.add(entry)
        db.flush()

        logger.info(
            "Recorded feedback '%s' for starter %s (log_id=%s).",
            rating,
            starter_id,
            entry.log_id,
        )
        return entry

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_feedback_history(
        self,
        db: Session,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[int, List[FeedbackEntryOut]]:
        """
        Retrieve feedback log entries ordered by most recent first.

        Parameters
        ----------
        db : Session
        limit : int
            Maximum number of records to return.
        offset : int
            Zero-based record offset for pagination.

        Returns
        -------
        tuple[int, list[FeedbackEntryOut]]
            (total_count, entries_for_this_page)
        """
        base_query = (
            db.query(LogEntry)
            .filter(LogEntry.action_type == ACTION_FEEDBACK)
        )

        total = base_query.count()

        rows = (
            base_query
            .order_by(desc(LogEntry.timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

        entries: List[FeedbackEntryOut] = []
        for row in rows:
            payload = self._parse_payload(row.payload_json)
            entries.append(
                FeedbackEntryOut(
                    log_id=row.log_id,
                    session_id=row.session_id,
                    starter_id=payload.get("starter_id", ""),
                    starter_text=payload.get("starter_text", "(text unavailable)"),
                    rating=payload.get("rating", ""),
                    timestamp=row.timestamp,
                )
            )

        logger.debug(
            "Returning %d/%d feedback entries (offset=%d).",
            len(entries),
            total,
            offset,
        )
        return total, entries

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_payload(payload_json: Optional[str]) -> dict:
        """
        Safely parse a JSON payload string.

        Returns an empty dict if the string is None or invalid JSON.
        """
        if not payload_json:
            return {}
        try:
            return json.loads(payload_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse feedback payload JSON: %r", payload_json)
            return {}
