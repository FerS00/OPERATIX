import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_session
from backend.app.main import app
from backend.app.models import AuditLog


@pytest.fixture
def client_and_engine(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-longer-than-32-characters")
    monkeypatch.setenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    get_settings.cache_clear()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    yield TestClient(app), engine
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
    get_settings.cache_clear()


def test_register_login_me_and_audit(client_and_engine) -> None:
    client, engine = client_and_engine

    registered = client.post(
        "/api/v1/auth/register",
        json={"email": "Ana@Example.com", "password": "correct horse battery staple"},
    )
    assert registered.status_code == 201
    assert registered.json()["roles"] == ["USER"]
    assert "password" not in registered.json()

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"email": "ana@example.com", "password": "correct horse battery staple"},
    )
    assert logged_in.status_code == 200
    token = logged_in.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/security/read-check", headers=headers).status_code == 200
    assert client.get("/api/v1/security/admin-check", headers=headers).status_code == 403

    with Session(engine) as session:
        logs = session.scalars(select(AuditLog)).all()
    assert {log.action for log in logs} >= {"user.register", "user.login"}
    assert all("correct horse" not in log.parameters_summary for log in logs)


def test_invalid_login_and_short_password_are_rejected(client_and_engine) -> None:
    client, _ = client_and_engine

    short_password = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid@example.com", "password": "short"},
    )
    assert short_password.status_code == 422

    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )
    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong password"},
    )
    assert invalid_login.status_code == 401
