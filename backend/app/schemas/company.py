from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str
    tax_registration: str | None
    is_active: bool
    settings: dict
    created_at: datetime
    updated_at: datetime


class CompanyUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    tax_registration: str | None = None
    settings: dict | None = None
