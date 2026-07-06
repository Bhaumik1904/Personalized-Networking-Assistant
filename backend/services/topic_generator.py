"""
backend/services/topic_generator.py
======================================
TopicGeneratorService — Generates personalised conversation starters.

Primary engine: Google Gemini 2.5 Flash (when USE_GEMINI=true in .env).
Fallback engine: Local GPT-2 Small via HuggingFace Transformers.

Architecture:
- The service is modular: the private methods `_generate_with_gemini` and
  `_generate_with_local_model` are fully interchangeable.
- Swapping in a new model (e.g., Claude, GPT-4) requires only adding a new
  private method and updating `_route_to_engine`.
- Both engines share the same prompt-building logic so outputs are consistent.
- Uses the google-genai SDK (google.genai), the successor to google-generativeai.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from backend.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Local model singleton (GPT-2 fallback)
# ---------------------------------------------------------------------------

_local_pipeline = None


def _get_local_pipeline():
    """
    Return the singleton GPT-2 text-generation pipeline (lazy init).
    """
    global _local_pipeline
    if _local_pipeline is None:
        logger.info(
            "Loading local generation model: %s", settings.local_gen_model
        )
        try:
            from transformers import pipeline as hf_pipeline

            _local_pipeline = hf_pipeline(
                "text-generation",
                model=settings.local_gen_model,
                device=-1,
            )
            logger.info("Local generation model loaded.")
        except Exception as exc:
            logger.error("Failed to load local generation model: %s", exc)
            raise RuntimeError(
                f"Could not load local model '{settings.local_gen_model}': {exc}"
            ) from exc
    return _local_pipeline


# ---------------------------------------------------------------------------
# Prompt building (shared between Gemini and local)
# ---------------------------------------------------------------------------

def _build_prompt(
    user_bio: str,
    event_description: str,
    themes: List[str],
    num_starters: int,
    index: int = 0,
) -> str:
    """
    Build the full generation prompt for a single starter.

    Parameters
    ----------
    user_bio : str
        The user's professional biography.
    event_description : str
        Description of the networking event.
    themes : list[str]
        Dominant topics extracted from the event description.
    num_starters : int
        Total number of starters being requested (for context in the prompt).
    index : int
        0-based index of the current starter (0, 1, 2…) — used to ask
        for stylistic variation across starters.

    Returns
    -------
    str
        A formatted prompt string ready to send to the generation model.
    """
    theme_str = ", ".join(themes) if themes else "professional networking"
    styles = [
        "as an open-ended question that invites elaboration",
        "as a concise observation that shows insider knowledge",
        "as a bridge connecting the event topic to the user's background",
    ]
    style_hint = styles[index % len(styles)]

    prompt = (
        "You are a professional networking coach helping someone craft "
        "memorable conversation openers for a networking event.\n\n"
        f"User background: {user_bio.strip()}\n\n"
        f"Event: {event_description.strip()}\n\n"
        f"Key themes: {theme_str}\n\n"
        f"Write exactly one conversation starter (1–2 sentences) framed "
        f"{style_hint}. The starter should be natural, specific to the event, "
        "and feel like something a real person would say — not a generic "
        "icebreaker. Do not include any preamble, numbering, or explanation. "
        "Output only the conversation starter itself.\n\n"
        "Conversation starter:"
    )
    return prompt


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class TopicGeneratorService:
    """
    Generates personalised conversation starters for networking events.

    Public interface
    ----------------
    generate_starters(user_bio, event_description, themes, num_starters)
        -> list[dict]  — list of {"text": str, "prompt": str}

    The service routes generation through Gemini (if configured) or
    falls back to the local GPT-2 model, ensuring the API always
    returns usable starters even without an internet connection.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    # ------------------------------------------------------------------
    # Public method
    # ------------------------------------------------------------------

    def generate_starters(
        self,
        user_bio: str,
        event_description: str,
        themes: List[str],
        num_starters: int = 3,
    ) -> List[dict]:
        """
        Generate `num_starters` personalised conversation starters.

        Parameters
        ----------
        user_bio : str
            The user's professional bio.
        event_description : str
            Description of the networking event.
        themes : list[str]
            Themes extracted by EventAnalyzerService.
        num_starters : int
            Number of starters to generate (1–5).

        Returns
        -------
        list[dict]
            List of {"text": str, "prompt": str} dicts.
            Each dict contains the generated text and the prompt used.
        """
        if not user_bio.strip():
            raise ValueError("user_bio must not be empty.")
        if not event_description.strip():
            raise ValueError("event_description must not be empty.")
        num_starters = max(1, min(num_starters, 5))

        logger.info(
            "Generating %d starter(s) | engine=%s",
            num_starters,
            "gemini" if self._settings.use_gemini else "local",
        )

        if self._settings.use_gemini and self._settings.gemini_api_key:
            return self._generate_with_gemini(
                user_bio, event_description, themes, num_starters
            )
        else:
            logger.info(
                "USE_GEMINI is false or key absent — using local GPT-2 fallback."
            )
            return self._generate_with_local_model(
                user_bio, event_description, themes, num_starters
            )

    # ------------------------------------------------------------------
    # Gemini engine
    # ------------------------------------------------------------------

    def _generate_with_gemini(
        self,
        user_bio: str,
        event_description: str,
        themes: List[str],
        num_starters: int,
    ) -> List[dict]:
        """
        Generate starters using Google Gemini 2.5 Flash via the google-genai SDK.

        Sends one prompt requesting all starters at once in a numbered list,
        then parses and cleans the response.

        Uses the google.genai Client API (successor to google-generativeai).
        """
        try:
            from google import genai
            from google.genai import types as genai_types

            client = genai.Client(api_key=self._settings.gemini_api_key)

            theme_str = ", ".join(themes) if themes else "professional networking"

            # Single prompt requesting all starters together — more efficient
            # and produces better stylistic variety than N separate calls.
            prompt = (
                "You are a professional networking coach helping someone craft "
                "memorable conversation openers.\n\n"
                f"User background: {user_bio.strip()}\n\n"
                f"Event: {event_description.strip()}\n\n"
                f"Key themes: {theme_str}\n\n"
                f"Generate exactly {num_starters} distinct conversation starters. "
                "Each should be 1–2 sentences, natural, specific to the event, "
                "and feel like something a real professional would say. "
                "Vary the style: mix open-ended questions, observations, and "
                "personal connection statements. "
                f"Format your response as a numbered list:\n"
                "1. [first starter]\n"
                "2. [second starter]\n"
                f"{'3. [third starter]' if num_starters >= 3 else ''}\n\n"
                "Output ONLY the numbered list. No preamble, no explanations."
            )

            logger.debug("Gemini prompt length: %d chars", len(prompt))

            response = client.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    temperature=0.85,
                    max_output_tokens=512,
                    top_p=0.95,
                ),
            )

            raw_text = response.text.strip()
            logger.debug("Gemini raw response: %s", raw_text[:200])

            starters = self._parse_numbered_list(raw_text, num_starters)

            # Attach per-starter prompts for audit trail
            return [
                {"text": text, "prompt": prompt}
                for text in starters
            ]

        except Exception as exc:
            logger.error("Gemini generation failed: %s", exc, exc_info=True)
            logger.warning("Falling back to local GPT-2 model.")
            return self._generate_with_local_model(
                user_bio, event_description, themes, num_starters
            )

    # ------------------------------------------------------------------
    # Local GPT-2 engine (fallback)
    # ------------------------------------------------------------------

    def _generate_with_local_model(
        self,
        user_bio: str,
        event_description: str,
        themes: List[str],
        num_starters: int,
    ) -> List[dict]:
        """
        Generate starters using a local GPT-2 Small pipeline.

        Runs N separate inference calls (one per starter) with different
        prompts to encourage stylistic variety. Each call is capped at
        `local_gen_max_new_tokens` tokens.
        """
        results: List[dict] = []
        pipeline = _get_local_pipeline()

        for i in range(num_starters):
            prompt = _build_prompt(
                user_bio=user_bio,
                event_description=event_description,
                themes=themes,
                num_starters=num_starters,
                index=i,
            )
            try:
                output = pipeline(
                    prompt,
                    max_new_tokens=self._settings.local_gen_max_new_tokens,
                    do_sample=True,
                    temperature=self._settings.local_gen_temperature + (i * 0.05),
                    pad_token_id=50256,  # GPT-2 EOS token as pad
                    truncation=True,
                )
                generated = output[0]["generated_text"]
                # Strip the prompt prefix from the output
                starter_text = generated[len(prompt):].strip()
                starter_text = self._clean_starter(starter_text)

                results.append({"text": starter_text, "prompt": prompt})

            except Exception as exc:
                logger.error(
                    "Local generation failed for starter %d: %s", i, exc
                )
                results.append(
                    {
                        "text": (
                            "What's one takeaway you're hoping to get from "
                            "this event?"
                        ),
                        "prompt": prompt,
                    }
                )

        return results

    # ------------------------------------------------------------------
    # Text-cleaning helpers
    # ------------------------------------------------------------------

    def _parse_numbered_list(self, raw: str, expected: int) -> List[str]:
        """
        Parse a numbered list from Gemini's response into a Python list.

        Handles formats like "1. text", "1) text", "1: text".
        Returns at most `expected` items; pads with a fallback if too few.
        """
        lines = raw.split("\n")
        starters: List[str] = []
        pattern = re.compile(r"^\s*\d+[\.\)\:]\s*(.+)$")

        for line in lines:
            match = pattern.match(line)
            if match:
                text = self._clean_starter(match.group(1))
                if text:
                    starters.append(text)
            if len(starters) >= expected:
                break

        # Pad with fallback if Gemini returned fewer than expected
        fallback = (
            "What aspect of this event are you most looking forward to?"
        )
        while len(starters) < expected:
            starters.append(fallback)

        return starters[:expected]

    @staticmethod
    def _clean_starter(text: str) -> str:
        """
        Clean a generated starter text.

        - Strips leading/trailing whitespace
        - Removes common prompt-bleed prefixes
        - Truncates at the first sentence boundary (if very long)
        - Ensures the text ends with proper punctuation
        """
        # Remove prompt-bleed artifacts
        text = text.strip()
        for prefix in [
            "Conversation starter:",
            "Starter:",
            "Question:",
            "Opening:",
        ]:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        # Truncate to the first two sentences to keep starters concise
        sentences = re.split(r"(?<=[.!?])\s+", text)
        text = " ".join(sentences[:2]).strip()

        # Ensure terminal punctuation
        if text and text[-1] not in ".!?":
            text += "?"

        return text
