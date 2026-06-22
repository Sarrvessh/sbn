"""add_reviews_audit_tables

Revision ID: c5a2f73b9e1f
Revises: c4a1f62b8d0e
Create Date: 2026-06-16 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5a2f73b9e1f'
down_revision: Union[str, Sequence[str], None] = 'c4a1f62b8d0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('reviews'):
        op.create_table('reviews',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.String(length=64), nullable=False),
            sa.Column('reviewer', sa.String(length=255), nullable=False),
            sa.Column('decision', sa.String(length=20), nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_reviews_request_id'), 'reviews', ['request_id'], unique=False)
        op.create_index(op.f('ix_reviews_decision'), 'reviews', ['decision'], unique=False)

    if not inspector.has_table('audit_log'):
        op.create_table('audit_log',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('actor', sa.String(length=255), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('resource_type', sa.String(length=50), nullable=False),
            sa.Column('resource_id', sa.String(length=64), nullable=True),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_audit_log_actor'), 'audit_log', ['actor'], unique=False)
        op.create_index(op.f('ix_audit_log_action'), 'audit_log', ['action'], unique=False)
        op.create_index(op.f('ix_audit_log_resource_type'), 'audit_log', ['resource_type'], unique=False)
        op.create_index(op.f('ix_audit_log_created_at'), 'audit_log', ['created_at'], unique=False)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('audit_log'):
        op.drop_index(op.f('ix_audit_log_created_at'), table_name='audit_log')
        op.drop_index(op.f('ix_audit_log_resource_type'), table_name='audit_log')
        op.drop_index(op.f('ix_audit_log_action'), table_name='audit_log')
        op.drop_index(op.f('ix_audit_log_actor'), table_name='audit_log')
        op.drop_table('audit_log')

    if inspector.has_table('reviews'):
        op.drop_index(op.f('ix_reviews_decision'), table_name='reviews')
        op.drop_index(op.f('ix_reviews_request_id'), table_name='reviews')
        op.drop_table('reviews')
