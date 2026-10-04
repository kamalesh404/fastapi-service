"""Pydantic schemas for FastAPI request/response validation."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


# User schemas
class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    password: str = Field(..., min_length=8, description="User password")


class UserResponse(BaseModel):
    """Schema for user response."""

    id: int
    email: EmailStr
    username: str
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Item schemas
class ItemCreate(BaseModel):
    """Schema for creating a new item."""

    title: str = Field(..., min_length=1, max_length=200, description="Item title")
    description: Optional[str] = Field(None, max_length=500, description="Item description")
    owner_id: int = Field(..., description="Item owner ID")


class ItemResponse(BaseModel):
    """Schema for item response."""

    id: int
    title: str
    description: Optional[str]
    owner_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True