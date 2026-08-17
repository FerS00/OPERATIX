"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_session
from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.security.permissions import PermissionCode
from backend.app.security.tokens import InvalidAccessToken, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    """Authenticate a bearer token and load the active user from MySQL."""
    try:
        user_id = decode_access_token(token)
    except InvalidAccessToken as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    user = session.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_permission(permission: PermissionCode) -> Callable:
    """Build a dependency that enforces one permission and audits denials."""

    def dependency(
        current_user: Annotated[User, Depends(get_current_user)],
        session: Annotated[Session, Depends(get_session)],
    ) -> User:
        if not current_user.has_permission(permission.value):
            record_audit(
                session,
                user_id=current_user.id,
                action="authorization.denied",
                tool=None,
                parameters_summary=f"permission={permission.value}",
                result="forbidden",
                status="denied",
            )
            session.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
        return current_user

    return dependency
