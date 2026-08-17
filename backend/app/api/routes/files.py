"""Authenticated upload, preview and download endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.schemas.files import ExcelPreviewResponse
from backend.app.api.schemas.files import FileResponse as FileMetadataResponse
from backend.app.core.config import get_settings
from backend.app.db.session import get_session
from backend.app.models.files import FileRecord
from backend.app.models.security import User
from backend.app.security.dependencies import require_permission
from backend.app.security.permissions import PermissionCode
from backend.app.services.excel import ExcelFileError, preview_file
from backend.app.services.storage import (
    FileStorage,
    FileTooLargeError,
    StorageError,
    register_file,
)

router = APIRouter(prefix="/api/v1/files", tags=["files"])
SessionDependency = Annotated[Session, Depends(get_session)]


def _storage() -> FileStorage:
    settings = get_settings()
    return FileStorage(settings.storage_root, settings.max_upload_bytes)


@router.post("/upload", response_model=FileMetadataResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    session: SessionDependency,
    upload: UploadFile = File(...),
    current_user: User = Depends(require_permission(PermissionCode.CREATE)),
) -> FileRecord:
    """Store an allowed workbook/delimited file and persist only its metadata."""
    storage = _storage()
    stored = None
    registered = False
    try:
        stored = storage.store(
            upload.file,
            original_name=upload.filename or "upload.xlsx",
            content_type=upload.content_type,
            purpose="upload",
        )
        record = register_file(session, current_user, stored)
        registered = True
        return record
    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error)
        ) from error
    except StorageError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except Exception as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar el archivo",
        ) from error
    finally:
        if stored is not None and not registered:
            storage.delete(stored.storage_path)


@router.get("", response_model=list[FileMetadataResponse])
def list_files(
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> list[FileRecord]:
    return list(session.scalars(select(FileRecord).order_by(FileRecord.created_at.desc())))


@router.post("/{file_id}/excel/preview", response_model=ExcelPreviewResponse)
def preview_excel(
    file_id: str,
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> dict[str, object]:
    record = session.get(FileRecord, file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    try:
        return preview_file(_storage().resolve(record.storage_path))
    except ExcelFileError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    except StorageError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{file_id}/download")
def download_file(
    file_id: str,
    session: SessionDependency,
    _current_user: User = Depends(require_permission(PermissionCode.READ)),
) -> FileResponse:
    record = session.get(FileRecord, file_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no encontrado")
    path = _storage().resolve(record.storage_path)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contenido de archivo no encontrado",
        )
    return FileResponse(path, media_type=record.mime_type, filename=Path(record.original_name).name)
