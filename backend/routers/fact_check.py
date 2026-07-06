"""
backend/routers/fact_check.py
===============================
FastAPI router for GET /api/v1/fact-check.

Accepts a query string and an optional session_id, performs a Wikipedia
lookup via FactCheckerService, persists the result, and returns a structured
response including status, summary, and source URL.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.fact_check import FactCheckResponse
from backend.services.fact_checker import FactCheckerService
from backend.services.history_logger import HistoryLoggerService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Fact Check"])

# ---------------------------------------------------------------------------
# Service instances
# ---------------------------------------------------------------------------

_fact_checker = FactCheckerService()
_history_logger = HistoryLoggerService()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get(
    "/fact-check",
    response_model=FactCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Fact-check a topic via Wikipedia",
    description=(
        "Looks up the supplied query string on Wikipedia using the "
        "wikipedia-api library. Returns a trimmed summary (up to 3 sentences) "
        "and the source URL if a matching article is found. The result is "
        "persisted to the database. Optionally links the lookup to an "
        "existing networking session via `session_id`."
    ),
    response_description="Fact-check result with status, summary, and source URL.",
)
def fact_check(
    query: str = Query(
        ...,
        min_length=2,
        max_length=300,
        description="Topic or concept to look up on Wikipedia.",
        examples=["blockchain in healthcare"],
    ),
    session_id: Optional[str] = Query(
        default=None,
        description=(
            "Optional UUID of an existing NetworkingSession to link this "
            "fact-check to."
        ),
    ),
    db: Session = Depends(get_db),
) -> FactCheckResponse:
    """
    Look up a topic on Wikipedia and persist the result.

    Returns status='found' with summary and URL if a matching Wikipedia
    article exists, or status='not_found' with null fields otherwise.
    """
    logger.info("GET /fact-check — query=%r, session_id=%s", query, session_id)

    # ------------------------------------------------------------------
    # Step 1: Wikipedia lookup
    # ------------------------------------------------------------------
    try:
        result = _fact_checker.check(query=query)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Fact-check failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Wikipedia lookup failed. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # Step 2: Persist result
    # ------------------------------------------------------------------
    try:
        fact_check_record = _history_logger.save_fact_check(
            db=db,
            result=result,
            session_id=session_id,
        )

        _history_logger.log_fact_check_action(
            db=db,
            session_id=session_id,
            payload={
                "query": query,
                "status": result.status,
                "fact_check_id": fact_check_record.fact_check_id,
            },
        )

    except Exception as exc:
        logger.error("Failed to persist fact-check result: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save fact-check result.",
        ) from exc

    # ------------------------------------------------------------------
    # Step 3: Return response
    # ------------------------------------------------------------------
    logger.info(
        "Fact-check complete: fact_check_id=%s, status=%s",
        fact_check_record.fact_check_id,
        result.status,
    )

    return FactCheckResponse(
        fact_check_id=fact_check_record.fact_check_id,
        session_id=session_id,
        query=query,
        summary=result.summary,
        source_url=result.source_url,
        status=result.status,
        verified_at=datetime.now(timezone.utc),
    )
