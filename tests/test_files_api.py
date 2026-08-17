from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_session
from backend.app.main import app
from backend.app.models.security import User
from backend.app.security.permissions import RoleName
from backend.app.security.roles import ensure_role


@pytest.fixture
def files_client(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("JWT_SECRET", "test-secret-that-is-longer-than-32-characters")
    monkeypatch.setenv("OPERATIX_STORAGE_ROOT", str(tmp_path))
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
    yield TestClient(app), engine, tmp_path
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
    get_settings.cache_clear()


def _token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": "files@example.com", "password": "correct horse battery staple"},
    )
    return client.post(
        "/api/v1/auth/login",
        json={"email": "files@example.com", "password": "correct horse battery staple"},
    ).json()["access_token"]


def test_upload_preview_list_and_download_file(files_client) -> None:
    client, _engine, _root = files_client
    headers = {"Authorization": f"Bearer {_token(client)}"}

    uploaded = client.post(
        "/api/v1/files/upload",
        headers=headers,
        files={
            "upload": (
                "ventas.csv",
                b"sku,quantity,customer_email\nLAP-1,2,ana@example.com\n",
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 201
    file_id = uploaded.json()["id"]

    preview = client.post(f"/api/v1/files/{file_id}/excel/preview", headers=headers)
    listed = client.get("/api/v1/files", headers=headers)
    downloaded = client.get(f"/api/v1/files/{file_id}/download", headers=headers)

    assert preview.status_code == 200
    assert preview.json()["valid_rows"] == 1
    assert listed.status_code == 200
    assert listed.json()[0]["original_name"] == "ventas.csv"
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(b"sku,quantity")


def test_manager_can_generate_sales_report(files_client) -> None:
    client, engine, _root = files_client
    headers = {"Authorization": f"Bearer {_token(client)}"}
    with Session(engine) as session:
        user = session.scalar(select(User).where(User.email == "files@example.com"))
        assert user is not None
        user.roles.append(ensure_role(session, RoleName.MANAGER))
        session.commit()

    summary = client.get("/api/v1/reports/sales/summary", headers=headers)
    exported = client.post("/api/v1/reports/sales/export", headers=headers)

    assert summary.status_code == 200
    assert summary.json()["transactions"] == 0
    assert exported.status_code == 201
    assert exported.json()["purpose"] == "export"
