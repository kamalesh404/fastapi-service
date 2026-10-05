"""
Users API routes.

Handles user management for admins and user profiles.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user, require_scopes
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas import (
    MessageResponse,
    PageParams,
    PageInfo,
    PaginatedResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=PaginatedResponse[UserListResponse])
async def list_users(
    page_params: PageParams = Depends(),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in email/username/name"),
    current_user: User = Depends(require_scopes("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    List users with pagination and filters.

    Requires admin scope.
    """
    query = select(User)

    # Apply filters
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            (User.email.ilike(search_term))
            | (User.username.ilike(search_term))
            | (User.full_name.ilike(search_term))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset(page_params.offset).limit(page_params.limit)
    query = query.order_by(User.created_at.desc())

    result = await db.execute(query)
    users = result.scalars().all()

    return PaginatedResponse(
        items=[UserListResponse.model_validate(u) for u in users],
        page_info=PageInfo.create(page_params.page, page_params.size, total),
    )


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get current user's full profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
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


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(require_scopes("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_scopes("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-demotion
    if user.id == current_user.id and "role" in user_data.model_dump(exclude_unset=True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    update_data = user_data.model_dump(exclude_unset=True)

    # Check email uniqueness
    if "email" in update_data:
        result = await db.execute(
            select(User).where(
                User.email == update_data["email"],
                User.id != user_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use",
            )

    # Check username uniqueness
    if "username" in update_data:
        result = await db.execute(
            select(User).where(
                User.username == update_data["username"],
                User.id != user_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_scopes("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete user (superadmin only).

    Soft deletes by setting status to DELETED.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    user.status = "deleted"
    user.is_active = False
    await db.commit()


@router.post("/{user_id}/activate", response_model=MessageResponse)
async def activate_user(
    user_id: int,
    current_user: User = Depends(require_scopes("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Activate a suspended user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.status = "active"
    await db.commit()

    return MessageResponse(message=f"User {user.username} has been activated")


@router.post("/{user_id}/suspend", response_model=MessageResponse)
async def suspend_user(
    user_id: int,
    current_user: User = Depends(require_scopes("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Suspend a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend yourself",
        )

    user.status = "suspended"
    await db.commit()

    return MessageResponse(message=f"User {user.username} has been suspended")


@router.post("/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: int,
    role: str = Query(..., description="New role"),
    current_user: User = Depends(require_scopes("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    """Change user role (superadmin only)."""
    from app.models.user import UserRole

    try:
        new_role = UserRole(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {[r.value for r in UserRole]}",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    user.role = new_role
    await db.commit()
    await db.refresh(user)

    return user