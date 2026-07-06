"""
backend/services/fact_checker.py
===================================
FactCheckerService — Wikipedia fact-checking via the wikipedia-api library.

Responsibilities:
- Query the Wikipedia API for a user-supplied topic string.
- Extract a trimmed summary (configurable number of sentences).
- Return structured result data for persistence and API response.
- Handle gracefully: disambiguation pages, missing pages, network errors.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

import wikipediaapi

from backend.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Result dataclass (decoupled from any ORM or Pydantic model)
# ---------------------------------------------------------------------------

@dataclass
class FactCheckResult:
    """
    Plain dataclass returned by FactCheckerService.check().

    Attributes
    ----------
    query : str
        The original search string.
    status : str
        "found" | "not_found"
    summary : str | None
        Trimmed excerpt from the Wikipedia article.
    source_url : str | None
        Full URL of the matched Wikipedia article.
    """

    query: str
    status: str
    summary: Optional[str]
    source_url: Optional[str]

    @property
    def is_found(self) -> bool:
        """True when the Wikipedia lookup returned a matching article."""
        return self.status == "found"


# ---------------------------------------------------------------------------
# Wikipedia client singleton
# ---------------------------------------------------------------------------

_wiki_client: Optional[wikipediaapi.Wikipedia] = None


def _get_wiki_client() -> wikipediaapi.Wikipedia:
    """
    Return the singleton Wikipedia client instance.

    The client is language-aware and uses a descriptive User-Agent string
    as required by the Wikimedia API usage policy.
    """
    global _wiki_client
    if _wiki_client is None:
        _wiki_client = wikipediaapi.Wikipedia(
            language=settings.wikipedia_language,
            user_agent=settings.wikipedia_user_agent,
        )
        logger.info(
            "Wikipedia client initialised (lang=%s).",
            settings.wikipedia_language,
        )
    return _wiki_client


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class FactCheckerService:
    """
    Performs Wikipedia fact-check lookups.

    Methods
    -------
    check(query) -> FactCheckResult
        Look up `query` on Wikipedia and return a structured result.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def check(self, query: str) -> FactCheckResult:
        """
        Look up a topic on Wikipedia and return a structured result.

        Parameters
        ----------
        query : str
            The search string to look up. May be a topic, person, concept,
            or event name.

        Returns
        -------
        FactCheckResult
            Contains status, summary, and source URL.
            If the page is not found, status is "not_found" and summary/URL
            are None.

        Notes
        -----
        - The wikipedia-api library performs an exact title lookup.
          If the exact title is not found the page.exists() check fails.
        - This is intentional: we want precise lookups, not search results.
          The user should refine their query if needed.
        - Disambiguation pages (those with "(disambiguation)" in the title)
          are treated as not-found since they do not contain useful summaries.
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty.")

        clean_query = query.strip()
        logger.info("Performing Wikipedia fact-check for: %r", clean_query)

        try:
            wiki = _get_wiki_client()
            page = wiki.page(clean_query)

            if not page.exists():
                logger.info("Wikipedia: page not found for %r", clean_query)
                return FactCheckResult(
                    query=clean_query,
                    status="not_found",
                    summary=None,
                    source_url=None,
                )

            # Check for disambiguation page
            if "(disambiguation)" in page.title.lower():
                logger.info(
                    "Wikipedia: disambiguation page for %r — treating as not found.",
                    clean_query,
                )
                return FactCheckResult(
                    query=clean_query,
                    status="not_found",
                    summary=None,
                    source_url=None,
                )

            summary = self._extract_summary(page.summary)
            source_url = page.fullurl

            logger.info(
                "Wikipedia: found page '%s' — summary length %d chars.",
                page.title,
                len(summary) if summary else 0,
            )

            return FactCheckResult(
                query=clean_query,
                status="found",
                summary=summary,
                source_url=source_url,
            )

        except Exception as exc:
            logger.error(
                "Wikipedia lookup failed for %r: %s", clean_query, exc,
                exc_info=True,
            )
            # Return a graceful not-found rather than crashing the API
            return FactCheckResult(
                query=clean_query,
                status="not_found",
                summary=None,
                source_url=None,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_summary(self, full_summary: str) -> Optional[str]:
        """
        Extract the first N sentences from the Wikipedia page summary.

        Parameters
        ----------
        full_summary : str
            The full summary text returned by the wikipedia-api library.

        Returns
        -------
        str | None
            Trimmed summary with at most `wikipedia_max_summary_sentences`
            sentences, or None if the summary is empty.
        """
        if not full_summary or not full_summary.strip():
            return None

        max_sentences = self._settings.wikipedia_max_summary_sentences

        # Split on sentence boundaries (period, exclamation, question mark)
        # followed by whitespace and an uppercase letter.
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", full_summary.strip())

        trimmed = " ".join(sentences[:max_sentences]).strip()

        # Ensure terminal punctuation
        if trimmed and trimmed[-1] not in ".!?":
            trimmed += "."

        return trimmed if trimmed else None
