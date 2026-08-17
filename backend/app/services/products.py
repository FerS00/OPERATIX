"""Product and inventory application services."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.schemas.business import InventoryUpdate, ProductCreate
from backend.app.models.business import Inventory, Product
from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.services.errors import DuplicateResourceError, ResourceNotFoundError


def create_product(session: Session, actor: User, payload: ProductCreate) -> Product:
    """Create a product and its initial inventory row atomically."""
    product = Product(
        sku=payload.sku,
        name=payload.name,
        unit_price=payload.unit_price,
        currency=payload.currency,
        inventory=Inventory(quantity=payload.initial_quantity),
    )
    session.add(product)
    try:
        session.flush()
        record_audit(
            session,
            user_id=actor.id,
            action="product.create",
            tool="products.create_product",
            parameters_summary=f"sku={product.sku}",
            result="created",
            status="success",
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateResourceError("Product SKU already exists") from error
    session.refresh(product)
    return product


def list_products(session: Session) -> list[Product]:
    """Return active and inactive products in SKU order."""
    return list(session.scalars(select(Product).order_by(Product.sku)))


def update_inventory(
    session: Session,
    actor: User,
    product_id: str,
    payload: InventoryUpdate,
) -> Inventory:
    """Set stock explicitly, recording an auditable update."""
    inventory = session.scalar(
        select(Inventory).where(Inventory.product_id == product_id).with_for_update()
    )
    if inventory is None:
        raise ResourceNotFoundError("Product inventory not found")
    inventory.quantity = payload.quantity
    session.flush()
    record_audit(
        session,
        user_id=actor.id,
        action="inventory.update",
        tool="inventory.update_stock",
        parameters_summary=f"product_id={product_id};quantity={payload.quantity}",
        result="updated",
        status="success",
    )
    session.commit()
    session.refresh(inventory)
    return inventory


def list_inventory(session: Session) -> list[Inventory]:
    """Return inventory rows in product order."""
    return list(session.scalars(select(Inventory).order_by(Inventory.product_id)))
