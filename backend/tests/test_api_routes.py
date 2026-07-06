"""
backend/tests/test_api_routes.py
===================================
Integration tests for all FastAPI API routes using httpx.AsyncClient and
an in-memory SQLite test database.

All AI service calls (DistilBERT, Gemini) are mocked so tests run fast and
without external dependencies. The database dependency is overridden to
use an isolated in-memory SQLite instance per test session.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app


# ---------------------------------------------------------------------------
# Test database setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def override_get_db() -> Generator:
    """Override the get_db dependency with an in-memory test session."""
    import backend.models  # noqa: F401 — ensure all models are registered
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

def _mock_themes():
    """Patch EventAnalyzerService.extract_themes to return fixed themes."""
    return patch(
        "backend.routers.generate._event_analyzer.extract_themes",
        return_value=["Artificial Intelligence", "Sustainability"],
    )


def _mock_starters():
    """Patch TopicGeneratorService.generate_starters to return fixed starters."""
    return patch(
        "backend.routers.generate._topic_generator.generate_starters",
        return_value=[
            {
                "text": "What AI applications are you most excited about for sustainability?",
                "prompt": "test prompt 1",
            },
            {
                "text": "How is your organisation measuring its environmental impact?",
                "prompt": "test prompt 2",
            },
            {
                "text": "Which sustainable city initiative would you love to see scaled globally?",
                "prompt": "test prompt 3",
            },
        ],
    )


def _mock_wikipedia_found():
    """Patch FactCheckerService.check to return a found result."""
    from backend.services.fact_checker import FactCheckResult
    return patch(
        "backend.routers.fact_check._fact_checker.check",
        return_value=FactCheckResult(
            query="blockchain",
            status="found",
            summary="Blockchain is a distributed ledger technology.",
            source_url="https://en.wikipedia.org/wiki/Blockchain",
        ),
    )


def _mock_wikipedia_not_found():
    """Patch FactCheckerService.check to return a not_found result."""
    from backend.services.fact_checker import FactCheckResult
    return patch(
        "backend.routers.fact_check._fact_checker.check",
        return_value=FactCheckResult(
            query="xyzzy_not_real",
            status="not_found",
            summary=None,
            source_url=None,
        ),
    )


# ---------------------------------------------------------------------------
# Test client fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Return an httpx TestClient for the FastAPI app."""
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health check should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_contains_status_ok(self, client: TestClient) -> None:
        """Health response should include status field."""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["version"] is not None

    def test_health_contains_version(self, client: TestClient) -> None:
        """Health response should include version field."""
        data = client.get("/health").json()
        assert "version" in data


# ---------------------------------------------------------------------------
# Tests — POST /api/v1/generate
# ---------------------------------------------------------------------------

class TestGenerateEndpoint:
    """Tests for POST /api/v1/generate."""

    def test_generate_returns_200(self, client: TestClient) -> None:
        """Valid request should return HTTP 200."""
        with _mock_themes(), _mock_starters():
            response = client.post(
                "/api/v1/generate",
                json={
                    "user_bio": "I am a data scientist focused on climate tech.",
                    "event_description": "AI for Sustainable Cities 2026 conference.",
                    "num_starters": 3,
                },
            )
        assert response.status_code == 200

    def test_generate_returns_starters(self, client: TestClient) -> None:
        """Response should include the correct number of starters."""
        with _mock_themes(), _mock_starters():
            response = client.post(
                "/api/v1/generate",
                json={
                    "user_bio": "I am a data scientist focused on climate tech.",
                    "event_description": "AI for Sustainable Cities 2026.",
                    "num_starters": 3,
                },
            )
        data = response.json()
        assert "starters" in data
        assert len(data["starters"]) == 3

    def test_generate_returns_themes(self, client: TestClient) -> None:
        """Response should include extracted themes."""
        with _mock_themes(), _mock_starters():
            response = client.post(
                "/api/v1/generate",
                json={
                    "user_bio": "I am a data scientist.",
                    "event_description": "AI summit on climate change.",
                    "num_starters": 2,
                },
            )
        data = response.json()
        assert "themes" in data
        assert isinstance(data["themes"], list)

    def test_generate_returns_session_id(self, client: TestClient) -> None:
        """Response should include a session_id UUID."""
        with _mock_themes(), _mock_starters():
            response = client.post(
                "/api/v1/generate",
                json={
                    "user_bio": "Climate researcher interested in AI.",
                    "event_description": "Green Tech Summit 2026.",
                    "num_starters": 2,
                },
            )
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) == 36  # UUID length

    def test_generate_rejects_short_bio(self, client: TestClient) -> None:
        """Bio shorter than 10 chars should return 422."""
        response = client.post(
            "/api/v1/generate",
            json={
                "user_bio": "Hi",
                "event_description": "AI conference on climate change.",
                "num_starters": 2,
            },
        )
        assert response.status_code == 422

    def test_generate_rejects_missing_fields(self, client: TestClient) -> None:
        """Missing required fields should return 422."""
        response = client.post("/api/v1/generate", json={})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — GET /api/v1/fact-check
# ---------------------------------------------------------------------------

class TestFactCheckEndpoint:
    """Tests for GET /api/v1/fact-check."""

    def test_fact_check_found_returns_200(self, client: TestClient) -> None:
        """Found Wikipedia page should return 200."""
        with _mock_wikipedia_found():
            response = client.get("/api/v1/fact-check?query=blockchain")
        assert response.status_code == 200

    def test_fact_check_found_has_summary(self, client: TestClient) -> None:
        """Found result should include a summary."""
        with _mock_wikipedia_found():
            data = client.get("/api/v1/fact-check?query=blockchain").json()
        assert data["status"] == "found"
        assert data["summary"] is not None

    def test_fact_check_not_found_returns_200(self, client: TestClient) -> None:
        """Not-found Wikipedia result should still return 200 (not 404)."""
        with _mock_wikipedia_not_found():
            response = client.get("/api/v1/fact-check?query=xyzzy_not_real")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_found"
        assert data["summary"] is None

    def test_fact_check_requires_query(self, client: TestClient) -> None:
        """Missing query param should return 422."""
        response = client.get("/api/v1/fact-check")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — GET /api/v1/history
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:
    """Tests for GET /api/v1/history."""

    def test_history_returns_200(self, client: TestClient) -> None:
        """History endpoint should return 200."""
        response = client.get("/api/v1/history")
        assert response.status_code == 200

    def test_history_response_structure(self, client: TestClient) -> None:
        """Response should have total, limit, offset, sessions fields."""
        data = client.get("/api/v1/history").json()
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_history_respects_limit(self, client: TestClient) -> None:
        """Limit parameter should be reflected in response."""
        data = client.get("/api/v1/history?limit=5").json()
        assert data["limit"] == 5

    def test_history_rejects_invalid_limit(self, client: TestClient) -> None:
        """limit=0 should return 422."""
        response = client.get("/api/v1/history?limit=0")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests — POST /api/v1/feedback
# ---------------------------------------------------------------------------

class TestFeedbackEndpoint:
    """Tests for the feedback endpoints."""

    def _create_session_and_starter(self, client: TestClient) -> tuple[str, str]:
        """Helper: generate a session and return (session_id, starter_id)."""
        with _mock_themes(), _mock_starters():
            response = client.post(
                "/api/v1/generate",
                json={
                    "user_bio": "A professional interested in AI and ethics.",
                    "event_description": "Ethics in AI conference 2026.",
                    "num_starters": 2,
                },
            )
        data = response.json()
        session_id = data["session_id"]
        starter_id = data["starters"][0]["starter_id"]
        return session_id, starter_id

    def test_submit_thumbs_up_returns_201(self, client: TestClient) -> None:
        """Valid thumbs-up should return 201."""
        session_id, starter_id = self._create_session_and_starter(client)

        response = client.post(
            "/api/v1/feedback",
            json={
                "starter_id": starter_id,
                "session_id": session_id,
                "rating": "up",
            },
        )
        assert response.status_code == 201

    def test_submit_thumbs_down_returns_201(self, client: TestClient) -> None:
        """Valid thumbs-down should return 201."""
        session_id, starter_id = self._create_session_and_starter(client)

        response = client.post(
            "/api/v1/feedback",
            json={
                "starter_id": starter_id,
                "session_id": session_id,
                "rating": "down",
            },
        )
        assert response.status_code == 201

    def test_feedback_rejects_invalid_rating(self, client: TestClient) -> None:
        """Invalid rating should return 422."""
        response = client.post(
            "/api/v1/feedback",
            json={
                "starter_id": "some-uuid",
                "session_id": "some-session",
                "rating": "neutral",  # Invalid
            },
        )
        assert response.status_code == 422

    def test_feedback_history_returns_200(self, client: TestClient) -> None:
        """Feedback history endpoint should return 200."""
        response = client.get("/api/v1/feedback-history")
        assert response.status_code == 200

    def test_feedback_history_response_structure(self, client: TestClient) -> None:
        """Feedback history should have total and feedback fields."""
        data = client.get("/api/v1/feedback-history").json()
        assert "total" in data
        assert "feedback" in data
        assert isinstance(data["feedback"], list)
