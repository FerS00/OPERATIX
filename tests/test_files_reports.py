from decimal import Decimal
from io import BytesIO

import pytest
from openpyxl import load_workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.models.business import Customer, Inventory, Product, Sale
from backend.app.models.security import User
from backend.app.services.excel import preview_file
from backend.app.services.reports import build_sales_report, export_sales_report
from backend.app.services.storage import FileStorage, FileTooLargeError


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as current_session:
        yield current_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_storage_streams_opaque_paths_and_enforces_size(tmp_path) -> None:
    storage = FileStorage(tmp_path, max_bytes=100)

    stored = storage.store(
        BytesIO(b"sku,quantity\nA,1\n"),
        original_name="../../ventas.csv",
        content_type="text/csv",
    )

    assert stored.storage_path.startswith("uploads/")
    assert ".." not in stored.storage_path
    assert storage.resolve(stored.storage_path).read_bytes() == b"sku,quantity\nA,1\n"
    small_storage = FileStorage(tmp_path / "small", max_bytes=10)
    with pytest.raises(FileTooLargeError):
        small_storage.store(BytesIO(b"12345678901"), original_name="too-large.csv")


def test_preview_validates_rows_and_rejects_formulas(tmp_path) -> None:
    path = tmp_path / "ventas.csv"
    path.write_text(
        "sku,quantity,customer_email\n"
        "LAP-1,2,ana@example.com\n"
        "LAP-2,-1,\n"
        "LAP-3,=2,juan@example.com\n",
        encoding="utf-8",
    )

    preview = preview_file(path)

    assert preview["total_rows"] == 3
    assert preview["valid_rows"] == 1
    assert preview["invalid_rows"] == 2
    assert any(error["column"] == "quantity" for error in preview["errors"])


def test_report_keeps_currency_totals_separate_and_neutralizes_formula_text(
    session: Session, tmp_path
) -> None:
    actor = User(email="manager@example.com", password_hash="not-a-real-password")
    customer = Customer(name="=Formula Customer", email="customer@example.com")
    usd_product = Product(sku="USD-1", name="Laptop", unit_price=Decimal("10.00"), currency="USD")
    pen_product = Product(sku="PEN-1", name="Teclado", unit_price=Decimal("20.00"), currency="PEN")
    session.add_all([actor, customer, usd_product, pen_product])
    session.flush()
    session.add_all(
        [
            Inventory(product_id=usd_product.id, quantity=10),
            Inventory(product_id=pen_product.id, quantity=10),
            Sale(
                idempotency_key="report-usd-1",
                request_hash="a" * 64,
                customer_id=customer.id,
                product_id=usd_product.id,
                quantity=2,
                unit_price=Decimal("10.00"),
                total_amount=Decimal("20.00"),
                currency="USD",
                created_by=actor.id,
            ),
            Sale(
                idempotency_key="report-pen-1",
                request_hash="b" * 64,
                customer_id=customer.id,
                product_id=pen_product.id,
                quantity=1,
                unit_price=Decimal("20.00"),
                total_amount=Decimal("20.00"),
                currency="PEN",
                created_by=actor.id,
            ),
        ]
    )
    session.commit()

    report = build_sales_report(session)
    record, _ = export_sales_report(session, actor, FileStorage(tmp_path, max_bytes=1_000_000))
    workbook = load_workbook(tmp_path / record.storage_path, data_only=False)

    assert report["transactions"] == 2
    assert report["by_currency"]["USD"]["total"] == Decimal("20.00")
    assert report["by_currency"]["PEN"]["total"] == Decimal("20.00")
    assert workbook["Ventas"]["C2"].value == "'=Formula Customer"
