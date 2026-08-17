"""Explicit, permission-aware tool execution boundary."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.security.permissions import PermissionCode
from backend.app.services.errors import BusinessError
from backend.app.services.products import list_inventory
from backend.app.services.sales import create_sale, list_sales, sales_summary


class ToolExecutionLimitError(BusinessError):
    """Raised when a request attempts too many tool calls."""


class UnknownToolError(BusinessError):
    """Raised when a model requests a tool that is not registered."""


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Tool metadata and handler contract."""

    name: str
    permission: PermissionCode
    handler: Callable[[Session, User, Mapping[str, Any]], Any]


def _create_sale_tool(
    session: Session,
    actor: User,
    arguments: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt validated tool arguments to the transactional sale service."""
    from backend.app.api.schemas.business import SaleCreate

    payload = SaleCreate.model_validate(arguments)
    idempotency_key = str(arguments.get("idempotency_key", ""))
    sale, replayed = create_sale(session, actor, payload, idempotency_key)
    return {"sale": sale, "replayed": replayed}


def _get_sales_tool(
    session: Session,
    _actor: User,
    _arguments: Mapping[str, Any],
) -> list[Any]:
    """Read sales through the same controlled boundary used by the agent."""
    return list_sales(session)


def _get_inventory_tool(
    session: Session,
    _actor: User,
    _arguments: Mapping[str, Any],
) -> list[Any]:
    """Read inventory through an explicit tool contract."""
    return list_inventory(session)


def _get_sales_summary_tool(
    session: Session,
    _actor: User,
    _arguments: Mapping[str, Any],
) -> dict[str, object]:
    """Return currency-safe metrics for reporting tools."""
    return sales_summary(session)


class ToolRegistry:
    """Registry that limits, authorizes and dispatches tools explicitly."""

    def __init__(self, specs: list[ToolSpec], *, max_calls: int = 1) -> None:
        self._specs = {spec.name: spec for spec in specs}
        self._max_calls = max_calls
        self._calls = 0

    def execute(
        self,
        session: Session,
        actor: User,
        name: str,
        arguments: Mapping[str, Any],
    ) -> Any:
        """Execute one authorized tool and reject loops or unknown names."""
        if self._calls >= self._max_calls:
            raise ToolExecutionLimitError("Tool execution limit reached")
        spec = self._specs.get(name)
        if spec is None:
            raise UnknownToolError("Unknown tool")
        self._calls += 1
        if not actor.has_permission(spec.permission.value):
            record_audit(
                session,
                user_id=actor.id,
                action="authorization.denied",
                tool=name,
                parameters_summary=f"permission={spec.permission.value}",
                result="forbidden",
                status="denied",
            )
            session.commit()
            raise PermissionError("Permission denied")
        return spec.handler(session, actor, arguments)


def build_default_registry() -> ToolRegistry:
    """Build the phase-three registry; future tools are added explicitly."""
    return ToolRegistry(
        [
            ToolSpec(
                name="create_sale",
                permission=PermissionCode.CREATE,
                handler=_create_sale_tool,
            ),
            ToolSpec(
                name="get_sales",
                permission=PermissionCode.READ,
                handler=_get_sales_tool,
            ),
            ToolSpec(
                name="get_inventory",
                permission=PermissionCode.READ,
                handler=_get_inventory_tool,
            ),
            ToolSpec(
                name="get_sales_summary",
                permission=PermissionCode.REPORTS,
                handler=_get_sales_summary_tool,
            ),
        ],
        max_calls=1,
    )
