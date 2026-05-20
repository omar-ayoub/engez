"""review desk: expense review columns, audit table, indexes, trigger

Revision ID: 003_review_desk
Revises: 002_capture_fields
Create Date: 2026-05-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = '003_review_desk'
down_revision = '002_capture_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('expenses', sa.Column('review_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('expenses', sa.Column('reviewed_by', sa.String(36), nullable=True))
    op.add_column('expenses', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key(
        'fk_expenses_reviewed_by_users',
        'expenses', 'users',
        ['reviewed_by'], ['id'],
    )

    op.create_index('ix_expenses_review_queue', 'expenses', ['company_id', 'status', 'created_at'])
    op.create_index('ix_expenses_company_amount', 'expenses', ['company_id', 'amount'])
    op.create_index('ix_expenses_company_employee', 'expenses', ['company_id', 'user_id', 'created_at'])
    op.create_index('ix_expenses_company_status_project_date', 'expenses', ['company_id', 'status', 'project_id', 'created_at'])

    op.create_index('ix_correction_feedback_company_field_created', 'correction_feedback', ['company_id', 'field_name', 'created_at'])
    op.create_index('ix_correction_feedback_company_expense', 'correction_feedback', ['company_id', 'expense_id'])

    op.create_table(
        'review_audit_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('company_id', sa.String(36), sa.ForeignKey('companies.id'), nullable=False),
        sa.Column('expense_id', sa.String(36), sa.ForeignKey('expenses.id'), nullable=False),
        sa.Column('actor_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action_type', sa.String(30), nullable=False),
        sa.Column('field_name', sa.String(50), nullable=True),
        sa.Column('value_before', JSONB(), nullable=True),
        sa.Column('value_after', JSONB(), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('bulk_operation_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_index('ix_review_audit_company_expense_created', 'review_audit_logs', ['company_id', 'expense_id', 'created_at'])
    op.create_index('ix_review_audit_company_actor_created', 'review_audit_logs', ['company_id', 'actor_id', 'created_at'])
    op.create_index('ix_review_audit_company_action_created', 'review_audit_logs', ['company_id', 'action_type', 'created_at'])
    op.create_index('ix_review_audit_bulk_operation', 'review_audit_logs', ['bulk_operation_id'])

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_review_audit_log_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'review_audit_logs are append-only';
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;

        CREATE TRIGGER trg_prevent_audit_update
            BEFORE UPDATE ON review_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_review_audit_log_mutation();

        CREATE TRIGGER trg_prevent_audit_delete
            BEFORE DELETE ON review_audit_logs
            FOR EACH ROW EXECUTE FUNCTION prevent_review_audit_log_mutation();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_delete ON review_audit_logs")
    op.execute("DROP TRIGGER IF EXISTS trg_prevent_audit_update ON review_audit_logs")
    op.execute("DROP FUNCTION IF EXISTS prevent_review_audit_log_mutation()")

    op.drop_table('review_audit_logs')

    op.drop_index('ix_correction_feedback_company_expense', 'correction_feedback')
    op.drop_index('ix_correction_feedback_company_field_created', 'correction_feedback')

    op.drop_index('ix_expenses_company_status_project_date', 'expenses')
    op.drop_index('ix_expenses_company_employee', 'expenses')
    op.drop_index('ix_expenses_company_amount', 'expenses')
    op.drop_index('ix_expenses_review_queue', 'expenses')

    op.drop_constraint('fk_expenses_reviewed_by_users', 'expenses', type_='foreignkey')

    op.drop_column('expenses', 'reviewed_at')
    op.drop_column('expenses', 'reviewed_by')
    op.drop_column('expenses', 'review_version')
