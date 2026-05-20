from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CAPTURE_MODES = Literal["voice", "receipt", "combined", "manual"]


class ExpenseCreate(BaseModel):
    offline_id: str
    amount: float = Field(gt=0)
    currency: str = "EGP"
    vendor: str
    vendor_tax_reg: str | None = None
    items: str = ""
    category_id: str | None = None
    project_id: str | None = None
    notes: str | None = None
    capture_mode: CAPTURE_MODES = "manual"
    voice_url: str | None = None
    voice_transcript: str | None = None
    receipt_url: str | None = None
    eta_uuid: str | None = None
    eta_verified: bool = False
    ai_extraction: dict | None = None
    ai_confidence: dict | None = None


class ExpenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    offline_id: str | None = None
    amount: float
    currency: str
    vendor: str | None = None
    items: str
    category_id: str | None = None
    project_id: str | None = None
    capture_mode: str
    status: str
    eta_verified: bool = False
    synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ExpenseListResponse(BaseModel):
    items: list[ExpenseResponse]
    total: int
    page: int
    per_page: int
    pages: int


class ExpensePatch(BaseModel):
    amount: float | None = None
    currency: str | None = None
    vendor: str | None = None
    vendor_tax_reg: str | None = None
    items: str | None = None
    category_id: str | None = None
    project_id: str | None = None
    notes: str | None = None
    status: str | None = None
    eta_uuid: str | None = None
    eta_verified: bool | None = None
    ai_extraction: dict | None = None
    ai_confidence: dict | None = None
