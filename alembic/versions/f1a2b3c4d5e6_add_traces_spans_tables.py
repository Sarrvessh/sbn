"""Add traces and spans tables (PostgreSQL).

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


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("flagged_for_governance", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id"),
    )
    op.create_index(op.f("ix_traces_request_id"), "traces", ["request_id"])
    op.create_index(op.f("ix_traces_project_name"), "traces", ["project_name"])
    op.create_index(op.f("ix_traces_timestamp"), "traces", ["timestamp"])

    op.create_table(
        "spans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("span_id", sa.String(length=32), nullable=False),
        sa.Column("parent_span_id", sa.String(length=32), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("trace_request_id", sa.String(length=64), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=30), nullable=False, server_default="INTERNAL"),
        sa.Column("span_type", sa.String(length=30), nullable=False),
        sa.Column("input", sa.Text(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("tool_name", sa.String(length=255), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("retrieval_documents", sa.JSON(), nullable=True),
        sa.Column("status_code", sa.String(length=10), nullable=False, server_default="UNSET"),
        sa.Column("status_message", sa.String(length=500), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("span_id"),
    )
    op.create_index(op.f("ix_spans_span_id"), "spans", ["span_id"])
    op.create_index(op.f("ix_spans_parent_span_id"), "spans", ["parent_span_id"])
    op.create_index(op.f("ix_spans_trace_id"), "spans", ["trace_id"])
    op.create_index(op.f("ix_spans_trace_request_id"), "spans", ["trace_request_id"])
    op.create_index(op.f("ix_spans_project_name"), "spans", ["project_name"])


def downgrade() -> None:
    op.drop_table("spans")
    op.drop_table("traces")