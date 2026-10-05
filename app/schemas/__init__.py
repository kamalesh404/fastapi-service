"""
Pydantic schemas for request/response validation.

All schemas follow strict validation with clear documentation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        str_strip_whitespace=True,
        json_schema_extra={},
    )


# =============================================================================
# Pagination
# =============================================================================

class PageParams(BaseSchema):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


class PageInfo(BaseSchema):
    """Pagination metadata."""

    page: int
    size: int
    total: int
    pages: int

    @classmethod
    def create(cls, page: int, size: int, total: int) -> "PageInfo":
        return cls(
            page=page,
            size=size,
            total=total,
            pages=(total + size - 1) // size if size > 0 else 0,
        )


class PaginatedResponse(BaseSchema):
    """Generic paginated response."""

    items: List[Any]
    page_info: PageInfo


# =============================================================================
# Error Responses
# =============================================================================

class ErrorDetail(BaseSchema):
    """Error detail structure."""

    code: str
    message: str
    field: Optional[str] = None


class ErrorResponse(BaseSchema):
    """Standard error response."""

    success: bool = False
    error: ErrorDetail
    details: Optional[List[ErrorDetail]] = None


# =============================================================================
# Success Responses
# =============================================================================

class MessageResponse(BaseSchema):
    """Simple success message response."""

    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# =============================================================================
# Token Schemas
# =============================================================================

class TokenData(BaseSchema):
    """Decoded JWT token data."""

    sub: str
    scopes: List[str] = []


class TokenResponse(BaseSchema):
    """Token response with access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseSchema):
    """Refresh token request."""

    refresh_token: str


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseSchema):
    """Base user fields."""

    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=100, description="Username")
    full_name: Optional[str] = Field(None, max_length=200, description="Full name")
    bio: Optional[str] = Field(None, max_length=500, description="Bio")
    avatar_url: Optional[str] = Field(None, max_length=500, description="Avatar URL")


class UserCreate(UserBase):
    """User registration request."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (min 8 chars)",
    )
    password_confirm: str = Field(..., description="Password confirmation")

    def passwords_match(self) -> bool:
        return self.password == self.password_confirm


class UserUpdate(BaseSchema):
    """User profile update request."""

    full_name: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=500)
    avatar_url: Optional[str] = Field(None, max_length=500)
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)


class UserChangePassword(BaseSchema):
    """Password change request."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    new_password_confirm: str = Field(..., description="New password confirmation")

    def passwords_match(self) -> bool:
        return self.new_password == self.new_password_confirm


class UserResponse(BaseSchema):
    """User response with all public fields."""

    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    role: str
    status: str
    is_verified: bool
    is_2fa_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]


class UserListResponse(BaseSchema):
    """User list item (minimal fields)."""

    id: int
    email: EmailStr
    username: str
    full_name: Optional[str]
    role: str
    status: str
    is_verified: bool
    created_at: datetime


# =============================================================================
# Auth Schemas
# =============================================================================

class LoginRequest(BaseSchema):
    """Login request with username/email and password."""

    identifier: str = Field(..., description="Email or username")
    password: str = Field(..., description="Password")
    remember_me: bool = Field(default=False, description="Extend refresh token expiry")


class RegisterRequest(UserCreate):
    """User registration request (alias for UserCreate)."""


class ForgotPasswordRequest(BaseSchema):
    """Password reset request."""

    email: EmailStr = Field(..., description="User email")


class ResetPasswordRequest(BaseSchema):
    """Password reset confirmation."""

    token: str = Field(..., description="Reset token from email")
    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(...)

    def passwords_match(self) -> bool:
        return self.password == self.password_confirm


class VerifyEmailRequest(BaseSchema):
    """Email verification request."""

    token: str = Field(..., description="Verification token from email")


class ResendVerificationRequest(BaseSchema):
    """Resend verification email request."""

    email: EmailStr = Field(..., description="User email")


# =============================================================================
# OAuth2 Schemas
# =============================================================================

class OAuth2Provider(str, BaseSchema):
    """OAuth2 provider enum."""

    GOOGLE = "google"
    GITHUB = "github"


class OAuth2LoginRequest(BaseSchema):
    """OAuth2 login request."""

    provider: OAuth2Provider
    code: str = Field(..., description="Authorization code from provider")
    redirect_uri: str = Field(..., description="Redirect URI used in auth flow")


# =============================================================================
# Item Schemas
# =============================================================================

class ItemBase(BaseSchema):
    """Base item fields."""

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list)
    category: Optional[str] = Field(None, max_length=100)
    is_public: bool = False


class ItemCreate(ItemBase):
    """Item creation request."""

    pass


class ItemUpdate(BaseSchema):
    """Item update request."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    category: Optional[str] = Field(None, max_length=100)
    is_public: Optional[bool] = None
    is_featured: Optional[bool] = None


class ItemResponse(BaseSchema):
    """Item response with all fields."""

    id: int
    title: str
    description: Optional[str]
    content: Optional[str]
    tags: List[str]
    category: Optional[str]
    is_active: bool
    is_public: bool
    is_featured: bool
    view_count: int
    like_count: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime]


class ItemListResponse(BaseSchema):
    """Item list item (minimal fields)."""

    id: int
    title: str
    description: Optional[str]
    category: Optional[str]
    is_public: bool
    is_featured: bool
    owner_id: int
    created_at: datetime


# =============================================================================
# Health Check
# =============================================================================

class HealthResponse(BaseSchema):
    """Health check response."""

    status: str
    version: str
    environment: str
    timestamp: datetime
    checks: Dict[str, str]


# =============================================================================
# WebSocket Schemas
# =============================================================================

class WSMessage(BaseSchema):
    """WebSocket message envelope."""

    type: str
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WSSubscribe(BaseSchema):
    """WebSocket subscription request."""

    channels: List[str]


class WSNotification(BaseSchema):
    """WebSocket notification payload."""

    title: str
    message: str
    level: str = "info"  # info, warning, error, success
    action_url: Optional[str] = None
    action_text: Optional[str] = None


# Import timezone for datetime default
from datetime import timezone