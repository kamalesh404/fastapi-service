"""
Items API routes.

Handles CRUD operations for items with ownership and permissions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.item import Item
from app.models.user import User
from app.schemas import (
    ItemCreate,
    ItemListResponse,
    ItemResponse,
    ItemUpdate,
    PageParams,
    PageInfo,
    PaginatedResponse,
)

router = APIRouter(prefix="/items", tags=["items"])


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new item.

    Associates item with current user as owner.
    """
    item = Item(
        title=item_data.title,
        description=item_data.description,
        content=item_data.content,
        category=item_data.category,
        is_public=item_data.is_public,
        owner_id=current_user.id,
    )

    if item_data.tags:
        item.set_tags(item_data.tags)

    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.get("", response_model=PaginatedResponse[ItemListResponse])
async def list_items(
    page_params: PageParams = Depends(),
    category: Optional[str] = Query(None, description="Filter by category"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    search: Optional[str] = Query(None, description="Search in title/description"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List items with pagination and filters.

    Shows:
    - All public items
    - Private items owned by current user
    """
    query = select(Item).where(Item.is_active == True, Item.deleted_at.is_(None))

    # Apply visibility filters
    query = query.where(
        or_(
            Item.is_public == True,
            Item.owner_id == current_user.id,
        )
    )

    # Apply filters
    if category:
        query = query.where(Item.category == category)
    if is_public is not None:
        query = query.where(Item.is_public == is_public)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.title.ilike(f"%{search}%"),
                Item.description.ilike(f"%{search}%"),
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset(page_params.offset).limit(page_params.limit)
    query = query.order_by(Item.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ItemListResponse.model_validate(item) for item in items],
        page_info=PageInfo.create(page_params.page, page_params.size, total),
    )


@router.get("/my-items", response_model=PaginatedResponse[ItemListResponse])
async def list_my_items(
    page_params: PageParams = Depends(),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List current user's items.

    Shows all items owned by current user (including deleted if requested).
    """
    query = select(Item).where(Item.owner_id == current_user.id)

    if is_active is not None:
        if is_active:
            query = query.where(Item.is_active == True, Item.deleted_at.is_(None))
        else:
            query = query.where(or_(Item.is_active == False, Item.deleted_at.is_not(None)))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination
    query = query.offset(page_params.offset).limit(page_params.limit)
    query = query.order_by(Item.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ItemListResponse.model_validate(item) for item in items],
        page_info=PageInfo.create(page_params.page, page_params.size, total),
    )


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get item by ID.

    Returns item if:
    - Item is public
    - Item is owned by current user
    """
    result = await db.execute(
        select(Item).where(
            Item.id == item_id,
            Item.is_active == True,
            Item.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    # Check access
    if not item.is_public and item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this item",
        )

    # Increment view count
    item.view_count += 1
    await db.commit()

    return item


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    item_data: ItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update item.

    Only owner can update their items.
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    # Check ownership
    if item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this item",
        )

    update_data = item_data.model_dump(exclude_unset=True)

    # Handle tags separately
    if "tags" in update_data:
        tags = update_data.pop("tags")
        if tags is not None:
            item.set_tags(tags)

    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Soft delete item.

    Only owner can delete their items.
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    # Check ownership
    if item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this item",
        )

    # Soft delete
    item.deleted_at = datetime.now(timezone.utc)
    item.is_active = False
    await db.commit()


@router.post("/{item_id}/restore", response_model=ItemResponse)
async def restore_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore soft-deleted item.

    Only owner can restore their items.
    """
    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )

    if item.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to restore this item",
        )

    if not item.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item is not deleted",
        )

    item.deleted_at = None
    item.is_active = True
    await db.commit()
    await db.refresh(item)

    return item


@router.get("/categories/list", response_model=list[str])
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all categories."""
    result = await db.execute(
        select(Item.category).where(
            Item.category.is_not(None),
            Item.is_active == True,
            Item.deleted_at.is_(None),
        ).distinct()
    )
    categories = [c[0] for c in result.all() if c[0]]
    return sorted(categories)


@router.get("/tags/list", response_model=list[str])
async def list_tags(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of all tags."""
    result = await db.execute(
        select(Item.tags).where(
            Item.tags.is_not(None),
            Item.is_active == True,
            Item.deleted_at.is_(None),
        )
    )
    all_tags = set()
    for row in result.all():
        if row[0]:
            tags = [tag.strip() for tag in row[0].split(",") if tag.strip()]
            all_tags.update(tags)
    return sorted(all_tags)


# Public items endpoint (no auth required for public items)
@router.get("/public", response_model=PaginatedResponse[ItemListResponse])
async def list_public_items(
    page_params: PageParams = Depends(),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List public items (no authentication required).

    Only shows public, active items.
    """
    query = select(Item).where(
        Item.is_active == True,
        Item.deleted_at.is_(None),
        Item.is_public == True,
    )

    if category:
        query = query.where(Item.category == category)
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Item.title.ilike(f"%{search}%"),
                Item.description.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    query = query.offset(page_params.offset).limit(page_params.limit)
    query = query.order_by(Item.created_at.desc())

    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedResponse(
        items=[ItemListResponse.model_validate(item) for item in items],
        page_info=PageInfo.create(page_params.page, page_params.size, total),
    )