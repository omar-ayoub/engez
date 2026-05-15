from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, require_admin
from app.core.database import get_db
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyRead, CompanyUpdate

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/me", response_model=CompanyRead)
async def get_my_company(
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    company = result.scalar_one()
    return company


@router.patch("/me", response_model=CompanyRead)
async def update_my_company(
    body: CompanyUpdate,
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == user.company_id))
    company = result.scalar_one()

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)
    return company
