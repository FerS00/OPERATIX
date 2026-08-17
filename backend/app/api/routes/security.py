"""Protected security and audit endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_session
from backend.app.models.security import AuditLog, User
from backend.app.security.dependencies import require_permission
from backend.app.security.permissions import PermissionCode

router = APIRouter(prefix="/api/v1/security", tags=["security"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/read-check")
def read_check(
    current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> dict[str, str]:
    """Confirm that the authenticated user has READ permission."""
    return {"status": "authorized", "permission": PermissionCode.READ.value}


@router.get("/admin-check")
def admin_check(
    current_user: User = Depends(require_permission(PermissionCode.ADMIN)),
) -> dict[str, str]:
    """Protected placeholder for future administrative operations."""
    return {"status": "authorized", "permission": PermissionCode.ADMIN.value}


@router.get("/audit")
def audit_entries(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.ADMIN)),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[dict[str, object]]:
    """Return a bounded, read-only audit feed for administrators."""
    entries = session.scalars(
        select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    )
    return [
        {
            "id": entry.id,
            "action": entry.action,
            "tool": entry.tool,
            "parameters_summary": entry.parameters_summary,
            "result": entry.result,
            "status": entry.status,
            "created_at": entry.created_at,
        }
        for entry in entries
    ]
