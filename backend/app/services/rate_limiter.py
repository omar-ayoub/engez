import logging

import redis.asyncio as aioredis

from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_rate_limit(
    company_id: str,
    endpoint: str,
    limit: int = 100,
    window_seconds: int = 3600,
) -> None:
    r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        key = f"ratelimit:{company_id}:{endpoint}:{window_seconds}"
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, window_seconds)
        if current > limit:
            logger.warning(
                "Rate limit exceeded for company=%s endpoint=%s (%d/%d)",
                company_id, endpoint, current, limit,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "detail": "تم تجاوز حد الاستخدام. يرجى المحاولة لاحقاً",
                    "detail_en": "Rate limit exceeded. Please try again later",
                    "retry_after": window_seconds,
                },
            )
    finally:
        await r.aclose()
