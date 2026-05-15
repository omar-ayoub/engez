from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.users import router as users_router
from app.api.v1.projects import router as projects_router
from app.api.v1.categories import router as categories_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(auth_router)
v1_router.include_router(companies_router)
v1_router.include_router(users_router)
v1_router.include_router(projects_router)
v1_router.include_router(categories_router)
