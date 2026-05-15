from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    name_ar: str
    code: str
    budget: Decimal | None = None


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str
    code: str
    budget: Decimal | None
    is_active: bool
    created_at: datetime


class ProjectUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    budget: Decimal | None = None
    is_active: bool | None = None


class PaginatedProjects(BaseModel):
    items: list[ProjectRead]
    total: int
    page: int
    per_page: int
