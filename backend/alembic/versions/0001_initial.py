"""Establish the initial migration boundary for the MySQL-backed MVP."""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create no tables yet; domain tables arrive in the next phase."""
    pass


def downgrade() -> None:
    """Keep the initial migration reversible while it has no schema changes."""
    pass
