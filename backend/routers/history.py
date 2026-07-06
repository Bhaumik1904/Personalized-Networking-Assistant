"""
backend/routers/history.py
============================
FastAPI router for GET /api/v1/history.

Returns a paginated list of past networking sessions with their themes,
generated starters, fact-check counts, and feedback counts.
"""

from __future__ import annotations

import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import (
    ACTION_FEEDBACK,
    EventContext,
    GeneratedStarter,
    LogEntry,
    NetworkingSession,
    WikipediaFactCheck,
)
from backend.schemas.history import (
    HistoryResponse,
    SessionHistoryOut,
    StarterHistoryOut,
)


logger = logging.getLogger(__name__)

router = APIRouter(tags=["History"])


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=HistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve session history",
    description=(
        "Returns a paginated list of past networking sessions ordered by "
        "most recent first. Each session includes the event description, "
        "extracted themes, generated starters, and aggregated counts for "
        "fact-checks and feedback submissions."
    ),
    response_description="Paginated list of past networking sessions.",
)
def get_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of sessions to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    ),
    db: Session = Depends(get_db),
) -> HistoryResponse:
    """
    Retrieve paginated networking session history.

    Each session in the response includes:
    - event_description and themes from the linked EventContext
    - all starters generated in the session
    - count of fact-checks linked to the session
    - count of feedback log entries linked to the session
    """
    logger.info("GET /history — limit=%d, offset=%d", limit, offset)

    try:
        # ------------------------------------------------------------------
        # Total count
        # ------------------------------------------------------------------
        total = db.query(func.count(NetworkingSession.session_id)).scalar() or 0

        # ------------------------------------------------------------------
        # Paginated sessions with eager-loaded relationships
        # ------------------------------------------------------------------
        sessions = (
            db.query(NetworkingSession)
            .options(
                joinedload(NetworkingSession.event),
                joinedload(NetworkingSession.starters),
            )
            .order_by(desc(NetworkingSession.session_timestamp))
            .offset(offset)
            .limit(limit)
            .all()
        )

        # ------------------------------------------------------------------
        # Assemble response objects
        # ------------------------------------------------------------------
        session_outs: List[SessionHistoryOut] = []

        for net_session in sessions:
            event_ctx: EventContext = net_session.event

            # Deserialise themes from the EventContext JSON column
            themes: List[str] = []
            if event_ctx and event_ctx.analyzed_themes:
                try:
                    themes = json.loads(event_ctx.analyzed_themes)
                except (json.JSONDecodeError, TypeError):
                    themes = []

            # Starters for this session
            starter_outs: List[StarterHistoryOut] = [
                StarterHistoryOut(
                    starter_id=s.starter_id,
                    text=s.starter_text,
                    created_at=s.created_at,
                )
                for s in net_session.starters
            ]

            # Fact-check count (queried separately to avoid N+1 with lazy)
            fact_check_count = (
                db.query(func.count(WikipediaFactCheck.fact_check_id))
                .filter(
                    WikipediaFactCheck.session_id == net_session.session_id
                )
                .scalar()
                or 0
            )

            # Feedback count from log_entries
            feedback_count = (
                db.query(func.count(LogEntry.log_id))
                .filter(
                    LogEntry.session_id == net_session.session_id,
                    LogEntry.action_type == ACTION_FEEDBACK,
                )
                .scalar()
                or 0
            )

            session_outs.append(
                SessionHistoryOut(
                    session_id=net_session.session_id,
                    event_description=(
                        event_ctx.event_description if event_ctx else ""
                    ),
                    themes=themes,
                    starters=starter_outs,
                    fact_check_count=fact_check_count,
                    feedback_count=feedback_count,
                    created_at=net_session.session_timestamp,
                )
            )

        logger.info(
            "Returning %d/%d sessions (offset=%d).",
            len(session_outs),
            total,
            offset,
        )

        return HistoryResponse(
            total=total,
            limit=limit,
            offset=offset,
            sessions=session_outs,
        )

    except Exception as exc:
        logger.error("History retrieval failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history.",
        ) from exc
