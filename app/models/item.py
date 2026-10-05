"""
Item model for demonstration CRUD operations.

Features:
- Ownership tracking
- Soft delete support
- Tagging system
- Search indexing preparation
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Item(Base):
    """
    Item model with ownership and categorization.

    Features:
    - Ownership tracking
    - Soft delete
    - Tags for categorization
    - Search-ready fields
    """

    __tablename__ = "items"

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Ownership
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Categorization
    tags: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Metadata
    view_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    like_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    owner = relationship("User", back_populates="items", lazy="selectin")

    # Indexes
    __table_args__ = (
        Index("ix_items_owner_active", "owner_id", "is_active"),
        Index("ix_items_category_active", "category", "is_active"),
        Index("ix_items_public_active", "is_public", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, title='{self.title}', owner_id={self.owner_id})>"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def tag_list(self) -> List[str]:
        """Get tags as a list."""
        if not self.tags:
            return []
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    def set_tags(self, tags: List[str]) -> None:
        """Set tags from a list."""
        self.tags = ",".join(tags) if tags else None