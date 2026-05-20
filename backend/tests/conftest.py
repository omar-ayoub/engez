import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from unittest.mock import AsyncMock as _AsyncMock
from app.core.security import create_access_token


def _fake_hash(password: str) -> str:
    import hashlib
    return f"$2b$12$fakehash{hashlib.sha256(password.encode()).hexdigest()[:40]}"


HASHED_PASSWORD = _fake_hash("password123")
HASHED_ADMIN = _fake_hash("admin123")
from app.models.base import Base
from app.models.company import Company
from app.models.user import User
from app.models.category import Category
from app.models.project import Project
from app.models.vendor_cache import VendorCache
from app.models.expense import Expense
from app.main import app


DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(DATABASE_URL, echo=False)

from sqlalchemy.dialects.postgresql import JSONB as PgJSONB
from sqlalchemy import JSON, text as sa_text
from sqlalchemy.sql.elements import TextClause


for table in Base.metadata.sorted_tables:
    for column in table.columns:
        if isinstance(column.type, PgJSONB):
            column.type = JSON()
        if column.server_default is not None:
            srv = column.server_default
            if hasattr(srv, "arg") and isinstance(srv.arg, TextClause):
                if "now()" in str(srv.arg):
                    from sqlalchemy.schema import ColumnDefault
                    column.default = ColumnDefault(lambda: datetime.now(timezone.utc))
                    column.server_default = None

TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)




@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await test_engine.dispose()
    test_db = Path("./test.db")
    if test_db.exists():
        test_db.unlink()


@pytest_asyncio.fixture(scope="session")
async def db_session():
    async with TestSessionFactory() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def seed_data(db_session: AsyncSession):
    company = Company(
        id="comp-001",
        name="Test Company",
        name_ar="شركة اختبار",
        is_active=True,
    )
    db_session.add(company)
    await db_session.flush()

    user = User(
        id="user-001",
        email="test@engez.app",
        name="Test User",
        name_ar="مستخدم اختبار",
        hashed_password=HASHED_PASSWORD,
        role="field_worker",
        is_active=True,
        company_id=company.id,
    )
    db_session.add(user)
    await db_session.flush()

    admin = User(
        id="admin-001",
        email="admin@engez.app",
        name="Admin User",
        name_ar="مدير",
        hashed_password=HASHED_ADMIN,
        role="admin",
        is_active=True,
        company_id=company.id,
    )
    db_session.add(admin)
    await db_session.flush()

    category = Category(
        id="cat-001",
        name="materials",
        name_ar="مواد",
        company_id=company.id,
        is_active=True,
    )
    db_session.add(category)
    await db_session.flush()

    project = Project(
        id="proj-001",
        name="Tower A",
        name_ar="برج أ",
        code="TA",
        is_active=True,
        company_id=company.id,
    )
    db_session.add(project)
    await db_session.flush()

    vendor = VendorCache(
        id="vendor-001",
        name="Cement Egypt",
        name_ar="أسمنت مصر",
        tax_registration="123456789",
        category_hint="materials",
        company_id=company.id,
    )
    db_session.add(vendor)
    await db_session.flush()

    await db_session.commit()

    accountant = User(
        id="accountant-001",
        email="accountant@engez.app",
        name="Accountant User",
        name_ar="محاسب",
        hashed_password=_fake_hash("accountant123"),
        role="accountant",
        is_active=True,
        company_id=company.id,
    )
    db_session.add(accountant)
    await db_session.flush()

    await db_session.commit()

    return {
        "company": company,
        "user": user,
        "admin": admin,
        "accountant": accountant,
        "category": category,
        "project": project,
        "vendor": vendor,
    }


@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession, seed_data):
    token = create_access_token(
        user_id=seed_data["user"].id,
        company_id=seed_data["company"].id,
        role=seed_data["user"].role,
    )

    async def override_get_db():
        yield db_session

    from app.core.deps import get_current_active_user, get_tenant_scope
    from app.core.database import get_db
    from app.core.tenant import TenantScope

    app.dependency_overrides[get_current_active_user] = lambda: seed_data["user"]
    app.dependency_overrides[get_tenant_scope] = lambda: TenantScope(seed_data["company"].id)
    app.dependency_overrides[get_db] = override_get_db

    from unittest.mock import patch as _patch
    import app.api.v1.voice as _voice_router
    import app.api.v1.receipts as _receipt_router

    _voice_router.check_rate_limit = _AsyncMock()
    _receipt_router.check_rate_limit = _AsyncMock()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def accountant_client(db_session: AsyncSession, seed_data):
    token = create_access_token(
        user_id=seed_data["accountant"].id,
        company_id=seed_data["company"].id,
        role=seed_data["accountant"].role,
    )

    async def override_get_db():
        yield db_session

    from app.core.deps import get_current_active_user, get_tenant_scope
    from app.core.database import get_db
    from app.core.tenant import TenantScope

    app.dependency_overrides[get_current_active_user] = lambda: seed_data["accountant"]
    app.dependency_overrides[get_tenant_scope] = lambda: TenantScope(seed_data["company"].id)
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(db_session: AsyncSession, seed_data):
    token = create_access_token(
        user_id=seed_data["admin"].id,
        company_id=seed_data["company"].id,
        role=seed_data["admin"].role,
    )

    async def override_get_db():
        yield db_session

    from app.core.deps import get_current_active_user, get_tenant_scope
    from app.core.database import get_db
    from app.core.tenant import TenantScope

    app.dependency_overrides[get_current_active_user] = lambda: seed_data["admin"]
    app.dependency_overrides[get_tenant_scope] = lambda: TenantScope(seed_data["company"].id)
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.headers["Authorization"] = f"Bearer {token}"
        yield client

    app.dependency_overrides.clear()
