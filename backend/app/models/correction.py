import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class CorrectionFeedback(Base, TimestampMixin, TenantMixin):
    __tablename__ = "correction_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    expense_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("expenses.id"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(50), nullable=False)
    ai_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_value: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
