"""Business domain request and response contracts."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CustomerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()


class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: EmailStr | None


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(min_length=3, max_length=3)
    initial_quantity: int = Field(default=0, ge=0)

    @field_validator("sku", "name")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sku: str
    name: str
    unit_price: Decimal
    currency: str
    is_active: bool


class InventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)


class InventoryResponse(BaseModel):
    product_id: str
    quantity: int


class SaleCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=36)
    product_id: str = Field(min_length=1, max_length=36)
    quantity: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=500)


class SaleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    customer_id: str
    product_id: str
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    currency: str
    notes: str | None
    created_by: str


class SaleResult(BaseModel):
    sale: SaleResponse
    replayed: bool
