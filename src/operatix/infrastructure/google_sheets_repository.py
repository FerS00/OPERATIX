"""Google Sheets implementation of the sales repository."""

from __future__ import annotations

from pathlib import Path

import gspread

from operatix.domain.sales import SALE_HEADERS, SaleRecord


class GoogleSheetsSalesRepository:
    """Store transactions in a worksheet using a service account."""

    def __init__(
        self,
        spreadsheet_id: str,
        credentials_path: Path | str,
        worksheet: str = "Ventas",
    ) -> None:
        if not spreadsheet_id.strip():
            raise ValueError("Falta GOOGLE_SHEETS_SPREADSHEET_ID.")
        self.spreadsheet_id = spreadsheet_id
        self.credentials_path = Path(credentials_path)
        self.worksheet_name = worksheet

    def _worksheet(self):
        if not self.credentials_path.exists():
            raise FileNotFoundError(
                f"No existe el archivo de credenciales: {self.credentials_path}"
            )

        client = gspread.service_account(filename=str(self.credentials_path))
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(self.worksheet_name)
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(
                title=self.worksheet_name,
                rows=1000,
                cols=len(SALE_HEADERS),
            )
        if not worksheet.row_values(1):
            worksheet.append_row(SALE_HEADERS)
        return worksheet

    @staticmethod
    def _row(sale: SaleRecord) -> list[str | int | float]:
        return [
            str(sale.transaction_id),
            sale.created_at.isoformat(),
            sale.customer_name,
            sale.product,
            sale.quantity,
            float(sale.unit_price),
            float(sale.total_amount),
            sale.currency,
            sale.notes or "",
        ]

    def append(self, sale: SaleRecord) -> bool:
        worksheet = self._worksheet()
        transaction_id = str(sale.transaction_id)
        if transaction_id in worksheet.col_values(1)[1:]:
            return False
        worksheet.append_row(self._row(sale), value_input_option="USER_ENTERED")
        return True

    def list_all(self) -> list[SaleRecord]:
        rows = self._worksheet().get_all_records()
        return [SaleRecord.model_validate(row) for row in rows if row.get("transaction_id")]
