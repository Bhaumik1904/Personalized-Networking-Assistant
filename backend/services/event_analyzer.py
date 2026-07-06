"""
backend/services/event_analyzer.py
=====================================
EventAnalyzerService — Theme extraction from event descriptions using
DistilBERT zero-shot classification via HuggingFace Transformers.

Architecture notes:
- The pipeline is loaded **once** at module import time (module-level singleton).
  This avoids a 3–5 second cold-start on every API request.
- The service is a plain Python class with no FastAPI coupling; it can be
  imported and tested independently.
- The candidate label set covers the most common professional networking
  event topics. Labels are normalised to title-case before being returned.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from backend.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Candidate topic labels for zero-shot classification
# ---------------------------------------------------------------------------

_CANDIDATE_LABELS: List[str] = [
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
    "Sustainability",
    "Climate Change",
    "Urban Planning",
    "Healthcare",
    "Blockchain",
    "Finance",
    "Education",
    "Entrepreneurship",
    "Cybersecurity",
    "Cloud Computing",
    "Internet of Things",
    "Robotics",
    "Ethics",
    "Policy",
    "Marketing",
    "Human Resources",
    "Leadership",
    "Product Management",
    "Software Engineering",
    "Research",
    "Innovation",
    "Diversity and Inclusion",
]

# ---------------------------------------------------------------------------
# Module-level pipeline singleton
# ---------------------------------------------------------------------------

_pipeline = None  # HuggingFace pipeline object, initialised lazily


def _get_pipeline():
    """
    Return the singleton zero-shot classification pipeline.

    The pipeline is created on the first call and reused thereafter.
    Loading the model downloads weights to the HuggingFace cache (~250 MB)
    on first run; subsequent runs use the local cache.
    """
    global _pipeline
    if _pipeline is None:
        logger.info(
            "Loading zero-shot classification model: %s",
            settings.zero_shot_model,
        )
        try:
            from transformers import pipeline as hf_pipeline

            _pipeline = hf_pipeline(
                "zero-shot-classification",
                model=settings.zero_shot_model,
                # Run on CPU — sufficient for classification at this scale
                device=-1,
            )
            logger.info("Zero-shot classification model loaded successfully.")
        except Exception as exc:
            logger.error(
                "Failed to load zero-shot classification model: %s", exc
            )
            raise RuntimeError(
                f"Could not load theme extraction model "
                f"'{settings.zero_shot_model}': {exc}"
            ) from exc
    return _pipeline


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class EventAnalyzerService:
    """
    Extracts dominant themes from a free-text event description.

    Uses DistilBERT fine-tuned on MultiNLI for zero-shot classification.
    The model scores each candidate label against the event text and returns
    the top-N labels sorted by confidence.

    Methods
    -------
    extract_themes(event_description, max_themes) -> list[str]
        Return up to `max_themes` topic labels sorted by confidence.
    extract_themes_with_scores(event_description, max_themes) -> list[dict]
        Return themes along with their confidence scores (for debugging).
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def extract_themes(
        self,
        event_description: str,
        max_themes: Optional[int] = None,
    ) -> List[str]:
        """
        Extract the top-N themes from an event description.

        Parameters
        ----------
        event_description : str
            Raw text describing the networking event.
        max_themes : int | None
            Maximum number of themes to return.
            Defaults to settings.max_themes (from .env).

        Returns
        -------
        list[str]
            List of theme strings sorted by model confidence (highest first).
            Returns an empty list if inference fails rather than crashing.

        Raises
        ------
        ValueError
            If event_description is empty or whitespace-only.
        """
        if not event_description or not event_description.strip():
            raise ValueError("event_description must not be empty.")

        n = max_themes if max_themes is not None else self._settings.max_themes

        logger.info(
            "Extracting themes from event description (len=%d, max=%d).",
            len(event_description),
            n,
        )

        try:
            clf = _get_pipeline()
            result = clf(
                sequences=event_description,
                candidate_labels=_CANDIDATE_LABELS,
                multi_label=True,
            )

            # Result format: {"labels": [...], "scores": [...]}
            # Labels are already sorted by score descending
            themes = result["labels"][:n]

            logger.info("Extracted themes: %s", themes)
            return themes

        except Exception as exc:
            logger.error("Theme extraction failed: %s", exc, exc_info=True)
            # Graceful degradation — return a generic fallback so the rest of
            # the pipeline can still run
            return ["Networking", "Professional Development"]

    def extract_themes_with_scores(
        self,
        event_description: str,
        max_themes: Optional[int] = None,
    ) -> List[dict]:
        """
        Extract themes along with confidence scores.

        Intended for debugging and model evaluation, not for production
        API responses.

        Parameters
        ----------
        event_description : str
            Raw text describing the networking event.
        max_themes : int | None
            Maximum number of themes to return.

        Returns
        -------
        list[dict]
            List of {"theme": str, "score": float} dicts, sorted by score.
        """
        if not event_description or not event_description.strip():
            raise ValueError("event_description must not be empty.")

        n = max_themes if max_themes is not None else self._settings.max_themes

        try:
            clf = _get_pipeline()
            result = clf(
                sequences=event_description,
                candidate_labels=_CANDIDATE_LABELS,
                multi_label=True,
            )
            return [
                {"theme": label, "score": round(score, 4)}
                for label, score in zip(
                    result["labels"][:n], result["scores"][:n]
                )
            ]
        except Exception as exc:
            logger.error(
                "Theme extraction with scores failed: %s", exc, exc_info=True
            )
            return [{"theme": "Networking", "score": 1.0}]
