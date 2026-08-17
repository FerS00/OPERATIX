"""SQLAlchemy engine lifecycle and request-level connections."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from backend.app.core.config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Create the process-local engine lazily, without connecting at import time."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
        )
    return _engine


def reset_engine() -> None:
    """Dispose the cached engine; useful for tests and controlled shutdowns."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
