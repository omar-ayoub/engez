from datetime import datetime

from pydantic import BaseModel


class ConfigureRequest(BaseModel):
    system_name: str
    credentials: dict
    field_mappings: dict | None = None


class IntegrationStatus(BaseModel):
    configured: bool
    system_name: str | None = None
    status: str | None = None
    last_sync_at: str | None = None
    last_error: str | None = None


class ExportRecordResponse(BaseModel):
    id: str
    expense_id: str
    system_name: str
    status: str
    external_ref_id: str | None = None
    error_message: str | None = None
    attempt_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExportListResponse(BaseModel):
    items: list[ExportRecordResponse]
    total: int
    page: int
    page_size: int


class TestConnectionResponse(BaseModel):
    success: bool
    message: str


class AvailableSystem(BaseModel):
    system_name: str
    display_name: str
    display_name_ar: str
    required_fields: list[str]


class AnomalyCheckRequest(BaseModel):
    amount: float
    currency: str = "EGP"
    vendor: str | None = None
    items: str | None = None
    capture_mode: str = "receipt"
    category_id: str | None = None
    receipt_hash: str | None = None
    user_id: str | None = None
    check_velocity: bool = False
