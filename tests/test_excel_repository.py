from decimal import Decimal

from operatix.domain.sales import SaleCommand, SaleRecord
from operatix.infrastructure.excel_repository import ExcelSalesRepository


def test_excel_repository_appends_and_reads_a_sale(tmp_path) -> None:
    repository = ExcelSalesRepository(tmp_path / "operatix.xlsx")
    sale = SaleRecord.from_command(
        SaleCommand(
            customer_name="Juan Perez",
            product="laptop",
            quantity=5,
            amount=Decimal("2500"),
        )
    )

    assert repository.append(sale) is True
    assert repository.append(sale) is False

    stored = repository.list_all()
    assert len(stored) == 1
    assert stored[0].transaction_id == sale.transaction_id
    assert stored[0].total_amount == Decimal("2500.00")
