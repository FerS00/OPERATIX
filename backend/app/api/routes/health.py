"""Health and readiness endpoints for local and container orchestration."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import get_settings
from backend.app.db.session import get_engine

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight liveness response without touching MySQL."""
    return {"status": "ok", "service": get_settings().app_name}


@router.get("/health/ready")
def readiness() -> dict[str, str]:
    """Verify that the configured MySQL connection can execute a simple query."""
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ready", "database": "mysql"}
