"""initial_tables

Revision ID: d8ef9e277c02
Revises: 
Create Date: 2026-06-16 13:02:11.294960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'd8ef9e277c02'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table('traces'):
        op.create_table(
            'traces',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('request_id', sa.String(length=64), nullable=False),
            sa.Column('project_name', sa.String(length=255), nullable=False),
            sa.Column('prompt', sa.Text(), nullable=False),
            sa.Column('response', sa.Text(), nullable=False),
            sa.Column('model_name', sa.String(length=255), nullable=False),
            sa.Column('total_tokens', sa.Integer(), nullable=False, server_default=sa.text('0')),
            sa.Column('cost', sa.Numeric(12, 6), nullable=False, server_default=sa.text('0')),
            sa.Column('latency_ms', sa.Float(), nullable=False),
            sa.Column('status', sa.String(length=20), nullable=False),
            sa.Column('flagged_for_governance', sa.Boolean(), nullable=False, server_default=sa.text('0')),
            sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('traces', schema=None) as batch_op:
            batch_op.create_index('ix_traces_project_name', ['project_name'])
            batch_op.create_index('ix_traces_request_id', ['request_id'], unique=True)
            batch_op.create_index('ix_traces_status', ['status'])
            batch_op.create_index('ix_traces_timestamp', ['timestamp'])

    if not inspector.has_table('api_keys'):
        op.create_table(
            'api_keys',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('key_prefix', sa.String(length=24), nullable=False),
            sa.Column('key_hash', sa.String(length=128), nullable=False),
            sa.Column('role', sa.String(length=20), nullable=False),
            sa.Column('project_scope', sa.String(length=255), nullable=True),
            sa.Column('description', sa.String(length=255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('api_keys', schema=None) as batch_op:
            batch_op.create_index('ix_api_keys_created_at', ['created_at'])
            batch_op.create_index('ix_api_keys_key_hash', ['key_hash'], unique=True)
            batch_op.create_index('ix_api_keys_key_prefix', ['key_prefix'])
            batch_op.create_index('ix_api_keys_project_scope', ['project_scope'])
            batch_op.create_index('ix_api_keys_role', ['role'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if inspector.has_table('api_keys'):
        with op.batch_alter_table('api_keys', schema=None) as batch_op:
            batch_op.drop_index('ix_api_keys_role')
            batch_op.drop_index('ix_api_keys_project_scope')
            batch_op.drop_index('ix_api_keys_key_prefix')
            batch_op.drop_index('ix_api_keys_key_hash')
            batch_op.drop_index('ix_api_keys_created_at')
        op.drop_table('api_keys')

    if inspector.has_table('traces'):
        with op.batch_alter_table('traces', schema=None) as batch_op:
            batch_op.drop_index('ix_traces_timestamp')
            batch_op.drop_index('ix_traces_status')
            batch_op.drop_index('ix_traces_request_id')
            batch_op.drop_index('ix_traces_project_name')
        op.drop_table('traces')
