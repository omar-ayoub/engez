"""Dev seed script: creates all tables and inserts test users via ORM."""
import asyncio

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.base import Base
from app.models.company import Company
from app.models.user import User
from app.models.category import Category
from app.models.project import Project
import app.models  # noqa: F401 — ensures all models registered


async def main():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    # Create all tables from SQLAlchemy models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tables created.")

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Company
        company = (await session.execute(
            select(Company).where(Company.id == "comp-001")
        )).scalar_one_or_none()
        if not company:
            company = Company(id="comp-001", name="Test Corp", name_ar="شركة تجربة")
            session.add(company)
            await session.flush()
            print("Created company comp-001")

        # Categories
        existing_cat = (await session.execute(
            select(Category).where(Category.id == "cat-materials")
        )).scalar_one_or_none()
        if not existing_cat:
            for i, (cid, name, name_ar) in enumerate([
                ("cat-materials", "Materials", "مواد"),
                ("cat-transport", "Transport", "نقل"),
                ("cat-food", "Food", "طعام"),
                ("cat-tools", "Tools", "أدوات"),
            ]):
                session.add(Category(
                    id=cid, name=name, name_ar=name_ar,
                    sort_order=i, company_id="comp-001",
                ))
            await session.flush()
            print("Created 4 categories")

        # Project
        existing_proj = (await session.execute(
            select(Project).where(Project.id == "proj-001")
        )).scalar_one_or_none()
        if not existing_proj:
            session.add(Project(
                id="proj-001", name="Site Alpha", name_ar="موقع ألفا",
                code="ALPHA", company_id="comp-001",
            ))
            await session.flush()
            print("Created project proj-001")

        # Users
        credentials = [
            ("admin-001", "admin@engez.app", "Admin", "مدير", "admin123", "admin"),
            ("user-001", "worker@engez.app", "Worker", "عامل", "worker123", "field_worker"),
            ("acct-001", "accountant@engez.app", "Accountant", "محاسب", "accountant123", "accountant"),
        ]
        for uid, email, name, name_ar, password, role in credentials:
            user = (await session.execute(
                select(User).where(User.id == uid)
            )).scalar_one_or_none()
            pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            if user:
                user.hashed_password = pw_hash
            else:
                session.add(User(
                    id=uid, email=email, name=name, name_ar=name_ar,
                    hashed_password=pw_hash, role=role, company_id="comp-001",
                ))
            print(f"  User {email} ({role}) ready")

        await session.commit()

    await engine.dispose()
    print("\nSeed complete! Test credentials:")
    print("  Admin:      admin@engez.app / admin123")
    print("  Worker:     worker@engez.app / worker123")
    print("  Accountant: accountant@engez.app / accountant123")


if __name__ == "__main__":
    asyncio.run(main())
