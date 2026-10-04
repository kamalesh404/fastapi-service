"""Items router for FastAPI service."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas import ItemCreate, ItemResponse
from app.models import Item
from app.db import get_db

router = APIRouter(prefix="/items", tags=["items"])


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item."""
    db_item = Item(
        title=item.title,
        description=item.description,
        owner_id=item.owner_id,
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/")
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Read all items with pagination."""
    items = db.query(Item).offset(skip).limit(limit).all()
    return {"items": items, "total": len(items)}


@router.get("/{item_id}")
def read_item(item_id: int, db: Session = Depends(get_db)):
    """Read a single item by ID."""
    item = db.query(Item).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    return item


@router.put("/{item_id}")
def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    """Update an existing item."""
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    
    db_item.title = item.title
    db_item.description = item.description
    db_item.owner_id = item.owner_id
    db.commit()
    db.refresh(db_item)
    return db_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item."""
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if db_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found",
        )
    
    db.delete(db_item)
    db.commit()
    return None