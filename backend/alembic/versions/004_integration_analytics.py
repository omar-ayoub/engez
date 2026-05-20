"""add integration_configs and export_records tables, expense receipt_hash index

Revision ID: 004_integration_analytics
Revises: 003_review_desk
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = '004_integration_analytics'
down_revision = '003_review_desk'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'integration_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('company_id', sa.String(36), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('system_name', sa.String(50), nullable=False),
        sa.Column('encrypted_credentials', sa.Text, nullable=False),
        sa.Column('oauth_refresh_token', sa.Text, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('field_mappings', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('uq_integration_company', 'integration_configs', ['company_id'], unique=True)
    op.create_index(op.f('ix_integration_configs_company_id'), 'integration_configs', ['company_id'])

    op.create_table(
        'export_records',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('company_id', sa.String(36), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('expense_id', sa.String(36), nullable=False),
        sa.Column('system_name', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending'),
        sa.Column('external_ref_id', sa.String(255), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_exports_company_status', 'export_records', ['company_id', 'status'])
    op.create_index('ix_exports_expense', 'export_records', ['expense_id'])
    op.create_index('ix_exports_retry', 'export_records', ['status', 'next_retry_at'])
    op.create_index(op.f('ix_export_records_company_id'), 'export_records', ['company_id'])

    op.create_index('ix_expenses_company_receipt_hash', 'expenses', ['company_id', 'receipt_hash'])


def downgrade() -> None:
    op.drop_index('ix_expenses_company_receipt_hash', table_name='expenses')
    op.drop_table('export_records')
    op.drop_table('integration_configs')
