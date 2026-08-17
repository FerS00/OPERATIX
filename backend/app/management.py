"""Local-only administrative helper for assigning a role after first registration."""

from __future__ import annotations

import argparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_engine
from backend.app.models.security import User
from backend.app.security.permissions import RoleName
from backend.app.security.roles import ensure_role


def grant_role(email: str, role_name: RoleName) -> None:
    """Grant one canonical role to an existing user using the configured database."""
    with Session(get_engine()) as session:
        user = session.scalar(select(User).where(User.email == email.strip().lower()))
        if user is None:
            raise ValueError(f"No existe un usuario con correo {email}")
        role = ensure_role(session, role_name)
        if role not in user.roles:
            user.roles.append(role)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Asignar un rol OPERATIX a un usuario existente")
    parser.add_argument("email", help="Correo exacto del usuario registrado")
    parser.add_argument(
        "role", choices=[role.value for role in RoleName], help="ADMIN, MANAGER o USER"
    )
    arguments = parser.parse_args()
    grant_role(arguments.email, RoleName(arguments.role))
    print(f"Rol {arguments.role} asignado a {arguments.email.strip().lower()}")


if __name__ == "__main__":
    main()
