"""File upload router for FastAPI service."""

from fastapi import APIRouter, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.models import Item
from app.db import get_db

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a file and store information in database."""
    # Read file content
    content = file.file.read()
    
    # Create database record
    db_item = Item(
        title=file.filename,
        description=f"Uploaded file: {file.filename}",
        owner_id=1,  # In production, use authenticated user ID
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return {
        "message": "File uploaded successfully",
        "filename": file.filename,
        "size": len(content),
        "item_id": db_item.id,
    }