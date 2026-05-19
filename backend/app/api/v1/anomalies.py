
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_tenant_scope, require_admin, require_accountant_or_admin
from app.core.tenant import TenantScope
from app.models.user import User
from app.schemas.integration import AnomalyCheckRequest
from app.services.anomaly import check_anomalies_from_request, get_anomaly_metrics

router = APIRouter(prefix="", tags=["anomalies"])


@router.post("/expenses/check-anomalies")
async def check_anomalies(
    body: AnomalyCheckRequest,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if not body.user_id:
        body.user_id = user.id
    flags = await check_anomalies_from_request(db, body, scope.company_id)
    return {
        "flags": flags,
        "blocking": False,
    }


@router.get("/anomalies/metrics")
async def anomaly_metrics(
    days: int = Query(30, ge=1, le=365),
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await get_anomaly_metrics(db, scope.company_id, days)
