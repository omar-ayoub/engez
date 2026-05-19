from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_tenant_scope, require_admin
from app.core.database import get_db
from app.core.tenant import TenantScope
from app.models.category import Category
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryListResponse, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=CategoryListResponse)
async def list_categories(
    is_active: bool | None = None,
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Category).where(Category.company_id == scope.company_id).order_by(Category.sort_order)
    if is_active is not None:
        query = query.where(Category.is_active == is_active)

    result = await db.execute(query)
    return CategoryListResponse(items=result.scalars().all())


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreate,
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Category).where(
            Category.company_id == scope.company_id, Category.name == body.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "اسم الفئة مستخدم بالفعل",
                "detail_en": "Category name already exists",
            },
        )

    category = Category(
        name=body.name,
        name_ar=body.name_ar,
        sort_order=body.sort_order,
        company_id=scope.company_id,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: str,
    body: CategoryUpdate,
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.company_id == scope.company_id)
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "الفئة غير موجودة", "detail_en": "Category not found"},
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)
    return category
