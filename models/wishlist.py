"""Wishlist models and schemas"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from models.base import BaseDocument, BaseResponse


class WishlistItem(BaseModel):
    """Wishlist item model"""
    product_id: str
    added_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = None
    priority: int = Field(default=0, ge=0, le=5, description="Priority 0-5")


class Wishlist(BaseDocument):
    """User wishlist model"""
    user_id: str
    items: List[WishlistItem] = Field(default_factory=list)
    is_public: bool = Field(default=False, description="Whether wishlist is publicly viewable")
    name: Optional[str] = Field(default="My Wishlist")
    
    def add_item(self, product_id: str, notes: Optional[str] = None, priority: int = 0) -> bool:
        """Add item to wishlist if not already present"""
        if not any(item.product_id == product_id for item in self.items):
            self.items.append(WishlistItem(
                product_id=product_id,
                notes=notes,
                priority=priority
            ))
            return True
        return False
    
    def remove_item(self, product_id: str) -> bool:
        """Remove item from wishlist"""
        initial_count = len(self.items)
        self.items = [item for item in self.items if item.product_id != product_id]
        return len(self.items) < initial_count
    
    def has_product(self, product_id: str) -> bool:
        """Check if product is in wishlist"""
        return any(item.product_id == product_id for item in self.items)
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        return {
            'user_id': self.user_id,
            'items': [item.dict() for item in self.items],
            'is_public': self.is_public,
            'name': self.name,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class WishlistAddRequest(BaseModel):
    """Add to wishlist request"""
    product_id: str
    notes: Optional[str] = None
    priority: Optional[int] = Field(default=0, ge=0, le=5)


class WishlistResponse(BaseResponse):
    """Wishlist response"""
    wishlist: Optional[Wishlist] = None
    total_items: int = 0


class WishlistProductsResponse(BaseResponse):
    """Wishlist with populated products"""
    wishlist: Optional[Wishlist] = None
    products: List[Dict[str, Any]] = Field(default_factory=list)
    total_items: int = 0
