"""Filesystem storage for uploaded and generated files.

The database stores only metadata. Every object receives an opaque generated name so
user-controlled filenames can never select or overwrite a filesystem path.
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.models.files import FileRecord
from backend.app.models.security import User
from backend.app.security.audit import record_audit

ALLOWED_EXTENSIONS = frozenset({".xlsx", ".csv", ".tsv"})
ALLOWED_PURPOSES = frozenset({"upload", "export"})
DEFAULT_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
}


class StorageError(ValueError):
    """Base class for safe, user-facing storage validation failures."""


class UnsupportedFileTypeError(StorageError):
    """Raised when a file extension is not supported by the MVP."""


class FileTooLargeError(StorageError):
    """Raised when a stream exceeds the configured upload limit."""


class InvalidFileNameError(StorageError):
    """Raised when a filename cannot safely be represented as metadata."""


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Information returned after an atomic filesystem write."""

    original_name: str
    storage_path: str
    mime_type: str
    size_bytes: int
    sha256: str
    purpose: str


class FileStorage:
    """Store files below one configured root and resolve only relative paths."""

    def __init__(self, root: str | Path, max_bytes: int) -> None:
        self.root = Path(root).expanduser().resolve()
        self.max_bytes = max_bytes
        self.root.mkdir(parents=True, exist_ok=True)

    def store(
        self,
        source: BinaryIO,
        *,
        original_name: str,
        content_type: str | None = None,
        purpose: str = "upload",
    ) -> StoredObject:
        """Stream one file into an opaque, atomically-created object."""
        if purpose not in ALLOWED_PURPOSES:
            raise StorageError("El propósito del archivo no es válido")

        safe_name = self._safe_name(original_name)
        extension = Path(safe_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
            raise UnsupportedFileTypeError(f"Solo se permiten archivos: {allowed}")

        mime_type = (content_type or "").split(";", 1)[0].strip().lower()
        if not mime_type or mime_type == "application/octet-stream":
            mime_type = DEFAULT_MIME_TYPES[extension]

        destination_dir = self.root / ("exports" if purpose == "export" else "uploads")
        destination_dir.mkdir(parents=True, exist_ok=True)
        object_name = f"{uuid4().hex}{extension}"
        final_path = destination_dir / object_name
        temporary_path = destination_dir / f".{object_name}.partial"
        digest = hashlib.sha256()
        size = 0

        try:
            with temporary_path.open("wb") as target:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise FileTooLargeError("El archivo supera el límite configurado")
                    digest.update(chunk)
                    target.write(chunk)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary_path, final_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            final_path.unlink(missing_ok=True)
            raise

        relative_path = final_path.relative_to(self.root).as_posix()
        return StoredObject(
            original_name=safe_name,
            storage_path=relative_path,
            mime_type=mime_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
            purpose=purpose,
        )

    def resolve(self, relative_path: str) -> Path:
        """Resolve a metadata path and reject traversal outside the storage root."""
        candidate = (self.root / relative_path).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise StorageError("La ruta del archivo no es válida") from error
        return candidate

    def delete(self, relative_path: str) -> None:
        """Delete one object after validating its path is inside the root."""
        self.resolve(relative_path).unlink(missing_ok=True)

    @staticmethod
    def _safe_name(original_name: str) -> str:
        name = (original_name or "").replace("\x00", "").strip()
        if not name:
            raise InvalidFileNameError("El archivo debe tener un nombre")
        name = Path(name).name
        if not name or name in {".", ".."}:
            raise InvalidFileNameError("El nombre del archivo no es válido")
        if len(name) > 255:
            raise InvalidFileNameError("El nombre del archivo es demasiado largo")
        return name


def register_file(
    session: Session,
    actor: User,
    stored: StoredObject,
) -> FileRecord:
    """Persist metadata and audit it; callers remove the object if commit fails."""
    record = FileRecord(
        original_name=stored.original_name,
        storage_path=stored.storage_path,
        mime_type=stored.mime_type
        or mimetypes.guess_type(stored.original_name)[0]
        or "application/octet-stream",
        size_bytes=stored.size_bytes,
        sha256=stored.sha256,
        purpose=stored.purpose,
        created_by=actor.id,
    )
    session.add(record)
    record_audit(
        session,
        user_id=actor.id,
        action="file.register",
        tool="storage.register_file",
        parameters_summary=f"purpose={stored.purpose};size_bytes={stored.size_bytes}",
        result="created",
        status="success",
    )
    session.commit()
    session.refresh(record)
    return record
