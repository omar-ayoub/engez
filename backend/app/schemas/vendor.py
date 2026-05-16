from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str | None
    tax_registration: str | None
    category_hint: str | None


class VendorListResponse(BaseModel):
    vendors: list[VendorResponse]
    total: int
    last_updated: datetime | None = None


class VendorSearchResponse(BaseModel):
    vendors: list[VendorResponse]
