"""add_projects_table

Revision ID: a7c9e2b4d6f8
Revises: f1a2b3c4d5e6
Create Date: 2026-10-26 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a7c9e2b4d6f8"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Bring databases created by older revisions in line with the ORM models."""
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("projects"):
        op.create_table(
            "projects",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        )
        op.create_index(op.f("ix_projects_name"), "projects", ["name"], unique=False)

    if inspector.has_table("policies") and not _has_column(inspector, "policies", "action"):
        op.add_column(
            "policies",
            sa.Column(
                "action",
                sa.String(length=20),
                nullable=False,
                server_default=sa.text("'flag'"),
            ),
        )

    if not inspector.has_table("escalation_rules"):
        op.create_table(
            "escalation_rules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("rule_type", sa.String(length=30), nullable=False),
            sa.Column("rule_config", sa.JSON(), nullable=False),
            sa.Column("target_role", sa.String(length=20), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("default_agent_model", sa.String(length=255), nullable=False),
            sa.Column("max_tokens", sa.Integer(), nullable=False),
            sa.Column("temperature", sa.Float(), nullable=False),
            sa.Column("sampling_rate", sa.Integer(), nullable=False),
            sa.Column("budget_alert_threshold_pct", sa.Float(), nullable=False),
            sa.Column("openai_api_key", sa.String(length=512), nullable=True),
            sa.Column("openai_base_url", sa.String(length=512), nullable=True),
            sa.Column("openai_referer", sa.String(length=512), nullable=True),
            sa.Column("openai_app_title", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("webhooks"):
        op.create_table(
            "webhooks",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("url", sa.String(length=1024), nullable=False),
            sa.Column("secret", sa.String(length=512), nullable=True),
            sa.Column("events", sa.JSON(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if not inspector.has_table("webhook_deliveries"):
        op.create_table(
            "webhook_deliveries",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("webhook_id", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=10), nullable=False),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("response_body", sa.Text(), nullable=True),
            sa.Column(
                "delivered_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_webhook_deliveries_webhook_id"),
            "webhook_deliveries",
            ["webhook_id"],
            unique=False,
        )

    if not inspector.has_table("alert_rules"):
        op.create_table(
            "alert_rules",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("project_name", sa.String(length=255), nullable=True),
            sa.Column("alert_type", sa.String(length=30), nullable=False),
            sa.Column("severity", sa.String(length=10), nullable=False),
            sa.Column("threshold_value", sa.Float(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_alert_rules_project_name"),
            "alert_rules",
            ["project_name"],
            unique=False,
        )


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    return any(item["name"] == column for item in inspector.get_columns(table))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("projects"):
        op.drop_index(op.f("ix_projects_name"), table_name="projects")
        op.drop_table("projects")
