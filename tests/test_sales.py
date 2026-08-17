from decimal import Decimal
from uuid import UUID

from operatix.domain.sales import SaleCommand, SaleRecord


def test_total_price_is_split_into_unit_price() -> None:
    command = SaleCommand(
        customer_name="Juan Perez",
        product="laptop",
        quantity=5,
        amount=Decimal("2500"),
        price_basis="total",
        currency="usd",
    )

    sale = SaleRecord.from_command(command)

    assert isinstance(sale.transaction_id, UUID)
    assert sale.unit_price == Decimal("500.00")
    assert sale.total_amount == Decimal("2500.00")
    assert sale.currency == "USD"


def test_unit_price_is_multiplied_by_quantity() -> None:
    command = SaleCommand(
        customer_name="Ana Torres",
        product="monitor",
        quantity=3,
        amount=Decimal("200"),
        price_basis="unit",
    )

    sale = SaleRecord.from_command(command)

    assert sale.unit_price == Decimal("200.00")
    assert sale.total_amount == Decimal("600.00")
