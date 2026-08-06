from datetime import datetime
from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    fcm_token: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True

class FCMTokenUpdate(BaseModel):
    fcm_token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
