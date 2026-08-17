"""Small protected endpoints used to verify RBAC wiring."""

from fastapi import APIRouter, Depends

from backend.app.models.security import User
from backend.app.security.dependencies import require_permission
from backend.app.security.permissions import PermissionCode

router = APIRouter(prefix="/api/v1/security", tags=["security"])


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
