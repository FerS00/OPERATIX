"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

StorageBackend = Literal["excel", "google_sheets"]


def load_local_env() -> None:
    """Load developer configuration without overriding process-level secrets."""
    load_dotenv(".env.local", override=False)
    load_dotenv(".env", override=False)


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings for persistence adapters."""

    storage_backend: StorageBackend = "excel"
    excel_path: Path = Path("data/operatix.xlsx")
    google_spreadsheet_id: str | None = None
    google_worksheet: str = "Ventas"
    google_credentials_path: Path = Path(".secrets/google-service-account.json")

    @classmethod
    def from_env(cls) -> Settings:
        backend = os.getenv("OPERATIX_STORAGE_BACKEND", "excel").strip().lower()
        if backend not in {"excel", "google_sheets"}:
            raise ValueError("OPERATIX_STORAGE_BACKEND debe ser 'excel' o 'google_sheets'.")

        return cls(
            storage_backend=backend,  # type: ignore[arg-type]
            excel_path=Path(os.getenv("OPERATIX_EXCEL_PATH", "data/operatix.xlsx")),
            google_spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None,
            google_worksheet=os.getenv("GOOGLE_SHEETS_WORKSHEET", "Ventas"),
            google_credentials_path=Path(
                os.getenv(
                    "GOOGLE_APPLICATION_CREDENTIALS",
                    ".secrets/google-service-account.json",
                )
            ),
        )
