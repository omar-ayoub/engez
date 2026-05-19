import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_tenant_scope, require_accountant_or_admin
from app.core.tenant import TenantScope
from app.models.user import User
from app.models.integration import IntegrationConfig
from app.models.export_record import ExportRecord
from app.models.expense import Expense
from app.schemas.integration import (
    ConfigureRequest,
    ExportRecordResponse,
    ExportListResponse,
    TestConnectionResponse,
    AvailableSystem,
)
from app.services.exporters import EXPORTERS, get_exporter
from app.services.crypto import encrypt
from app.services.export_orchestrator import trigger_export, cancel_pending_exports
from app.services.exporters.csv_daftra import CsvDaftraExporter

router = APIRouter(prefix="/integrations", tags=["integrations"])

AVAILABLE_SYSTEMS = [
    AvailableSystem(
        system_name="zoho_books",
        display_name="Zoho Books",
        display_name_ar="زوهو بوكس",
        required_fields=["access_token", "organization_id", "expense_account_id"],
    ),
    AvailableSystem(
        system_name="odoo",
        display_name="Odoo",
        display_name_ar="أودو",
        required_fields=["url", "database", "uid", "password"],
    ),
    AvailableSystem(
        system_name="csv_daftra",
        display_name="Daftra (CSV)",
        display_name_ar="دفتيرا (CSV)",
        required_fields=[],
    ),
]


@router.get("/available", response_model=list[AvailableSystem])
async def list_available(
    user: User = Depends(require_accountant_or_admin),
):
    return AVAILABLE_SYSTEMS


@router.post("/configure", status_code=status.HTTP_201_CREATED)
async def configure(
    body: ConfigureRequest,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.system_name not in EXPORTERS:
        raise HTTPException(status_code=422, detail="Invalid system_name")

    existing = await db.execute(
        select(IntegrationConfig).where(IntegrationConfig.company_id == scope.company_id)
    )
    config = existing.scalar_one_or_none()

    if config and config.system_name != body.system_name:
        await cancel_pending_exports(db, scope.company_id, config.system_name)

    encrypted = encrypt(scope.company_id, json.dumps(body.credentials))

    if config:
        config.system_name = body.system_name
        config.encrypted_credentials = encrypted
        config.field_mappings = body.field_mappings
        config.status = "active"
        config.last_error = None
    else:
        config = IntegrationConfig(
            company_id=scope.company_id,
            system_name=body.system_name,
            encrypted_credentials=encrypted,
            field_mappings=body.field_mappings,
            status="active",
        )
        db.add(config)

    await db.commit()
    return {"system_name": config.system_name, "status": config.status, "last_sync_at": config.last_sync_at}


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    body: ConfigureRequest,
    user: User = Depends(require_accountant_or_admin),
):
    exporter = get_exporter(body.system_name)
    if not exporter:
        raise HTTPException(status_code=422, detail="Invalid system_name")
    success, message = await exporter.test_connection(body.credentials)
    return TestConnectionResponse(success=success, message=message)


@router.get("/status")
async def get_status(
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(IntegrationConfig).where(IntegrationConfig.company_id == scope.company_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"configured": False}
    return {
        "configured": True,
        "system_name": config.system_name,
        "status": config.status,
        "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
        "last_error": config.last_error,
    }


@router.post("/export/{expense_id}", status_code=status.HTTP_202_ACCEPTED)
async def manual_export(
    expense_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    expense_result = await db.execute(
        select(Expense).where(Expense.id == expense_id, Expense.company_id == scope.company_id)
    )
    expense = expense_result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    if expense.status != "approved":
        raise HTTPException(status_code=400, detail="Expense must be approved first")

    existing = await db.execute(
        select(ExportRecord).where(
            ExportRecord.expense_id == expense_id,
            ExportRecord.status.in_(["pending", "success"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Already exported")

    record = await trigger_export(db, expense_id, scope.company_id)
    if not record:
        raise HTTPException(status_code=400, detail="No active integration configured")
    return {"export_id": record.id, "status": record.status}


@router.post("/export/{expense_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_export(
    expense_id: str,
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExportRecord).where(
            ExportRecord.expense_id == expense_id,
            ExportRecord.company_id == scope.company_id,
            ExportRecord.status == "failed",
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="No failed export found")

    record.status = "pending"
    record.next_retry_at = None
    await db.commit()
    return {"export_id": record.id, "status": "pending", "attempt_count": record.attempt_count}


@router.get("/exports", response_model=ExportListResponse)
async def list_exports(
    status_filter: str = Query("all", alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(ExportRecord).where(ExportRecord.company_id == scope.company_id)
    count_query = select(func.count()).select_from(ExportRecord).where(ExportRecord.company_id == scope.company_id)

    if status_filter != "all":
        query = query.where(ExportRecord.status == status_filter)
        count_query = count_query.where(ExportRecord.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ExportRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    records = result.scalars().all()

    return ExportListResponse(
        items=[ExportRecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/csv-export")
async def csv_export(
    date_from: str = Query(...),
    date_to: str = Query(...),
    scope: TenantScope = Depends(get_tenant_scope),
    user: User = Depends(require_accountant_or_admin),
    db: AsyncSession = Depends(get_db),
):
    from_dt = datetime.fromisoformat(date_from).replace(hour=0, minute=0, second=0)
    to_dt = datetime.fromisoformat(date_to).replace(hour=23, minute=59, second=59)

    csv_content = await CsvDaftraExporter.generate_csv(db, scope.company_id, from_dt, to_dt)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=daftra-export-{date_from}.csv"},
    )
