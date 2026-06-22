"""add_teams_budgets_tables

Revision ID: c4a1f62b8d0e
Revises: e471be7c3f7b
Create Date: 2026-06-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c4a1f62b8d0e'
down_revision: Union[str, Sequence[str], None] = 'e471be7c3f7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('teams'):
        op.create_table('teams',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
        )

    if not inspector.has_table('team_project_assignments'):
        op.create_table('team_project_assignments',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('project_name', sa.String(length=255), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_team_project_assignments_team_id'), 'team_project_assignments', ['team_id'], unique=False)
        op.create_index(op.f('ix_team_project_assignments_project_name'), 'team_project_assignments', ['project_name'], unique=False)

    if not inspector.has_table('budgets'):
        op.create_table('budgets',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('month', sa.String(length=7), nullable=False),
            sa.Column('budget_cents', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_budgets_team_id'), 'budgets', ['team_id'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('budgets'):
        op.drop_index(op.f('ix_budgets_team_id'), table_name='budgets')
        op.drop_table('budgets')

    if inspector.has_table('team_project_assignments'):
        op.drop_index(op.f('ix_team_project_assignments_project_name'), table_name='team_project_assignments')
        op.drop_index(op.f('ix_team_project_assignments_team_id'), table_name='team_project_assignments')
        op.drop_table('team_project_assignments')

    if inspector.has_table('teams'):
        op.drop_table('teams')
