"""Customer, product, inventory and sale API adapters."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from backend.app.api.schemas.business import (
    CustomerCreate,
    CustomerResponse,
    InventoryResponse,
    InventoryUpdate,
    ProductCreate,
    ProductResponse,
    SaleCreate,
    SaleResponse,
    SaleResult,
)
from backend.app.db.session import get_session
from backend.app.models.business import Customer, Product
from backend.app.models.security import User
from backend.app.orchestrator import AIOrchestrator
from backend.app.security.dependencies import get_current_user, require_permission
from backend.app.security.permissions import PermissionCode
from backend.app.services.customers import create_customer, list_customers
from backend.app.services.errors import (
    BusinessError,
    DuplicateResourceError,
    IdempotencyConflictError,
    InsufficientStockError,
    ResourceNotFoundError,
)
from backend.app.services.products import (
    create_product,
    list_inventory,
    list_products,
    update_inventory,
)
from backend.app.services.sales import list_sales, sales_summary
from backend.app.tools.registry import (
    ToolExecutionLimitError,
    UnknownToolError,
)

router = APIRouter(prefix="/api/v1", tags=["business"])
SessionDependency = Annotated[Session, Depends(get_session)]
CurrentUserDependency = Annotated[User, Depends(get_current_user)]


def _business_error(error: BusinessError) -> HTTPException:
    if isinstance(error, ResourceNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, InsufficientStockError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(error, (DuplicateResourceError, IdempotencyConflictError)):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_customer_endpoint(
    payload: CustomerCreate,
    session: SessionDependency,
    current_user: User = Depends(require_permission(PermissionCode.CREATE)),
) -> Customer:
    try:
        return create_customer(session, current_user, payload)
    except BusinessError as error:
        raise _business_error(error) from error


@router.get("/customers", response_model=list[CustomerResponse])
def list_customers_endpoint(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> list[Customer]:
    return list_customers(session)


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product_endpoint(
    payload: ProductCreate,
    session: SessionDependency,
    current_user: User = Depends(require_permission(PermissionCode.CREATE)),
) -> Product:
    try:
        return create_product(session, current_user, payload)
    except BusinessError as error:
        raise _business_error(error) from error


@router.get("/products", response_model=list[ProductResponse])
def list_products_endpoint(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> list[Product]:
    return list_products(session)


@router.get("/inventory", response_model=list[InventoryResponse])
def list_inventory_endpoint(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
):
    return list_inventory(session)


@router.put("/inventory/{product_id}", response_model=InventoryResponse)
def update_inventory_endpoint(
    product_id: str,
    payload: InventoryUpdate,
    session: SessionDependency,
    current_user: User = Depends(require_permission(PermissionCode.UPDATE)),
):
    try:
        return update_inventory(session, current_user, product_id, payload)
    except BusinessError as error:
        raise _business_error(error) from error


@router.post("/sales", response_model=SaleResult, status_code=status.HTTP_201_CREATED)
def create_sale_endpoint(
    payload: SaleCreate,
    response: Response,
    session: SessionDependency,
    current_user: CurrentUserDependency,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SaleResult:
    """Create a sale only through the permission-aware tool registry."""
    if idempotency_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required",
        )
    try:
        result = AIOrchestrator().execute(
            session,
            current_user,
            "create_sale",
            {**payload.model_dump(), "idempotency_key": idempotency_key},
        )
    except (BusinessError, ValueError) as error:
        raise (
            _business_error(error)
            if isinstance(error, BusinessError)
            else HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))
        ) from error
    except (PermissionError, ToolExecutionLimitError, UnknownToolError) as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error

    sale = result["sale"]
    if result["replayed"]:
        response.status_code = status.HTTP_200_OK
    return SaleResult(sale=SaleResponse.model_validate(sale), replayed=result["replayed"])


@router.get("/sales", response_model=list[SaleResponse])
def list_sales_endpoint(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
):
    return list_sales(session)


@router.get("/sales/summary")
def sales_summary_endpoint(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.REPORTS)),
) -> dict[str, object]:
    return sales_summary(session)
