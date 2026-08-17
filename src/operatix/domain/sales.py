"""Sale transaction models independent from LLM and storage providers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

MONEY_STEP = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    """Normalize monetary values to two decimal places."""
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


class SaleCommand(BaseModel):
    """Structured arguments expected from the model's tool call."""

    model_config = ConfigDict(str_strip_whitespace=True)

    customer_name: str = Field(min_length=1, description="Nombre completo del cliente.")
    product: str = Field(min_length=1, description="Producto o servicio vendido.")
    quantity: int = Field(gt=0, description="Cantidad de unidades vendidas.")
    amount: Decimal = Field(gt=0, description="Importe monetario indicado por el usuario.")
    price_basis: Literal["total", "unit"] = Field(
        default="total",
        description=(
            "Usa 'unit' solo si el usuario dice por unidad, cada uno o equivalente; "
            "en los demás casos usa 'total'."
        ),
    )
    currency: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="Código ISO 4217, por ejemplo USD o PEN.",
    )
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class SaleRecord(BaseModel):
    """Canonical transaction persisted by OPERATIX."""

    transaction_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    customer_name: str
    product: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    total_amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    notes: str | None = None

    @field_validator("unit_price", "total_amount")
    @classmethod
    def normalize_money(cls, value: Decimal) -> Decimal:
        return money(value)

    @classmethod
    def from_command(
        cls,
        command: SaleCommand,
        transaction_id: UUID | None = None,
    ) -> SaleRecord:
        if command.price_basis == "unit":
            unit_price = money(command.amount)
            total_amount = money(command.amount * command.quantity)
        else:
            total_amount = money(command.amount)
            unit_price = money(command.amount / command.quantity)

        return cls(
            transaction_id=transaction_id or uuid4(),
            customer_name=command.customer_name,
            product=command.product,
            quantity=command.quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            currency=command.currency,
            notes=command.notes,
        )


SALE_HEADERS = [
    "transaction_id",
    "created_at",
    "customer_name",
    "product",
    "quantity",
    "unit_price",
    "total_amount",
    "currency",
    "notes",
]
