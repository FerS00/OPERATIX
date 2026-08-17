"""Transactional sale service with inventory and idempotency guarantees."""

from __future__ import annotations

import hashlib
import json
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.schemas.business import SaleCreate
from backend.app.models.business import Customer, Inventory, Product, Sale
from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.services.errors import (
    DuplicateResourceError,
    IdempotencyConflictError,
    InsufficientStockError,
    ResourceNotFoundError,
)

MONEY_STEP = Decimal("0.01")


def _request_hash(payload: SaleCreate) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def create_sale(
    session: Session,
    actor: User,
    payload: SaleCreate,
    idempotency_key: str,
) -> tuple[Sale, bool]:
    """Create one sale atomically; replaying the same command is safe."""
    key = idempotency_key.strip()
    if not 8 <= len(key) <= 255:
        raise ValueError("Idempotency-Key must contain between 8 and 255 characters")
    request_hash = _request_hash(payload)
    existing = session.scalar(select(Sale).where(Sale.idempotency_key == key))
    if existing is not None:
        if existing.request_hash != request_hash:
            raise IdempotencyConflictError("Idempotency-Key was reused with different data")
        record_audit(
            session,
            user_id=actor.id,
            action="sale.replay",
            tool="sales.create_sale",
            parameters_summary=f"idempotency_key={key}",
            result="already_exists",
            status="success",
        )
        session.commit()
        return existing, True

    customer = session.scalar(select(Customer).where(Customer.id == payload.customer_id))
    product = session.scalar(
        select(Product).where(Product.id == payload.product_id, Product.is_active.is_(True))
    )
    inventory = session.scalar(
        select(Inventory).where(Inventory.product_id == payload.product_id).with_for_update()
    )
    if customer is None:
        raise ResourceNotFoundError("Customer not found")
    if product is None or inventory is None:
        raise ResourceNotFoundError("Active product or inventory not found")
    if inventory.quantity < payload.quantity:
        raise InsufficientStockError("Insufficient inventory")

    total_amount = _money(product.unit_price * payload.quantity)
    inventory.quantity -= payload.quantity
    sale = Sale(
        idempotency_key=key,
        request_hash=request_hash,
        customer_id=customer.id,
        product_id=product.id,
        quantity=payload.quantity,
        unit_price=_money(product.unit_price),
        total_amount=total_amount,
        currency=product.currency,
        notes=payload.notes,
        created_by=actor.id,
    )
    session.add(sale)
    try:
        session.flush()
        record_audit(
            session,
            user_id=actor.id,
            action="sale.create",
            tool="sales.create_sale",
            parameters_summary=(
                f"customer_id={customer.id};product_id={product.id};quantity={payload.quantity}"
            ),
            result="created",
            status="success",
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateResourceError("Sale could not be created") from error
    session.refresh(sale)
    return sale, False


def list_sales(session: Session) -> list[Sale]:
    """Return persisted sales in creation order."""
    return list(session.scalars(select(Sale).order_by(Sale.created_at, Sale.id)))


def sales_summary(session: Session) -> dict[str, object]:
    """Aggregate sales by currency without adding incompatible money values."""
    totals: dict[str, Decimal] = {}
    transactions: dict[str, int] = {}
    for sale in list_sales(session):
        currency = sale.currency
        totals[currency] = _money(totals.get(currency, Decimal("0")) + sale.total_amount)
        transactions[currency] = transactions.get(currency, 0) + 1
    return {
        "transactions": sum(transactions.values()),
        "by_currency": {
            currency: {"transactions": transactions[currency], "total": str(totals[currency])}
            for currency in sorted(totals)
        },
    }
