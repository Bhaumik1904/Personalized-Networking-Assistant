"""
backend/models/__init__.py
===========================
Re-exports all SQLAlchemy ORM models so that:

1. `backend.database.create_all_tables()` can simply do
   `import backend.models` and every model's metadata is registered
   on `Base` before `Base.metadata.create_all()` is called.

2. Consumers can import from the package directly::

       from backend.models import UserProfile, NetworkingSession

All models are listed explicitly — wildcard imports are intentionally avoided.
"""

from backend.models.event_context import EventContext
from backend.models.generated_starter import GeneratedStarter
from backend.models.log_entry import (
    ACTION_ERROR,
    ACTION_FACT_CHECK,
    ACTION_FEEDBACK,
    ACTION_GENERATE_STARTER,
    ACTION_SESSION_START,
    LogEntry,
)
from backend.models.networking_session import NetworkingSession
from backend.models.user_profile import UserProfile
from backend.models.wikipedia_fact_check import (
    STATUS_FOUND,
    STATUS_NOT_FOUND,
    WikipediaFactCheck,
)

__all__ = [
    # ORM models
    "UserProfile",
    "EventContext",
    "NetworkingSession",
    "GeneratedStarter",
    "WikipediaFactCheck",
    "LogEntry",
    # LogEntry action constants
    "ACTION_GENERATE_STARTER",
    "ACTION_FACT_CHECK",
    "ACTION_FEEDBACK",
    "ACTION_SESSION_START",
    "ACTION_ERROR",
    # WikipediaFactCheck status constants
    "STATUS_FOUND",
    "STATUS_NOT_FOUND",
]
