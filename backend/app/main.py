"""FastAPI application entrypoint for OPERATIX."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.routes.health import router as health_router
from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    """Build the API application without performing network or database I/O."""
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.1.0")
    application.include_router(health_router)
    return application


app = create_app()
