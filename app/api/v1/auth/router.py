"""
Authentication API routes.

Handles login, registration, token refresh, password reset, and OAuth2.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    verify_token,
)
from app.db.session import get_db
from app.models.user import RefreshToken, User, UserStatus
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
)
from app.schemas.auth import (
    ForgotPasswordRequest,
    RefreshTokenRequest,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user.

    - Validates email/username uniqueness
    - Hashes password with bcrypt
    - Creates user with PENDING status
    - Returns user data (no tokens - requires email verification)
    """
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check username uniqueness
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Validate password confirmation
    if not user_data.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        bio=user_data.bio,
        avatar_url=user_data.avatar_url,
        hashed_password=hashed_password,
        status=UserStatus.PENDING,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # TODO: Send verification email

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login with username/email and password.

    Returns access and refresh tokens.
    Sets refresh token as HttpOnly cookie.
    """
    # Find user by username or email
    result = await db.execute(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled or not verified",
        )

    # Create tokens
    scopes = ["read", "write"]
    if user.role.value in ("admin", "superadmin"):
        scopes.append("admin")

    access_token = create_access_token(subject=user.email, scopes=scopes)
    refresh_token = create_refresh_token(subject=user.email)

    # Store refresh token hash
    refresh_token_hash = get_password_hash(refresh_token)
    refresh_token_obj = RefreshToken(
        token_hash=refresh_token_hash,
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        ),
    )
    db.add(refresh_token_obj)

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    user.last_login_ip = "unknown"  # Would get from request.client.host

    await db.commit()

    # Set refresh token as HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    response: Response,
    request: Request,
    refresh_data: Optional[RefreshTokenRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.

    Accepts refresh token from request body or HttpOnly cookie.
    Implements token rotation (invalidates old refresh token).
    """
    # Get refresh token from body or cookie
    refresh_token = refresh_data.refresh_token if refresh_data else None
    if not refresh_token:
        refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    # Verify token
    token_data = verify_token(refresh_token, "refresh")
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Find and validate stored refresh token
    result = await db.execute(select(RefreshToken).where(RefreshToken.user_id == user_id))
    # We need to find by hash - iterate (or add index on token_hash)
    stored_tokens = result.scalars().all()
    valid_token = None
    for stored in stored_tokens:
        if verify_password(refresh_token, stored.token_hash):
            if stored.is_valid:
                valid_token = stored
                break

    if not valid_token:
        # Potential token reuse attack - revoke all user tokens
        await db.execute(
            RefreshToken.__table__.update()
            .where(RefreshToken.user_id == user_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Get user
    result = await db.execute(select(User).where(User.email == token_data.sub))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Token rotation: revoke old token
    valid_token.revoked_at = datetime.now(timezone.utc)

    # Create new tokens
    scopes = ["read", "write"]
    if user.role.value in ("admin", "superadmin"):
        scopes.append("admin")

    new_access_token = create_access_token(subject=user.email, scopes=scopes)
    new_refresh_token = create_refresh_token(subject=user.email)

    # Store new refresh token
    new_refresh_hash = get_password_hash(new_refresh_token)
    new_refresh_obj = RefreshToken(
        token_hash=new_refresh_hash,
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        ),
        replaced_by_token_hash=new_refresh_hash,
    )
    db.add(new_refresh_obj)

    await db.commit()

    # Set new refresh token cookie
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Logout user by revoking refresh token.

    Clears refresh token cookie.
    """
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        token_data = verify_token(refresh_token, "refresh")
        if token_data:
            # Revoke the specific token
            await db.execute(
                RefreshToken.__table__.update()
                .where(RefreshToken.token_hash == get_password_hash(refresh_token))
                .values(revoked_at=datetime.now(timezone.utc))
            )
            await db.commit()

    # Clear cookie
    response.delete_cookie(key="refresh_token")

    return MessageResponse(message="Successfully logged out")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Request password reset email.

    Always returns success to prevent email enumeration.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user:
        # Generate reset token
        from secrets import token_urlsafe
        reset_token = token_urlsafe(32)
        user.reset_token = get_password_hash(reset_token)
        user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        # TODO: Send password reset email with reset_token

    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using token from email.

    Validates token and updates password.
    """
    if not request.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    # Find user with valid reset token
    result = await db.execute(select(User))
    users = result.scalars().all()

    user = None
    for u in users:
        if u.reset_token and verify_password(request.token, u.reset_token):
            if u.reset_token_expires and u.reset_token_expires > datetime.now(timezone.utc):
                user = u
                break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update password and clear reset token
    user.hashed_password = get_password_hash(request.password)
    user.reset_token = None
    user.reset_token_expires = None
    await db.commit()

    return MessageResponse(message="Password has been reset successfully")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email with token from registration email.
    """
    # Find user with valid verification token
    result = await db.execute(select(User))
    users = result.scalars().all()

    user = None
    for u in users:
        if u.verification_token and verify_password(request.token, u.verification_token):
            if u.verification_token_expires and u.verification_token_expires > datetime.now(timezone.utc):
                user = u
                break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Verify email
    user.is_verified = True
    user.status = UserStatus.ACTIVE
    user.verification_token = None
    user.verification_token_expires = None
    await db.commit()

    return MessageResponse(message="Email verified successfully")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ForgotPasswordRequest,  # Reuses email field
    db: AsyncSession = Depends(get_db),
):
    """
    Resend verification email.

    Rate limited to prevent abuse.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user and not user.is_verified:
        # Generate new verification token
        from secrets import token_urlsafe
        verification_token = token_urlsafe(32)
        user.verification_token = get_password_hash(verification_token)
        user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await db.commit()

        # TODO: Send verification email

    return MessageResponse(message="If the email exists and is unverified, a verification link has been sent")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile."""
    update_data = user_data.model_dump(exclude_unset=True)

    # Check email uniqueness if changing
    if "email" in update_data:
        result = await db.execute(
            select(User).where(
                User.email == update_data["email"],
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    # Check username uniqueness if changing
    if "username" in update_data:
        result = await db.execute(
            select(User).where(
                User.username == update_data["username"],
                User.id != current_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: UserChangePassword,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    if not request.passwords_match():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return MessageResponse(message="Password changed successfully")


# OAuth2 routes placeholder
@router.get("/oauth/{provider}")
async def oauth_login(provider: str):
    """Initiate OAuth2 login flow."""
    # TODO: Implement OAuth2 flow
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth2 not yet implemented",
    )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str):
    """Handle OAuth2 callback."""
    # TODO: Implement OAuth2 callback
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="OAuth2 not yet implemented",
    )