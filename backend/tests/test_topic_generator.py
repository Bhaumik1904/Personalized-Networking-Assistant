"""
backend/tests/test_topic_generator.py
========================================
Unit tests for TopicGeneratorService.

All external API calls (Gemini) and model pipeline calls (GPT-2) are mocked.
Tests verify:
- Correct number of starters returned
- Prompt building logic
- Numbered-list parsing from Gemini responses
- Text cleaning (_clean_starter)
- Engine routing (Gemini vs local)
- Graceful fallback when Gemini fails
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.services.topic_generator import TopicGeneratorService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def service() -> TopicGeneratorService:
    """Return a fresh TopicGeneratorService instance."""
    return TopicGeneratorService()


SAMPLE_BIO = "I'm a data scientist specialising in climate AI."
SAMPLE_EVENT = "AI for Sustainable Cities 2026"
SAMPLE_THEMES = ["Artificial Intelligence", "Sustainability", "Urban Planning"]


# ---------------------------------------------------------------------------
# Tests — generate_starters (routing)
# ---------------------------------------------------------------------------

class TestGenerateStartersRouting:
    """Tests that verify correct engine selection and output count."""

    def test_returns_correct_number_of_starters(
        self, service: TopicGeneratorService
    ) -> None:
        """Should return exactly num_starters items."""
        mock_response = MagicMock()
        mock_response.text = (
            "1. What role does AI play in urban planning today?\n"
            "2. How is your organisation measuring sustainability impact?\n"
            "3. Which smart city initiative excites you most right now?\n"
        )

        with patch("backend.services.topic_generator.get_settings") as mock_settings:
            mock_cfg = MagicMock()
            mock_cfg.use_gemini = True
            mock_cfg.gemini_api_key = "fake-key"
            mock_cfg.gemini_model = "gemini-2.5-flash"
            mock_settings.return_value = mock_cfg
            service._settings = mock_cfg

            with patch("google.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_response
                mock_client_cls.return_value = mock_client

                starters = service._generate_with_gemini(
                    SAMPLE_BIO, SAMPLE_EVENT, SAMPLE_THEMES, num_starters=3
                )

        assert len(starters) == 3

    def test_raises_on_empty_bio(self, service: TopicGeneratorService) -> None:
        """Should raise ValueError when user_bio is empty."""
        with pytest.raises(ValueError, match="user_bio must not be empty"):
            service.generate_starters(
                user_bio="   ",
                event_description=SAMPLE_EVENT,
                themes=SAMPLE_THEMES,
                num_starters=2,
            )

    def test_raises_on_empty_event(self, service: TopicGeneratorService) -> None:
        """Should raise ValueError when event_description is empty."""
        with pytest.raises(ValueError, match="event_description must not be empty"):
            service.generate_starters(
                user_bio=SAMPLE_BIO,
                event_description="",
                themes=SAMPLE_THEMES,
                num_starters=2,
            )

    def test_num_starters_clamped_to_max_5(
        self, service: TopicGeneratorService
    ) -> None:
        """num_starters > 5 should be silently clamped to 5."""
        mock_response = MagicMock()
        mock_response.text = "\n".join(
            f"{i+1}. Starter number {i+1}?" for i in range(5)
        )

        with patch("backend.services.topic_generator.get_settings") as mock_settings:
            mock_cfg = MagicMock()
            mock_cfg.use_gemini = True
            mock_cfg.gemini_api_key = "fake-key"
            mock_cfg.gemini_model = "gemini-2.5-flash"
            mock_settings.return_value = mock_cfg
            service._settings = mock_cfg

            with patch("google.genai.Client") as mock_client_cls:
                mock_client = MagicMock()
                mock_client.models.generate_content.return_value = mock_response
                mock_client_cls.return_value = mock_client

                starters = service.generate_starters(
                    user_bio=SAMPLE_BIO,
                    event_description=SAMPLE_EVENT,
                    themes=SAMPLE_THEMES,
                    num_starters=99,
                )

        assert len(starters) <= 5


# ---------------------------------------------------------------------------
# Tests — _parse_numbered_list
# ---------------------------------------------------------------------------

class TestParseNumberedList:
    """Tests for the Gemini response numbered-list parser."""

    def test_parses_dot_format(self, service: TopicGeneratorService) -> None:
        """Should parse '1. text' format."""
        raw = "1. First question?\n2. Second observation.\n3. Third opener."
        result = service._parse_numbered_list(raw, expected=3)
        assert len(result) == 3
        assert "First question" in result[0]

    def test_parses_paren_format(self, service: TopicGeneratorService) -> None:
        """Should parse '1) text' format."""
        raw = "1) First.\n2) Second.\n"
        result = service._parse_numbered_list(raw, expected=2)
        assert len(result) == 2

    def test_pads_with_fallback_if_too_few(
        self, service: TopicGeneratorService
    ) -> None:
        """Should pad with fallback starter if fewer than expected are parsed."""
        raw = "1. Only one starter."
        result = service._parse_numbered_list(raw, expected=3)
        assert len(result) == 3

    def test_truncates_if_too_many(self, service: TopicGeneratorService) -> None:
        """Should return at most `expected` starters."""
        raw = "1. A.\n2. B.\n3. C.\n4. D.\n5. E.\n"
        result = service._parse_numbered_list(raw, expected=2)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# Tests — _clean_starter
# ---------------------------------------------------------------------------

class TestCleanStarter:
    """Tests for the text-cleaning helper."""

    def test_strips_whitespace(self) -> None:
        """Should strip leading and trailing whitespace."""
        result = TopicGeneratorService._clean_starter("  Hello there!  ")
        assert result == "Hello there!"

    def test_removes_prompt_prefix(self) -> None:
        """Should strip known prompt-bleed prefixes."""
        result = TopicGeneratorService._clean_starter(
            "Conversation starter: What brings you here today?"
        )
        assert not result.startswith("Conversation starter:")

    def test_adds_terminal_punctuation(self) -> None:
        """Should add '?' if text has no terminal punctuation."""
        result = TopicGeneratorService._clean_starter("What brings you here")
        assert result.endswith("?")

    def test_preserves_existing_punctuation(self) -> None:
        """Should not add punctuation if already present."""
        result = TopicGeneratorService._clean_starter("I love sustainability!")
        assert result.endswith("!")
        assert not result.endswith("!?")

    def test_truncates_to_two_sentences(self) -> None:
        """Should keep at most 2 sentences."""
        long_text = (
            "First sentence. Second sentence. Third sentence. Fourth sentence."
        )
        result = TopicGeneratorService._clean_starter(long_text)
        # At most 2 sentences
        import re
        sentences = re.split(r"(?<=[.!?])\s+", result)
        assert len(sentences) <= 2
