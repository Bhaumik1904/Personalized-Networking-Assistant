"""
backend/main.py
================
FastAPI application factory.

Responsibilities:
- Create the FastAPI app instance with full metadata for OpenAPI docs.
- Configure CORS middleware (allow Streamlit frontend origin).
- Register all routers under /api/v1 prefix.
- Set up structured logging.
- Use the lifespan context manager to:
  - Warm up transformer models on startup (avoid first-request cold-start).
  - Create database tables if they do not exist.
- Expose a /health endpoint for deployment health checks.
- Expose the auto-generated /docs and /redoc endpoints (FastAPI built-in).
"""

from __future__ import annotations

import logging
import logging.config
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.database import create_all_tables, verify_database_connection
from backend.routers import (
    fact_check_router,
    feedback_router,
    generate_router,
    history_router,
)


settings = get_settings()

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """Set up structured logging for the application."""
    log_level = getattr(logging, settings.log_level, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


_configure_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup and shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Startup (before yield):
    1. Verify database connectivity.
    2. Create all database tables (idempotent).
    3. Warm up the DistilBERT theme-extraction pipeline so that the first
       API request does not incur a 3–5 second model-load delay.
    4. Warm up the local GPT-2 pipeline if Gemini is disabled.

    Shutdown (after yield):
    - Logs a clean shutdown message. SQLAlchemy connection pools are
      disposed automatically by Python's garbage collector.
    """
    logger.info("=" * 60)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    logger.info("Environment: %s | Debug: %s", settings.app_env, settings.debug)
    logger.info("=" * 60)

    # 1. Database
    if not verify_database_connection():
        logger.critical("Cannot connect to database. Aborting startup.")
        raise RuntimeError("Database connection failed at startup.")
    create_all_tables()

    # 2. Warm up AI models (non-blocking — errors are logged but don't abort)
    logger.info("Warming up AI models...")
    try:
        from backend.services.event_analyzer import _get_pipeline as _get_clf
        _get_clf()
        logger.info("DistilBERT zero-shot classifier warmed up.")
    except Exception as exc:
        logger.warning("Could not warm up classifier: %s", exc)

    if not settings.use_gemini:
        try:
            from backend.services.topic_generator import _get_local_pipeline
            _get_local_pipeline()
            logger.info("GPT-2 local generator warmed up.")
        except Exception as exc:
            logger.warning("Could not warm up local generator: %s", exc)
    else:
        logger.info(
            "Using Gemini %s for generation — no local warm-up needed.",
            settings.gemini_model,
        )

    logger.info("Startup complete. API is ready.")

    yield  # ← Application runs here

    logger.info("Shutting down %s.", settings.app_name)


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered networking assistant that generates personalised "
        "conversation starters and provides Wikipedia fact-checking. "
        "Built with FastAPI, DistilBERT, Google Gemini, and SQLite."
    ),
    contact={
        "name": "SkillWallet — Google Cloud Generative AI Module",
        "url": "https://myskillwallet.ai",
    },
    license_info={
        "name": "MIT",
    },
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

API_PREFIX = "/api/v1"

app.include_router(generate_router, prefix=API_PREFIX)
app.include_router(fact_check_router, prefix=API_PREFIX)
app.include_router(history_router, prefix=API_PREFIX)
app.include_router(feedback_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="API health check",
    description="Returns the application status and version. Used by load balancers and deployment tools.",
    response_description="Health status and version information.",
)
def health_check() -> JSONResponse:
    """
    Return application health status.

    Always returns HTTP 200 with status='ok' if the application is running.
    If the application fails to start, this endpoint will not be available.
    """
    db_ok = verify_database_connection()
    return JSONResponse(
        content={
            "status": "ok" if db_ok else "degraded",
            "version": settings.app_version,
            "app_name": settings.app_name,
            "environment": settings.app_env,
            "database": "connected" if db_ok else "disconnected",
            "generation_engine": "gemini" if settings.use_gemini else "local_gpt2",
        },
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Root redirect
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def root() -> JSONResponse:
    """Redirect root requests to the API documentation."""
    return JSONResponse(
        content={
            "message": f"Welcome to {settings.app_name} API",
            "docs": "/docs",
            "health": "/health",
            "version": settings.app_version,
        }
    )


# ---------------------------------------------------------------------------
# Entry point (for direct execution: python -m backend.main)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload,
        log_level=settings.log_level.lower(),
    )
