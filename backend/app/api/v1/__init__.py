from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.users import router as users_router
from app.api.v1.projects import router as projects_router
from app.api.v1.categories import router as categories_router
from app.api.v1.expenses import router as expenses_router
from app.api.v1.voice import router as voice_router
from app.api.v1.receipts import router as receipts_router
from app.api.v1.vendors import router as vendors_router
from app.api.v1.review import router as review_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.anomalies import router as anomalies_router
from app.api.v1.analytics import router as analytics_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(users_router)
v1_router.include_router(projects_router)
v1_router.include_router(categories_router)
v1_router.include_router(expenses_router)
v1_router.include_router(voice_router)
v1_router.include_router(receipts_router)
v1_router.include_router(vendors_router)
v1_router.include_router(review_router)
v1_router.include_router(notifications_router)
v1_router.include_router(integrations_router)
v1_router.include_router(anomalies_router)
v1_router.include_router(analytics_router)
