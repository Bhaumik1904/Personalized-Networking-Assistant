"""
backend/tests/test_event_analyzer.py
======================================
Unit tests for EventAnalyzerService.

These tests mock the HuggingFace pipeline to avoid downloading model weights
during CI/CD. The service logic (label selection, error handling, clamping)
is fully exercised with controlled pipeline outputs.
"""

from __future__ import annotations

from typing import List
from unittest.mock import MagicMock, patch

import pytest

from backend.services.event_analyzer import (
    EventAnalyzerService,
    _CANDIDATE_LABELS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def service() -> EventAnalyzerService:
    """Return a fresh EventAnalyzerService instance."""
    return EventAnalyzerService()


def _mock_pipeline_result(labels: List[str], scores: List[float]) -> dict:
    """Build the dict structure that a HuggingFace zero-shot pipeline returns."""
    return {
        "sequence": "test sequence",
        "labels": labels,
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# Tests — extract_themes
# ---------------------------------------------------------------------------

class TestExtractThemes:
    """Tests for EventAnalyzerService.extract_themes()."""

    def test_returns_top_n_themes(self, service: EventAnalyzerService) -> None:
        """Should return at most max_themes labels, sorted by score."""
        mock_result = _mock_pipeline_result(
            labels=["Artificial Intelligence", "Sustainability", "Healthcare", "Finance", "Education"],
            scores=[0.91, 0.85, 0.72, 0.60, 0.55],
        )

        with patch(
            "backend.services.event_analyzer._get_pipeline"
        ) as mock_get:
            mock_clf = MagicMock()
            mock_clf.return_value = mock_result
            mock_get.return_value = mock_clf

            themes = service.extract_themes(
                "AI conference focused on sustainable cities",
                max_themes=3,
            )

        assert len(themes) == 3
        assert themes[0] == "Artificial Intelligence"
        assert themes[1] == "Sustainability"
        assert themes[2] == "Healthcare"

    def test_respects_max_themes_setting(self, service: EventAnalyzerService) -> None:
        """Should respect the max_themes parameter."""
        labels = list(_CANDIDATE_LABELS[:10])
        scores = [0.9 - i * 0.05 for i in range(10)]
        mock_result = _mock_pipeline_result(labels, scores)

        with patch("backend.services.event_analyzer._get_pipeline") as mock_get:
            mock_clf = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_clf

            themes_2 = service.extract_themes("any event", max_themes=2)
            themes_5 = service.extract_themes("any event", max_themes=5)

        assert len(themes_2) == 2
        assert len(themes_5) == 5

    def test_raises_on_empty_description(self, service: EventAnalyzerService) -> None:
        """Should raise ValueError for empty event description."""
        with pytest.raises(ValueError, match="must not be empty"):
            service.extract_themes("")

    def test_raises_on_whitespace_description(self, service: EventAnalyzerService) -> None:
        """Should raise ValueError for whitespace-only description."""
        with pytest.raises(ValueError, match="must not be empty"):
            service.extract_themes("   \n\t  ")

    def test_graceful_degradation_on_pipeline_error(
        self, service: EventAnalyzerService
    ) -> None:
        """Should return fallback themes when the pipeline raises."""
        with patch("backend.services.event_analyzer._get_pipeline") as mock_get:
            mock_clf = MagicMock(side_effect=RuntimeError("Model load failed"))
            mock_get.return_value = mock_clf

            themes = service.extract_themes("AI event")

        # Should return fallback list, not raise
        assert isinstance(themes, list)
        assert len(themes) >= 1

    def test_single_theme_returned(self, service: EventAnalyzerService) -> None:
        """Should work correctly when max_themes=1."""
        mock_result = _mock_pipeline_result(
            labels=["Artificial Intelligence", "Finance"],
            scores=[0.95, 0.40],
        )
        with patch("backend.services.event_analyzer._get_pipeline") as mock_get:
            mock_clf = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_clf

            themes = service.extract_themes("AI event", max_themes=1)

        assert len(themes) == 1
        assert themes[0] == "Artificial Intelligence"


# ---------------------------------------------------------------------------
# Tests — extract_themes_with_scores
# ---------------------------------------------------------------------------

class TestExtractThemesWithScores:
    """Tests for EventAnalyzerService.extract_themes_with_scores()."""

    def test_returns_theme_score_dicts(self, service: EventAnalyzerService) -> None:
        """Should return list of {'theme': str, 'score': float} dicts."""
        mock_result = _mock_pipeline_result(
            labels=["Sustainability", "Innovation"],
            scores=[0.88, 0.72],
        )
        with patch("backend.services.event_analyzer._get_pipeline") as mock_get:
            mock_clf = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_clf

            results = service.extract_themes_with_scores("green tech summit", max_themes=2)

        assert len(results) == 2
        for item in results:
            assert "theme" in item
            assert "score" in item
            assert isinstance(item["score"], float)

    def test_scores_are_rounded(self, service: EventAnalyzerService) -> None:
        """Scores should be rounded to 4 decimal places."""
        mock_result = _mock_pipeline_result(
            labels=["AI"],
            scores=[0.912345678],
        )
        with patch("backend.services.event_analyzer._get_pipeline") as mock_get:
            mock_clf = MagicMock(return_value=mock_result)
            mock_get.return_value = mock_clf

            results = service.extract_themes_with_scores("AI summit", max_themes=1)

        assert results[0]["score"] == 0.9123

    def test_raises_on_empty_description(self, service: EventAnalyzerService) -> None:
        """Should raise ValueError for empty input."""
        with pytest.raises(ValueError):
            service.extract_themes_with_scores("")
