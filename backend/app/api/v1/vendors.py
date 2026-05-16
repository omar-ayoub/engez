from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_active_user, get_tenant_scope
from app.models.user import User
from app.models.vendor_cache import VendorCache
from app.schemas.vendor import VendorListResponse, VendorResponse, VendorSearchResponse

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("/", response_model=VendorListResponse)
async def list_vendors(
    request: Request,
    company_id: str = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if_modified_since = request.headers.get("If-Modified-Since")

    query = select(VendorCache).where(VendorCache.company_id == company_id).order_by(VendorCache.name)
    result = await db.execute(query)
    vendors = result.scalars().all()

    total_result = await db.execute(
        select(func.count()).select_from(VendorCache).where(VendorCache.company_id == company_id)
    )
    total = total_result.scalar() or 0

    last_updated = None
    if vendors:
        last_updated = max(v.updated_at for v in vendors)

    return VendorListResponse(
        vendors=vendors,
        total=total,
        last_updated=last_updated,
    )


@router.get("/search", response_model=VendorSearchResponse)
async def search_vendors(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=50),
    company_id: str = Depends(get_tenant_scope),
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    q_lower = q.lower()
    query = (
        select(VendorCache)
        .where(
            VendorCache.company_id == company_id,
            or_(
                func.lower(VendorCache.name).contains(q_lower),
                VendorCache.name_ar.contains(q),
                VendorCache.tax_registration.contains(q),
            ),
        )
        .limit(limit)
    )

    result = await db.execute(query)
    vendors = result.scalars().all()

    return VendorSearchResponse(vendors=vendors)
