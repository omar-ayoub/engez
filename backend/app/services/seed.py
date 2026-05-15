import asyncio
import uuid

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_factory, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.category import Category
from app.models.company import Company
from app.models.user import User

DEFAULT_CATEGORIES = [
    ("مواد بناء", "Building Materials"),
    ("نقل ومواصلات", "Transportation"),
    ("عمالة", "Labor"),
    ("طعام وشراب", "Food & Beverage"),
    ("معدات", "Equipment"),
    ("إيجار", "Rent"),
    ("مرافق", "Utilities"),
    ("متنوعة", "Miscellaneous"),
]


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.email == settings.SEED_ADMIN_EMAIL)
        )
        if result.scalar_one_or_none():
            print("Seed data already exists. Skipping.")
            return

        company = Company(
            id=str(uuid.uuid4()),
            name="ENGEZ Demo",
            name_ar="إنجز ديمو",
            is_active=True,
            settings={},
        )
        db.add(company)
        await db.flush()

        admin = User(
            id=str(uuid.uuid4()),
            email=settings.SEED_ADMIN_EMAIL,
            name="Admin",
            name_ar="المدير",
            hashed_password=hash_password(settings.SEED_ADMIN_PASSWORD),
            role="admin",
            company_id=company.id,
        )
        db.add(admin)

        for i, (name_ar, name_en) in enumerate(DEFAULT_CATEGORIES):
            cat = Category(
                id=str(uuid.uuid4()),
                name=name_en,
                name_ar=name_ar,
                sort_order=i,
                company_id=company.id,
            )
            db.add(cat)

        await db.commit()
        print(f"Created company: {company.name} ({company.name_ar})")
        print(f"Created admin: {admin.email}")
        print(f"Created {len(DEFAULT_CATEGORIES)} categories")


if __name__ == "__main__":
    asyncio.run(main())
