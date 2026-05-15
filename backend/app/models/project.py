import uuid

from sqlalchemy import Boolean, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class Project(Base, TimestampMixin, TenantMixin):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_project_company_code"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    budget: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
