"""
backend/routers/feedback.py
=============================
FastAPI router for:
  POST /api/v1/feedback           — submit thumbs-up/down on a starter
  GET  /api/v1/feedback-history   — retrieve all feedback entries
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.feedback import (
    FeedbackHistoryResponse,
    FeedbackRequest,
    FeedbackResponse,
)
from backend.services.feedback_logger import FeedbackLoggerService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Feedback"])

# ---------------------------------------------------------------------------
# Service instance
# ---------------------------------------------------------------------------

_feedback_logger = FeedbackLoggerService()


# ---------------------------------------------------------------------------
# POST /feedback — submit feedback
# ---------------------------------------------------------------------------

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback on a conversation starter",
    description=(
        "Records a thumbs-up or thumbs-down rating for a specific "
        "conversation starter. The feedback is stored as a log entry linked "
        "to the original networking session."
    ),
    response_description="Confirmation with the log entry UUID.",
)
def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """
    Record thumbs-up or thumbs-down feedback for a generated starter.
    """
    logger.info(
        "POST /feedback — starter_id=%s, session_id=%s, rating=%s",
        request.starter_id,
        request.session_id,
        request.rating,
    )

    try:
        log_entry = _feedback_logger.record_feedback(
            db=db,
            starter_id=request.starter_id,
            session_id=request.session_id,
            rating=request.rating,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Failed to record feedback: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record feedback. Please try again.",
        ) from exc

    logger.info("Feedback recorded: log_id=%s", log_entry.log_id)

    return FeedbackResponse(
        log_id=log_entry.log_id,
        message=f"Feedback '{request.rating}' recorded successfully.",
    )


# ---------------------------------------------------------------------------
# GET /feedback-history — retrieve feedback entries
# ---------------------------------------------------------------------------

@router.get(
    "/feedback-history",
    response_model=FeedbackHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve feedback history",
    description=(
        "Returns all feedback entries (thumbs-up/down) ordered by most "
        "recent first. Each entry includes the starter text (denormalised "
        "from the stored log payload), the session ID, and the rating."
    ),
    response_description="Total count and list of feedback entries.",
)
def get_feedback_history(
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of feedback entries to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    ),
    db: Session = Depends(get_db),
) -> FeedbackHistoryResponse:
    """
    Retrieve paginated feedback history for all networking sessions.
    """
    logger.info("GET /feedback-history — limit=%d, offset=%d", limit, offset)

    try:
        total, entries = _feedback_logger.get_feedback_history(
            db=db,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error("Feedback history retrieval failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve feedback history.",
        ) from exc

    logger.info(
        "Returning %d/%d feedback entries (offset=%d).",
        len(entries),
        total,
        offset,
    )

    return FeedbackHistoryResponse(
        total=total,
        feedback=entries,
    )
