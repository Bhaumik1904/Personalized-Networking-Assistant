"""
backend/config.py
=================
Centralised application configuration loaded from environment variables and
the .env file via pydantic-settings.

All other modules import `get_settings()` (cached singleton) — never read
environment variables directly.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """
    Application settings resolved from:
    1. Environment variables (highest priority)
    2. .env file
    3. Declared defaults (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    app_name: str = Field(default="Personalized Networking Assistant")
    app_version: str = Field(default="1.0.0")
    app_env: str = Field(default="development")
    debug: bool = Field(default=True)

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------
    database_url: str = Field(default="sqlite:///./networking_assistant.db")

    # ------------------------------------------------------------------
    # AI — Google Gemini
    # ------------------------------------------------------------------
    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-2.5-flash")
    use_gemini: bool = Field(default=True)

    # ------------------------------------------------------------------
    # AI — Theme Extraction (DistilBERT zero-shot)
    # ------------------------------------------------------------------
    zero_shot_model: str = Field(
        default="typeform/distilbert-base-uncased-mnli"
    )
    max_themes: int = Field(default=5, ge=1, le=10)

    # ------------------------------------------------------------------
    # AI — Local Fallback Generator (GPT-2 Small)
    # ------------------------------------------------------------------
    local_gen_model: str = Field(default="gpt2")
    local_gen_max_new_tokens: int = Field(default=100, ge=20, le=300)
    local_gen_temperature: float = Field(default=0.85, ge=0.1, le=2.0)

    # ------------------------------------------------------------------
    # Wikipedia API
    # ------------------------------------------------------------------
    wikipedia_language: str = Field(default="en")
    wikipedia_user_agent: str = Field(
        default="PersonalizedNetworkingAssistant/1.0"
    )
    wikipedia_max_summary_sentences: int = Field(default=3, ge=1, le=10)

    # ------------------------------------------------------------------
    # FastAPI Backend
    # ------------------------------------------------------------------
    backend_host: str = Field(default="0.0.0.0")
    backend_port: int = Field(default=8000, ge=1024, le=65535)
    backend_reload: bool = Field(default=True)

    # CORS — stored as comma-separated string, exposed as list
    cors_origins: str = Field(
        default="http://localhost:8501,http://127.0.0.1:8501"
    )

    # ------------------------------------------------------------------
    # Streamlit Frontend
    # ------------------------------------------------------------------
    frontend_port: int = Field(default=8501)
    api_base_url: str = Field(default="http://localhost:8000/api/v1")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is a valid Python logging level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(
                f"Invalid log_level '{v}'. Must be one of {allowed}."
            )
        return upper

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        """Ensure app environment is a recognised value."""
        allowed = {"development", "production", "testing"}
        lower = v.lower()
        if lower not in allowed:
            raise ValueError(
                f"Invalid app_env '{v}'. Must be one of {allowed}."
            )
        return lower

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------
    @property
    def cors_origins_list(self) -> List[str]:
        """Return CORS origins as a Python list, stripped of whitespace."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """True when running in production environment."""
        return self.app_env == "production"

    @property
    def sqlalchemy_echo(self) -> bool:
        """Echo SQL statements only in debug/development mode."""
        return self.debug and not self.is_production


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the application settings singleton.

    The result is cached after the first call, so the .env file is read
    exactly once per process lifetime.
    """
    settings = Settings()
    logger.info(
        "Settings loaded: env=%s, db=%s, gemini=%s",
        settings.app_env,
        settings.database_url,
        settings.use_gemini,
    )
    return settings
