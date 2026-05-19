from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.notification import (
    VapidPublicKeyResponse,
    PushSubscriptionRequest,
    SubscriptionUpsertResponse,
    SubscriptionDeleteResponse,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/vapid-public-key", response_model=VapidPublicKeyResponse)
async def get_vapid_public_key(
    user: User = Depends(get_current_active_user),
):
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "إشعارات الدفع غير مُعدة", "detail_en": "Push notifications not configured"},
        )
    return VapidPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@router.put("/subscription", response_model=SubscriptionUpsertResponse)
async def upsert_subscription(
    body: PushSubscriptionRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    subscription = {
        "endpoint": body.endpoint,
        "expirationTime": body.expirationTime.isoformat() if body.expirationTime else None,
        "keys": {
            "p256dh": body.keys.p256dh,
            "auth": body.keys.auth,
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    user.push_subscription = subscription
    await db.commit()
    return SubscriptionUpsertResponse(
        subscribed=True,
        updated_at=datetime.now(timezone.utc),
    )


@router.delete("/subscription", response_model=SubscriptionDeleteResponse)
async def delete_subscription(
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user.push_subscription = None
    await db.commit()
    return SubscriptionDeleteResponse(subscribed=False)
