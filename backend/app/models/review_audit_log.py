import uuid

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin


class ReviewAuditLog(Base, TenantMixin):
    __tablename__ = "review_audit_logs"

    __table_args__ = (
        Index("ix_review_audit_company_expense_created", "company_id", "expense_id", "created_at"),
        Index("ix_review_audit_company_actor_created", "company_id", "actor_id", "created_at"),
        Index("ix_review_audit_company_action_created", "company_id", "action_type", "created_at"),
        Index("ix_review_audit_bulk_operation", "bulk_operation_id"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    expense_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("expenses.id"), nullable=False
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    value_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    value_after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    bulk_operation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        default=lambda: datetime.now(timezone.utc),
    )
