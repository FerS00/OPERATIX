"""Controlled orchestration boundary for future LLM adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.security import User
from backend.app.tools.registry import ToolRegistry, build_default_registry


class AIOrchestrator:
    """Execute explicitly registered tools without autonomous loops."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or build_default_registry()

    def execute(
        self,
        session: Session,
        actor: User,
        tool_name: str,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Dispatch one tool call through the registry's permission boundary."""
        return self.registry.execute(session, actor, tool_name, arguments)
