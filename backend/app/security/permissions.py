"""Canonical roles and permission assignments."""

from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class PermissionCode(StrEnum):
    READ = "READ"
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    EXPORT = "EXPORT"
    REPORTS = "REPORTS"
    ADMIN = "ADMIN"


ROLE_PERMISSIONS: dict[RoleName, frozenset[PermissionCode]] = {
    RoleName.ADMIN: frozenset(PermissionCode),
    RoleName.MANAGER: frozenset(
        {
            PermissionCode.READ,
            PermissionCode.CREATE,
            PermissionCode.UPDATE,
            PermissionCode.EXPORT,
            PermissionCode.REPORTS,
        }
    ),
    RoleName.USER: frozenset({PermissionCode.READ, PermissionCode.CREATE}),
}
