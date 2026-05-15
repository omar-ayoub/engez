import uuid

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Expense(Base, TimestampMixin, TenantMixin):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_company_status", "company_id", "status"),
        Index("ix_expenses_company_project", "company_id", "project_id"),
        Index("ix_expenses_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id"), nullable=True)
    category_id: Mapped[str] = mapped_column(String(36), ForeignKey("categories.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EGP")
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vendor_tax_reg: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    receipt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    voice_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    eta_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    eta_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_extraction: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_confidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    anomaly_flags: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    offline_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
