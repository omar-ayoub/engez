from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    name_ar: str
    sort_order: int = 0


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    name_ar: str
    sort_order: int
    is_active: bool


class CategoryUpdate(BaseModel):
    name: str | None = None
    name_ar: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryListResponse(BaseModel):
    items: list[CategoryRead]
