"""
backend/database.py
===================
SQLAlchemy database layer: engine creation, session factory, declarative base,
and the FastAPI dependency `get_db()` that provides a scoped session per
request with automatic commit/rollback/close.

Design decisions:
- SQLite for local development (zero-config, file-based).
- Swap to PostgreSQL by changing DATABASE_URL in .env — no code changes needed.
- `check_same_thread=False` is required for SQLite because FastAPI may handle
  requests across multiple threads.
- `autocommit=False` + `autoflush=False` gives explicit transaction control.
"""

from __future__ import annotations

import logging
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.config import get_settings


logger = logging.getLogger(__name__)

settings = get_settings()

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args: dict = {}

if settings.database_url.startswith("sqlite"):
    # SQLite-specific: allow cross-thread usage required by FastAPI/uvicorn
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=settings.sqlalchemy_echo,
    # Connection pool settings — SQLite uses StaticPool by default for
    # in-memory DBs; file-based SQLite works with the default pool.
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001
    """
    Enable WAL mode and foreign key enforcement for SQLite connections.

    WAL (Write-Ahead Logging) dramatically improves concurrent read
    performance on SQLite. Foreign key enforcement is off by default in
    SQLite and must be activated per-connection.
    """
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,   # Keep objects usable after commit
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class for all ORM models.

    All models in `backend/models/` inherit from this class so that
    `Base.metadata.create_all(engine)` can create every table at once.
    """
    pass


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def create_all_tables() -> None:
    """
    Create all tables defined by ORM models that inherit from Base.

    Called once at application startup (see backend/main.py lifespan event).
    Safe to call repeatedly — tables are only created if they do not exist.
    """
    # Import all models here so their metadata is registered on Base
    # before create_all is called.
    import backend.models  # noqa: F401

    logger.info("Creating database tables (if not present)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")


def verify_database_connection() -> bool:
    """
    Execute a trivial query to confirm the database is reachable.

    Returns True on success, False on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
        return True
    except Exception as exc:
        logger.error("Database connection failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a SQLAlchemy Session per request.

    Usage in a router::

        @router.post("/example")
        def my_route(db: Session = Depends(get_db)):
            ...

    The session is automatically committed on success, rolled back on any
    exception, and always closed at the end of the request.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
