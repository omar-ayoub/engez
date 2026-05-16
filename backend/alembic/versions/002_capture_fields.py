"""add capture fields to expenses

Revision ID: 002_capture_fields
Revises: 
Create Date: 2026-05-15

"""
from alembic import op
import sqlalchemy as sa


revision = '002_capture_fields'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('items', sa.Text(), server_default='', nullable=False))
    op.add_column('expenses', sa.Column('capture_mode', sa.String(20), server_default='manual', nullable=False))
    op.add_column('expenses', sa.Column('voice_url', sa.String(500), nullable=True))
    op.alter_column('expenses', 'category_id', existing_type=sa.String(36), nullable=True)


def downgrade() -> None:
    op.alter_column('expenses', 'category_id', existing_type=sa.String(36), nullable=False)
    op.drop_column('expenses', 'voice_url')
    op.drop_column('expenses', 'capture_mode')
    op.drop_column('expenses', 'items')
