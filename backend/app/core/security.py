from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    sub: str
    company_id: str
    role: str
    exp: datetime


class RefreshPayload(BaseModel):
    sub: str
    exp: datetime


def create_access_token(user_id: str, company_id: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "company_id": company_id,
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return TokenPayload(
            sub=payload["sub"],
            company_id=payload["company_id"],
            role=payload["role"],
            exp=payload["exp"],
        )
    except (JWTError, KeyError) as e:
        raise ValueError(f"Invalid access token: {e}") from e


def verify_refresh_token(token: str) -> RefreshPayload:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        return RefreshPayload(sub=payload["sub"], exp=payload["exp"])
    except (JWTError, KeyError) as e:
        raise ValueError(f"Invalid refresh token: {e}") from e


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())
