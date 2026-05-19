import uuid

from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin


class IntegrationConfig(Base, TimestampMixin, TenantMixin):
    __tablename__ = "integration_configs"
    __table_args__ = (
        Index("uq_integration_company", "company_id", unique=True),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    system_name: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_credentials: Mapped[str] = mapped_column(Text, nullable=False)
    oauth_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_mappings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
