"""Store binary file metadata while keeping file contents outside MySQL."""

import sqlalchemy as sa
from alembic import op

revision = "0004_files"
down_revision = "0003_business"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the file metadata table."""
    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("original_name", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index("ix_files_created_by", "files", ["created_by"], unique=False)
    op.create_index("ix_files_created_at", "files", ["created_at"], unique=False)
    op.create_index("ix_files_purpose", "files", ["purpose"], unique=False)
    op.create_index("ix_files_sha256", "files", ["sha256"], unique=False)


def downgrade() -> None:
    """Drop file metadata."""
    op.drop_index("ix_files_sha256", table_name="files")
    op.drop_index("ix_files_purpose", table_name="files")
    op.drop_index("ix_files_created_at", table_name="files")
    op.drop_index("ix_files_created_by", table_name="files")
    op.drop_table("files")
