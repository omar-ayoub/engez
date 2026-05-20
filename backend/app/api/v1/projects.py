from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_tenant_scope, require_admin
from app.core.database import get_db
from app.core.tenant import TenantScope
from app.models.project import Project
from app.models.user import User
from app.schemas.project import PaginatedProjects, ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=PaginatedProjects)
async def list_projects(
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project).where(Project.company_id == scope.company_id)
    count_query = select(func.count()).select_from(Project).where(Project.company_id == scope.company_id)

    if is_active is not None:
        query = query.where(Project.is_active == is_active)
        count_query = count_query.where(Project.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    projects = result.scalars().all()

    return PaginatedProjects(items=projects, total=total, page=page, per_page=per_page)


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(Project).where(
            Project.company_id == scope.company_id, Project.code == body.code
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "detail": "كود المشروع مستخدم بالفعل",
                "detail_en": "Project code already exists",
            },
        )

    project = Project(
        name=body.name,
        name_ar=body.name_ar,
        code=body.code,
        budget=body.budget,
        company_id=scope.company_id,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    scope: TenantScope = Depends(get_tenant_scope),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.company_id == scope.company_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"detail": "المشروع غير موجود", "detail_en": "Project not found"},
        )

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project
