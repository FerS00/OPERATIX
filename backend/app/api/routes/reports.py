"""Reporting endpoints with explicit report/export permissions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.api.schemas.files import FileResponse as FileMetadataResponse
from backend.app.core.config import get_settings
from backend.app.db.session import get_session
from backend.app.models.security import User
from backend.app.security.dependencies import require_permission
from backend.app.security.permissions import PermissionCode
from backend.app.services.reports import export_sales_report, public_sales_summary
from backend.app.services.storage import FileStorage

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])
SessionDependency = Annotated[Session, Depends(get_session)]


@router.get("/sales/summary")
def sales_report_summary(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.REPORTS)),
) -> dict[str, object]:
    """Return totals grouped by currency, plus an overall transaction/unit count."""
    return public_sales_summary(session)


@router.post(
    "/sales/export",
    response_model=FileMetadataResponse,
    status_code=status.HTTP_201_CREATED,
)
def export_sales_report_endpoint(
    session: SessionDependency,
    current_user: User = Depends(require_permission(PermissionCode.EXPORT)),
):
    try:
        record, _data = export_sales_report(
            session,
            current_user,
            FileStorage(get_settings().storage_root, get_settings().max_upload_bytes),
        )
        return record
    except OSError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar el reporte",
        ) from error
