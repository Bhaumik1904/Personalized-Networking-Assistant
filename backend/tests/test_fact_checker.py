"""
backend/tests/test_fact_checker.py
=====================================
Unit tests for FactCheckerService.

The Wikipedia client is mocked to avoid live network calls during testing.
Tests verify:
- Successful page lookup with summary and URL
- Not-found handling
- Disambiguation page handling
- Summary sentence truncation
- Empty query validation
- Network error graceful degradation
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.fact_checker import FactCheckResult, FactCheckerService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def service() -> FactCheckerService:
    """Return a fresh FactCheckerService instance."""
    return FactCheckerService()


def _make_mock_page(
    exists: bool = True,
    title: str = "Blockchain",
    summary: str = (
        "Blockchain is a distributed ledger technology. "
        "It records transactions across many computers. "
        "It was first described in 2008."
    ),
    fullurl: str = "https://en.wikipedia.org/wiki/Blockchain",
) -> MagicMock:
    """Build a mock Wikipedia page object."""
    page = MagicMock()
    page.exists.return_value = exists
    page.title = title
    page.summary = summary
    page.fullurl = fullurl
    return page


# ---------------------------------------------------------------------------
# Tests — check() — found
# ---------------------------------------------------------------------------

class TestFactCheckerFound:
    """Tests for successful Wikipedia lookups."""

    def test_returns_found_status(self, service: FactCheckerService) -> None:
        """Should return status='found' when the page exists."""
        mock_page = _make_mock_page(exists=True)

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("Blockchain")

        assert isinstance(result, FactCheckResult)
        assert result.status == "found"
        assert result.is_found is True

    def test_returns_non_empty_summary(self, service: FactCheckerService) -> None:
        """Summary should be a non-empty string when page is found."""
        mock_page = _make_mock_page(exists=True)

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("Blockchain")

        assert result.summary is not None
        assert len(result.summary) > 10

    def test_returns_source_url(self, service: FactCheckerService) -> None:
        """Source URL should be present and start with https."""
        mock_page = _make_mock_page(exists=True)

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("Blockchain")

        assert result.source_url is not None
        assert result.source_url.startswith("https://")

    def test_query_preserved_in_result(self, service: FactCheckerService) -> None:
        """The query field should match the input (stripped)."""
        mock_page = _make_mock_page(exists=True)

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("  Blockchain  ")

        assert result.query == "Blockchain"


# ---------------------------------------------------------------------------
# Tests — check() — not found
# ---------------------------------------------------------------------------

class TestFactCheckerNotFound:
    """Tests for missing Wikipedia pages."""

    def test_returns_not_found_status(self, service: FactCheckerService) -> None:
        """Should return status='not_found' for non-existent pages."""
        mock_page = _make_mock_page(exists=False)

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("xyzzy_nonexistent_topic_12345")

        assert result.status == "not_found"
        assert result.is_found is False
        assert result.summary is None
        assert result.source_url is None

    def test_disambiguation_treated_as_not_found(
        self, service: FactCheckerService
    ) -> None:
        """Disambiguation pages should be treated as not found."""
        mock_page = _make_mock_page(
            exists=True,
            title="Python (disambiguation)",
        )

        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.return_value = mock_page
            mock_client_fn.return_value = mock_wiki

            result = service.check("Python")

        assert result.status == "not_found"


# ---------------------------------------------------------------------------
# Tests — check() — validation
# ---------------------------------------------------------------------------

class TestFactCheckerValidation:
    """Tests for input validation."""

    def test_raises_on_empty_query(self, service: FactCheckerService) -> None:
        """Should raise ValueError for empty query."""
        with pytest.raises(ValueError, match="must not be empty"):
            service.check("")

    def test_raises_on_whitespace_query(self, service: FactCheckerService) -> None:
        """Should raise ValueError for whitespace-only query."""
        with pytest.raises(ValueError, match="must not be empty"):
            service.check("   ")


# ---------------------------------------------------------------------------
# Tests — _extract_summary
# ---------------------------------------------------------------------------

class TestExtractSummary:
    """Tests for the sentence-trimming helper."""

    def test_returns_n_sentences(self, service: FactCheckerService) -> None:
        """Should return at most max_summary_sentences sentences."""
        full = "First. Second. Third. Fourth. Fifth."
        # Default setting is 3 sentences
        result = service._extract_summary(full)
        assert result is not None
        assert "First" in result
        assert "Fourth" not in result

    def test_returns_none_for_empty_summary(
        self, service: FactCheckerService
    ) -> None:
        """Should return None for empty input."""
        assert service._extract_summary("") is None
        assert service._extract_summary("   ") is None

    def test_adds_terminal_period(self, service: FactCheckerService) -> None:
        """Should add a period if the trimmed text lacks terminal punctuation."""
        result = service._extract_summary("A fact about something")
        assert result is not None
        assert result.endswith(".")


# ---------------------------------------------------------------------------
# Tests — network error graceful degradation
# ---------------------------------------------------------------------------

class TestFactCheckerNetworkError:
    """Tests for error handling when Wikipedia is unreachable."""

    def test_returns_not_found_on_network_error(
        self, service: FactCheckerService
    ) -> None:
        """Should return status='not_found' (not raise) on network error."""
        with patch("backend.services.fact_checker._get_wiki_client") as mock_client_fn:
            mock_wiki = MagicMock()
            mock_wiki.page.side_effect = ConnectionError("Network unreachable")
            mock_client_fn.return_value = mock_wiki

            result = service.check("Artificial Intelligence")

        assert result.status == "not_found"
        assert result.summary is None
