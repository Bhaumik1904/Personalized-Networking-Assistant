"""
backend/services/history_logger.py
=====================================
HistoryLoggerService — Persists session data to the database.

Responsibilities:
- Create or retrieve a UserProfile from the database.
- Create an EventContext with extracted themes.
- Create a NetworkingSession linking the profile and context.
- Persist all GeneratedStarter records for a session.
- Persist WikipediaFactCheck records.
- Write session-level LogEntry records.

All database writes happen in the caller's SQLAlchemy session (injected via
dependency injection). Transactions are controlled by the router layer — this
service does not commit or rollback.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models import (
    ACTION_FACT_CHECK,
    ACTION_GENERATE_STARTER,
    ACTION_SESSION_START,
    STATUS_FOUND,
    STATUS_NOT_FOUND,
    EventContext,
    GeneratedStarter,
    LogEntry,
    NetworkingSession,
    UserProfile,
    WikipediaFactCheck,
)
from backend.services.fact_checker import FactCheckResult


logger = logging.getLogger(__name__)


class HistoryLoggerService:
    """
    Writes interaction history to the database.

    All methods receive a SQLAlchemy `Session` as their first argument.
    This design makes the service stateless and easily testable with a
    test database session.

    Methods
    -------
    get_or_create_user(db, user_id, bio_text) -> UserProfile
    create_event_context(db, event_description, themes) -> EventContext
    create_session(db, user_id, event_id) -> NetworkingSession
    save_starters(db, session_id, starters_data) -> list[GeneratedStarter]
    save_fact_check(db, result, session_id) -> WikipediaFactCheck
    log_session_start(db, session_id, payload) -> LogEntry
    log_generate_action(db, session_id, payload) -> LogEntry
    log_fact_check_action(db, session_id, payload) -> LogEntry
    """

    # ------------------------------------------------------------------
    # User profile
    # ------------------------------------------------------------------

    def get_or_create_user(
        self,
        db: Session,
        user_id: Optional[str],
        bio_text: str,
    ) -> UserProfile:
        """
        Return an existing UserProfile or create a new one.

        If `user_id` is provided and a matching record exists, the bio is
        updated to reflect any changes. If `user_id` is None, a new profile
        is always created.

        Parameters
        ----------
        db : Session
            Active SQLAlchemy session.
        user_id : str | None
            UUID of an existing profile, or None to create a new one.
        bio_text : str
            Current bio text from the user.

        Returns
        -------
        UserProfile
            The existing or newly created profile.
        """
        if user_id:
            existing = db.get(UserProfile, user_id)
            if existing:
                existing.bio_text = bio_text
                existing.updated_at = datetime.now(timezone.utc)
                logger.debug("Updated existing user profile: %s", user_id)
                return existing

        # Create new profile
        profile = UserProfile(
            user_id=str(uuid.uuid4()),
            bio_text=bio_text,
        )
        db.add(profile)
        db.flush()  # Populate primary key before foreign-key references
        logger.info("Created new user profile: %s", profile.user_id)
        return profile

    # ------------------------------------------------------------------
    # Event context
    # ------------------------------------------------------------------

    def create_event_context(
        self,
        db: Session,
        event_description: str,
        themes: List[str],
    ) -> EventContext:
        """
        Persist a new EventContext record.

        Parameters
        ----------
        db : Session
        event_description : str
        themes : list[str]
            Themes extracted by EventAnalyzerService.

        Returns
        -------
        EventContext
        """
        event_ctx = EventContext(
            event_id=str(uuid.uuid4()),
            event_description=event_description,
        )
        event_ctx.set_themes(themes)
        db.add(event_ctx)
        db.flush()
        logger.info("Created event context: %s", event_ctx.event_id)
        return event_ctx

    # ------------------------------------------------------------------
    # Networking session
    # ------------------------------------------------------------------

    def create_session(
        self,
        db: Session,
        user_id: str,
        event_id: str,
    ) -> NetworkingSession:
        """
        Create and persist a new NetworkingSession.

        Parameters
        ----------
        db : Session
        user_id : str
            FK referencing user_profiles.user_id.
        event_id : str
            FK referencing event_contexts.event_id.

        Returns
        -------
        NetworkingSession
        """
        session = NetworkingSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            event_id=event_id,
        )
        db.add(session)
        db.flush()
        logger.info(
            "Created networking session: %s (user=%s, event=%s)",
            session.session_id,
            user_id,
            event_id,
        )
        return session

    # ------------------------------------------------------------------
    # Generated starters
    # ------------------------------------------------------------------

    def save_starters(
        self,
        db: Session,
        session_id: str,
        starters_data: List[dict],
    ) -> List[GeneratedStarter]:
        """
        Persist a list of generated starters for a session.

        Parameters
        ----------
        db : Session
        session_id : str
            FK referencing networking_sessions.session_id.
        starters_data : list[dict]
            Each dict must have keys "text" (str) and "prompt" (str).

        Returns
        -------
        list[GeneratedStarter]
        """
        records: List[GeneratedStarter] = []
        for item in starters_data:
            starter = GeneratedStarter(
                starter_id=str(uuid.uuid4()),
                session_id=session_id,
                starter_text=item["text"],
                context_prompt_used=item.get("prompt"),
            )
            db.add(starter)
            records.append(starter)

        db.flush()
        logger.info(
            "Saved %d starter(s) for session %s.", len(records), session_id
        )
        return records

    # ------------------------------------------------------------------
    # Fact check
    # ------------------------------------------------------------------

    def save_fact_check(
        self,
        db: Session,
        result: FactCheckResult,
        session_id: Optional[str] = None,
    ) -> WikipediaFactCheck:
        """
        Persist a WikipediaFactCheck record.

        Parameters
        ----------
        db : Session
        result : FactCheckResult
            The structured result from FactCheckerService.check().
        session_id : str | None
            Optional FK referencing networking_sessions.session_id.

        Returns
        -------
        WikipediaFactCheck
        """
        fact_check = WikipediaFactCheck(
            fact_check_id=str(uuid.uuid4()),
            session_id=session_id,
            verified_query_text=result.query,
            verification_status=STATUS_FOUND if result.is_found else STATUS_NOT_FOUND,
            summary_text=result.summary,
            wikipedia_source_url=result.source_url,
        )
        db.add(fact_check)
        db.flush()
        logger.info(
            "Saved fact check: %s (status=%s)",
            fact_check.fact_check_id,
            fact_check.verification_status,
        )
        return fact_check

    # ------------------------------------------------------------------
    # Log entries
    # ------------------------------------------------------------------

    def _create_log_entry(
        self,
        db: Session,
        action_type: str,
        session_id: Optional[str],
        payload: Optional[dict],
    ) -> LogEntry:
        """
        Internal helper: create and persist a single LogEntry.
        """
        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            session_id=session_id,
            action_type=action_type,
            payload_json=json.dumps(payload) if payload is not None else None,
        )
        db.add(entry)
        db.flush()
        logger.debug(
            "Logged action '%s' for session %s.", action_type, session_id
        )
        return entry

    def log_session_start(
        self,
        db: Session,
        session_id: str,
        payload: Optional[dict] = None,
    ) -> LogEntry:
        """Log a session-start event."""
        return self._create_log_entry(
            db, ACTION_SESSION_START, session_id, payload
        )

    def log_generate_action(
        self,
        db: Session,
        session_id: str,
        payload: Optional[dict] = None,
    ) -> LogEntry:
        """Log a generate-starter action."""
        return self._create_log_entry(
            db, ACTION_GENERATE_STARTER, session_id, payload
        )

    def log_fact_check_action(
        self,
        db: Session,
        session_id: Optional[str],
        payload: Optional[dict] = None,
    ) -> LogEntry:
        """Log a fact-check action."""
        return self._create_log_entry(
            db, ACTION_FACT_CHECK, session_id, payload
        )
