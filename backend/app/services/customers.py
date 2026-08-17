"""Customer application service."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.schemas.business import CustomerCreate
from backend.app.models.business import Customer
from backend.app.models.security import User
from backend.app.security.audit import record_audit
from backend.app.services.errors import DuplicateResourceError


def create_customer(session: Session, actor: User, payload: CustomerCreate) -> Customer:
    """Create a customer and record the operation atomically."""
    customer = Customer(name=payload.name, email=str(payload.email) if payload.email else None)
    session.add(customer)
    try:
        session.flush()
        record_audit(
            session,
            user_id=actor.id,
            action="customer.create",
            tool="customers.create_customer",
            parameters_summary=f"name={customer.name}",
            result="created",
            status="success",
        )
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateResourceError("Customer could not be created") from error
    session.refresh(customer)
    return customer


def list_customers(session: Session) -> list[Customer]:
    """Return customers in stable creation order."""
    return list(session.scalars(select(Customer).order_by(Customer.created_at, Customer.id)))
