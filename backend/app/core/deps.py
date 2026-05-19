from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSession, get_db
from app.core.security import verify_access_token
from app.core.tenant import TenantScope
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = verify_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "غير مصرح",
                "detail_en": "Not authenticated",
            },
        )
    result = await db.execute(
        select(User).options(selectinload(User.company)).where(User.id == payload.sub)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "غير مصرح",
                "detail_en": "Not authenticated",
            },
        )
    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "الحساب غير نشط",
                "detail_en": "Account is inactive",
            },
        )
    if not user.company.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "الحساب غير نشط",
                "detail_en": "Account is inactive",
            },
        )
    return user


async def require_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "غير مسموح",
                "detail_en": "Not authorized",
            },
        )
    return user


async def require_accountant_or_admin(
    user: User = Depends(get_current_active_user),
) -> User:
    if user.role not in ("accountant", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "detail": "صلاحية المحاسب أو المدير مطلوبة",
                "detail_en": "Accountant or admin role required",
            },
        )
    return user


def get_tenant_scope(user: User = Depends(get_current_active_user)) -> TenantScope:
    return TenantScope(user.company_id)
