"""Add customers, products, inventory and sales."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_business"
down_revision: str | None = "0002_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_customers"),
    )
    op.create_index("ix_customers_email", "customers", ["email"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
        sa.UniqueConstraint("sku", name="uq_products_sku"),
    )
    op.create_index("ix_products_sku", "products", ["sku"], unique=False)

    op.create_table(
        "inventory",
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_inventory_product_id_products",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("product_id", name="pk_inventory"),
    )

    op.create_table(
        "sales",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_sales_created_by_users", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_sales_customer_id_customers",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_sales_product_id_products",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_sales"),
        sa.UniqueConstraint("idempotency_key", name="uq_sales_idempotency_key"),
    )
    op.create_index("ix_sales_customer_id", "sales", ["customer_id"], unique=False)
    op.create_index("ix_sales_product_id", "sales", ["product_id"], unique=False)
    op.create_index("ix_sales_created_by", "sales", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sales_created_by", table_name="sales")
    op.drop_index("ix_sales_product_id", table_name="sales")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_table("sales")
    op.drop_table("inventory")
    op.drop_index("ix_products_sku", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
