"""Registration, login and current-user endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from backend.app.db.session import get_session
from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.security.dependencies import get_current_user
from backend.app.security.passwords import hash_password, verify_password
from backend.app.security.permissions import RoleName
from backend.app.security.roles import ensure_role
from backend.app.security.tokens import create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def user_response(user: User) -> UserResponse:
    """Convert an ORM user to a safe API response."""
    return UserResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        roles=[role.name for role in user.roles],
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)) -> UserResponse:
    """Register a normal USER; privileged roles are never accepted from the client."""
    email = str(payload.email)
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    user.roles.append(ensure_role(session, RoleName.USER))
    session.add(user)
    try:
        session.flush()
        record_audit(
            session,
            user_id=user.id,
            action="user.register",
            tool="auth.register",
            parameters_summary=f"email={email}",
            result="created",
            status="success",
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from error
    session.refresh(user)
    return user_response(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    """Authenticate credentials and issue a short-lived bearer token."""
    email = str(payload.email)
    user = session.scalar(select(User).where(User.email == email))
    valid = (
        user is not None
        and user.is_active
        and verify_password(payload.password, user.password_hash)
    )
    if not valid:
        record_audit(
            session,
            user_id=user.id if user else None,
            action="user.login",
            tool="auth.login",
            parameters_summary=f"email={email}",
            result="invalid_credentials",
            status="failure",
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user.id)
    record_audit(
        session,
        user_id=user.id,
        action="user.login",
        tool="auth.login",
        parameters_summary=f"email={email}",
        result="authenticated",
        status="success",
    )
    session.commit()
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the authenticated user's safe profile."""
    return user_response(current_user)
