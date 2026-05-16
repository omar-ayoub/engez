import uuid

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class VendorCache(Base, TimestampMixin, TenantMixin):
    __tablename__ = "vendor_cache"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "tax_registration", name="uq_vendor_company_tax"
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tax_registration: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_ar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_hint: Mapped[str | None] = mapped_column(String(100), nullable=True)
