"""Persistence adapter selection."""

from __future__ import annotations

from pathlib import Path

from operatix.config import Settings, StorageBackend
from operatix.infrastructure.excel_repository import ExcelSalesRepository
from operatix.infrastructure.google_sheets_repository import GoogleSheetsSalesRepository
from operatix.ports.sales_repository import SalesRepository


def build_repository(
    settings: Settings,
    backend: StorageBackend | None = None,
    *,
    excel_path: str | Path | None = None,
    spreadsheet_id: str | None = None,
    credentials_path: str | Path | None = None,
    worksheet: str | None = None,
) -> SalesRepository:
    """Create a persistence adapter from runtime settings and optional UI overrides."""
    selected = backend or settings.storage_backend
    if selected == "excel":
        return ExcelSalesRepository(
            excel_path or settings.excel_path,
            worksheet=worksheet or settings.google_worksheet,
        )

    sheet_id = spreadsheet_id or settings.google_spreadsheet_id or ""
    return GoogleSheetsSalesRepository(
        spreadsheet_id=sheet_id,
        credentials_path=credentials_path or settings.google_credentials_path,
        worksheet=worksheet or settings.google_worksheet,
    )
