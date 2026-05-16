from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.deps import get_current_active_user
from app.core.database import AsyncSession, get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshResponse,
    UserInfo,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_MAX_AGE = 7 * 24 * 3600


class WebAuthnRegisterRequest(BaseModel):
    credential_id: str
    public_key: str
    attestation: str


class WebAuthnAuthenticateRequest(BaseModel):
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str


def _set_refresh_cookie(response: Response, request: Request, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        httponly=True,
        secure=request.url.scheme == "https",
        samesite="strict",
        path="/api/v1/auth",
    )


def _build_user_info(user: User) -> UserInfo:
    return UserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        name_ar=user.name_ar,
        role=user.role,
        company_id=user.company_id,
        company_name=user.company.name,
        company_name_ar=user.company.name_ar,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    user = await AuthService.authenticate_user(db, body.email, body.password)
    tokens = await AuthService.create_tokens(user)

    _set_refresh_cookie(response, request, tokens["refresh_token"])

    return LoginResponse(
        access_token=tokens["access_token"],
        user=_build_user_info(user),
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(request: Request, db: AsyncSession = Depends(get_db)):
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "detail": "انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى",
                "detail_en": "Session expired. Please log in again",
            },
        )
    result = await AuthService.refresh_access_token(db, refresh_token_str)
    return TokenRefreshResponse(access_token=result["access_token"])


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    return {"logged_out": True}


@router.post("/webauthn/register")
async def webauthn_register(
    body: WebAuthnRegisterRequest,
    user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    user.webauthn_credential_id = body.credential_id
    user.webauthn_public_key = body.public_key
    await db.commit()
    return {"registered": True}


@router.post("/webauthn/authenticate", response_model=LoginResponse)
async def webauthn_authenticate(
    body: WebAuthnAuthenticateRequest,
    db: AsyncSession = Depends(get_db),
):
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail={
            "detail": "WebAuthn غير متاح حالياً",
            "detail_en": "WebAuthn not yet available",
        },
    )
