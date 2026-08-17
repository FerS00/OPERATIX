import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import get_session
from backend.app.main import app


@pytest.fixture
def business_client(monkeypatch):
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
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()
    get_settings.cache_clear()


def _token(client: TestClient) -> str:
    client.post(
        "/api/v1/auth/register",
        json={"email": "sales@example.com", "password": "correct horse battery staple"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "sales@example.com", "password": "correct horse battery staple"},
    )
    return response.json()["access_token"]


def test_sale_tool_is_authorized_idempotent_and_decrements_stock(business_client) -> None:
    client = business_client
    headers = {"Authorization": f"Bearer {_token(client)}"}

    customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "Ana Torres", "email": "ana@example.com"},
    )
    product = client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "sku": "LAP-001",
            "name": "Laptop",
            "unit_price": "25.00",
            "currency": "USD",
            "initial_quantity": 5,
        },
    )
    assert customer.status_code == 201
    assert product.status_code == 201

    sale_payload = {
        "customer_id": customer.json()["id"],
        "product_id": product.json()["id"],
        "quantity": 2,
    }
    first = client.post(
        "/api/v1/sales",
        headers={**headers, "Idempotency-Key": "order-001"},
        json=sale_payload,
    )
    replay = client.post(
        "/api/v1/sales",
        headers={**headers, "Idempotency-Key": "order-001"},
        json=sale_payload,
    )
    conflict = client.post(
        "/api/v1/sales",
        headers={**headers, "Idempotency-Key": "order-001"},
        json={**sale_payload, "quantity": 3},
    )

    assert first.status_code == 201
    assert first.json()["sale"]["total_amount"] == "50.00"
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert conflict.status_code == 409

    inventory = client.get("/api/v1/inventory", headers=headers)
    assert inventory.status_code == 200
    assert inventory.json()[0]["quantity"] == 3
