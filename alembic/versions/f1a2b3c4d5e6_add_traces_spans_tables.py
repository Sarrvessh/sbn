"""Add missing columns to existing traces/spans tables.

Traces/spans tables were already created by d8ef9e277c02 and
3b9acc8c9e6c. This migration adds columns that the current SQLAlchemy
models need but were missing from those original table definitions.

Revision ID: f1a2b3c4d5e6
Revises: c5a2f73b9e1f
Create Date: 2026-07-09 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "c5a2f73b9e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns(table)]
    return column in columns


def upgrade() -> None:
    if not _has_column("traces", "created_at"):
        op.add_column(
            "traces",
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    for col_name, col_type, nullable in [
        ("project_name", sa.String(255), False),
        ("retrieval_documents", sa.JSON(), True),
    ]:
        if not _has_column("spans", col_name):
            op.add_column("spans", sa.Column(col_name, col_type, nullable=nullable))

    if not _has_column("spans", "project_name"):
        op.create_index(op.f("ix_spans_project_name"), "spans", ["project_name"])


def downgrade() -> None:
    pass
