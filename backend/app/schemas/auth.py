from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    email: str
    password: str


class UserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str
    name_ar: str
    role: str
    company_id: str
    company_name: str
    company_name_ar: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
