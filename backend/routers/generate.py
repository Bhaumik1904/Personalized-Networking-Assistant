"""
backend/routers/generate.py
=============================
FastAPI router for POST /api/v1/generate.

This router contains ONLY input validation, service orchestration, and
response serialisation. All business logic lives in the service layer.

Pipeline:
1. Validate request (Pydantic)
2. Extract themes from event description (EventAnalyzerService)
3. Generate personalised conversation starters (TopicGeneratorService)
4. Persist session, event context, starters, and log entry (HistoryLoggerService)
5. Return structured response (GenerateResponse)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.generate import GenerateRequest, GenerateResponse, StarterOut
from backend.services.event_analyzer import EventAnalyzerService
from backend.services.history_logger import HistoryLoggerService
from backend.services.topic_generator import TopicGeneratorService


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Generation"])

# ---------------------------------------------------------------------------
# Service instances (module-level singletons — stateless, safe to share)
# ---------------------------------------------------------------------------

_event_analyzer = EventAnalyzerService()
_topic_generator = TopicGeneratorService()
_history_logger = HistoryLoggerService()


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate personalised conversation starters",
    description=(
        "Accepts a user bio and event description. Extracts themes using "
        "DistilBERT zero-shot classification, then generates personalised "
        "conversation starters using Google Gemini 2.5 Flash (or GPT-2 Small "
        "as a local fallback). All results are persisted to the database."
    ),
    response_description="Session details and generated conversation starters.",
)
def generate_starters(
    request: GenerateRequest,
    db: Session = Depends(get_db),
) -> GenerateResponse:
    """
    Generate personalised conversation starters for a networking event.

    This endpoint orchestrates the full AI pipeline:
    1. Theme extraction via DistilBERT zero-shot classification.
    2. Starter generation via Gemini 2.5 Flash (or local fallback).
    3. Persistence of all results to the database.
    """
    logger.info(
        "POST /generate — bio_len=%d, event_len=%d, num=%d",
        len(request.user_bio),
        len(request.event_description),
        request.num_starters,
    )

    # ------------------------------------------------------------------
    # Step 1: Extract themes
    # ------------------------------------------------------------------
    try:
        themes = _event_analyzer.extract_themes(
            event_description=request.event_description,
            max_themes=5,
        )
    except Exception as exc:
        logger.error("Theme extraction failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Theme extraction failed. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # Step 2: Generate starters
    # ------------------------------------------------------------------
    try:
        raw_starters = _topic_generator.generate_starters(
            user_bio=request.user_bio,
            event_description=request.event_description,
            themes=themes,
            num_starters=request.num_starters,
        )
    except Exception as exc:
        logger.error("Starter generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Starter generation failed. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # Step 3: Persist to database
    # ------------------------------------------------------------------
    try:
        # 3a. User profile
        user_profile = _history_logger.get_or_create_user(
            db=db,
            user_id=request.user_id,
            bio_text=request.user_bio,
        )

        # 3b. Event context
        event_ctx = _history_logger.create_event_context(
            db=db,
            event_description=request.event_description,
            themes=themes,
        )

        # 3c. Networking session
        net_session = _history_logger.create_session(
            db=db,
            user_id=user_profile.user_id,
            event_id=event_ctx.event_id,
        )

        # 3d. Save generated starters
        saved_starters = _history_logger.save_starters(
            db=db,
            session_id=net_session.session_id,
            starters_data=raw_starters,
        )

        # 3e. Audit log
        _history_logger.log_generate_action(
            db=db,
            session_id=net_session.session_id,
            payload={
                "themes": themes,
                "num_starters": request.num_starters,
                "engine": "gemini" if _topic_generator._settings.use_gemini else "local",
            },
        )

    except Exception as exc:
        logger.error("Database persistence failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save session data. Please try again.",
        ) from exc

    # ------------------------------------------------------------------
    # Step 4: Build and return response
    # ------------------------------------------------------------------
    starter_outs = [
        StarterOut(
            starter_id=db_starter.starter_id,
            text=db_starter.starter_text,
            context_prompt_used=db_starter.context_prompt_used,
        )
        for db_starter in saved_starters
    ]

    logger.info(
        "Generated %d starters for session %s.",
        len(starter_outs),
        net_session.session_id,
    )

    return GenerateResponse(
        session_id=net_session.session_id,
        event_id=event_ctx.event_id,
        user_id=user_profile.user_id,
        themes=themes,
        starters=starter_outs,
        generated_at=datetime.now(timezone.utc),
    )
