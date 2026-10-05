"""
User model with roles, permissions, and authentication fields.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class UserRole(str, enum.Enum):
    """User roles with hierarchical permissions."""

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

    def has_permission(self, required_role: "UserRole") -> bool:
        """Check if this role has at least the required role level."""
        hierarchy = {
            UserRole.USER: 0,
            UserRole.MODERATOR: 1,
            UserRole.ADMIN: 2,
            UserRole.SUPERADMIN: 3,
        }
        return hierarchy[self] >= hierarchy[required_role]


class UserStatus(str, enum.Enum):
    """User account status."""

    PENDING = "pending"          # Email not verified
    ACTIVE = "active"            # Normal active user
    SUSPENDED = "suspended"      # Temporarily disabled
    BANNED = "banned"            # Permanently banned
    DELETED = "deleted"          # Soft deleted


class User(Base):
    """
    User model with authentication, roles, and profile information.

    Features:
    - Email/username authentication
    - Role-based access control
    - Account status management
    - Profile information
    - OAuth2 provider linking
    - Two-factor authentication support
    """

    __tablename__ = "users"

    # Authentication
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    # Role & Status
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False),
        default=UserRole.USER,
        nullable=False,
        index=True,
    )
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, native_enum=False),
        default=UserStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Profile
    full_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Email verification
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    verification_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    verification_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Password reset
    reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    reset_token_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Two-factor authentication
    is_2fa_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    totp_secret: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    backup_codes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_ip: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )

    # OAuth2 provider links
    google_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )
    github_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    # Relationships
    items = relationship("Item", back_populates="owner", lazy="selectin")
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("username", name="uq_users_username"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role.value}')>"

    @property
    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE and self.is_verified

    @property
    def is_superuser(self) -> bool:
        """Check if user has superadmin privileges."""
        return self.role == UserRole.SUPERADMIN

    def has_role(self, role: UserRole) -> bool:
        """Check if user has at least the specified role."""
        return self.role.has_permission(role)

    def can_access(self, required_role: UserRole) -> bool:
        """Check if user can access resource requiring specific role."""
        return self.has_role(required_role)


class RefreshToken(Base):
    """
    Refresh token model for JWT token rotation.

    Features:
    - Token hashing for security
    - Device tracking
    - Expiration management
    - Revocation support
    """

    __tablename__ = "refresh_tokens"

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    device_info: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    replaced_by_token_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationship
    user = relationship("User", back_populates="refresh_tokens", lazy="selectin")

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token is revoked."""
        return self.revoked_at is not None

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired, not revoked)."""
        return not self.is_expired and not self.is_revoked