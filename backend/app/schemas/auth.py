from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.LAYMAN


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    onboarding_complete: bool


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    pan: str | None
    gstin: str | None
    onboarding_complete: bool

    class Config:
        from_attributes = True
