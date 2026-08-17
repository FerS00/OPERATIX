"""Role and permission bootstrap helpers."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.security import Permission, Role
from backend.app.security.permissions import ROLE_PERMISSIONS, RoleName


def ensure_role(session: Session, role_name: RoleName) -> Role:
    """Create a role and its canonical permissions when they do not exist."""
    role = session.scalar(select(Role).where(Role.name == role_name.value))
    if role is None:
        role = Role(name=role_name.value)
        session.add(role)
        session.flush()

    existing = {permission.code for permission in role.permissions}
    for permission_code in ROLE_PERMISSIONS[role_name]:
        permission = session.scalar(
            select(Permission).where(Permission.code == permission_code.value)
        )
        if permission is None:
            permission = Permission(code=permission_code.value)
            session.add(permission)
            session.flush()
        if permission.code not in existing:
            role.permissions.append(permission)
    session.flush()
    return role
