from datetime import datetime

from pydantic import BaseModel, Field


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str = Field(..., pattern=r"^https://")
    expirationTime: datetime | None = None
    keys: PushSubscriptionKeys


class SubscriptionUpsertResponse(BaseModel):
    subscribed: bool
    updated_at: datetime | None = None


class SubscriptionDeleteResponse(BaseModel):
    subscribed: bool
