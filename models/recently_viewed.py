"""Recently Viewed Products models"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.base import BaseDocument, BaseResponse


class ViewedProduct(BaseModel):
    """Viewed product entry"""
    product_id: str
    viewed_at: datetime = Field(default_factory=datetime.utcnow)
    view_count: int = Field(default=1, ge=1)
    last_viewed: datetime = Field(default_factory=datetime.utcnow)


class RecentlyViewed(BaseDocument):
    """User's recently viewed products"""
    user_id: str
    products: List[ViewedProduct] = Field(default_factory=list)
    max_items: int = Field(default=20, description="Maximum number of recently viewed items to store")
    
    def add_product(self, product_id: str) -> None:
        """Add or update a recently viewed product"""
        # Check if product already exists
        for product in self.products:
            if product.product_id == product_id:
                product.view_count += 1
                product.last_viewed = datetime.utcnow()
                # Move to front of list
                self.products.remove(product)
                self.products.insert(0, product)
                return
        
        # Add new product to front
        new_product = ViewedProduct(product_id=product_id)
        self.products.insert(0, new_product)
        
        # Trim list to max_items
        if len(self.products) > self.max_items:
            self.products = self.products[:self.max_items]
    
    def get_product_ids(self, limit: int = None) -> List[str]:
        """Get list of recently viewed product IDs"""
        products = self.products[:limit] if limit else self.products
        return [p.product_id for p in products]
    
    def clear(self) -> None:
        """Clear all recently viewed products"""
        self.products = []
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document"""
        return {
            'user_id': self.user_id,
            'products': [p.dict() for p in self.products],
            'max_items': self.max_items,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


class RecentlyViewedResponse(BaseResponse):
    """Recently viewed products response"""
    products: List[Dict[str, Any]] = Field(default_factory=list)
    total_items: int = 0
