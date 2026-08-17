"""Persistence contract for sales."""

from __future__ import annotations

from typing import Protocol

from operatix.domain.sales import SaleRecord


class SalesRepository(Protocol):
    """Port shared by Excel and Google Sheets adapters."""

    def append(self, sale: SaleRecord) -> bool:
        """Persist a sale; return False when its transaction ID already exists."""
        ...

    def list_all(self) -> list[SaleRecord]:
        """Return all persisted sales."""
        ...
