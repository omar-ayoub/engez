from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Literal


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    name_ar: str
    password: str = Field(min_length=8)
    role: Literal["field_worker", "accountant", "admin"]


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    name_ar: str
    role: str
    is_active: bool
    created_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    role: str | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)


class PaginatedUsers(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    per_page: int
