"""
Authentication Schemas
======================
Pydantic models that validate request/response data for auth endpoints.

Why Pydantic schemas?
- Automatic input validation (email format, password length, etc.)
- Automatic API documentation in Swagger UI
- Type safety — catches errors before they reach the database
- Clear contract between frontend and backend
"""

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime


class UserRegister(BaseModel):
    """Request body for POST /api/auth/register"""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Request body for POST /api/auth/login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Response for user data (never includes password)"""
    id: UUID
    email: str
    full_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Response for POST /api/auth/login"""
    access_token: str
    token_type: str = "bearer"
