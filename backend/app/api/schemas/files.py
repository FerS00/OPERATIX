"""File metadata and Excel preview contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    purpose: str
    created_by: str
    created_at: datetime


class ExcelPreviewResponse(BaseModel):
    headers: list[str]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[dict[str, Any]]
