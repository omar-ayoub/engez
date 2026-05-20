from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_refresh_token,
)
from app.models.user import User


class AuthService:
    @staticmethod
    async def authenticate_user(db, email: str, password: str) -> User:
        result = await db.execute(
            select(User)
            .options(selectinload(User.company))
            .where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
                    "detail_en": "Invalid email or password",
                },
            )

        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={
                    "detail": "تم تأمين الحساب. حاول مرة أخرى بعد 15 دقيقة",
                    "detail_en": "Account locked. Try again in 15 minutes",
                    "locked_until": user.locked_until.isoformat(),
                },
            )

        if not verify_password(password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "البريد الإلكتروني أو كلمة المرور غير صحيحة",
                    "detail_en": "Invalid email or password",
                },
            )

        user.failed_login_attempts = 0
        user.locked_until = None
        await db.commit()
        return user

    @staticmethod
    async def create_tokens(user: User) -> dict:
        access_token = create_access_token(
            user_id=user.id,
            company_id=user.company_id,
            role=user.role,
        )
        refresh_token = create_refresh_token(user_id=user.id)
        return {"access_token": access_token, "refresh_token": refresh_token}

    @staticmethod
    async def refresh_access_token(db, refresh_token_str: str) -> dict:
        try:
            payload = verify_refresh_token(refresh_token_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى",
                    "detail_en": "Session expired. Please log in again",
                },
            )

        result = await db.execute(
            select(User)
            .options(selectinload(User.company))
            .where(User.id == payload.sub)
        )
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "detail": "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى",
                    "detail_en": "Session expired. Please log in again",
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

        access_token = create_access_token(
            user_id=user.id,
            company_id=user.company_id,
            role=user.role,
        )
        return {"access_token": access_token}
