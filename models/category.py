"""Category models and schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse


class CategoryStatus(str, Enum):
    """Category status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class CategorySEO(BaseModel):
    """Category SEO metadata"""
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class Category(BaseDocument):
    """Category model for Firestore"""
    category_id: str = Field(..., description="Category ID")
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = Field(None, description="Parent category ID for subcategories")
    level: int = Field(default=0, description="0=root, 1=subcategory, etc.")
    path: str = Field(..., description="Category path (e.g., 'electronics/phones')")
    product_count: int = Field(default=0, ge=0)
    display_order: int = Field(default=0)
    status: CategoryStatus = Field(default=CategoryStatus.ACTIVE)
    seo: CategorySEO = Field(default_factory=CategorySEO)
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v
    
    def to_firestore(self) -> dict:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'category_id'})
        if data.get('seo'):
            data['seo'] = self.seo.dict()
        return data
    
    def is_root_category(self) -> bool:
        """Check if this is a root category"""
        return self.parent_id is None and self.level == 0
    
    def is_subcategory(self) -> bool:
        """Check if this is a subcategory"""
        return self.parent_id is not None and self.level > 0


class CategoryCreate(BaseModel):
    """Category creation request model"""
    name: str
    slug: str
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    parent_id: Optional[str] = None
    display_order: int = Field(default=0)
    status: CategoryStatus = Field(default=CategoryStatus.ACTIVE)
    seo: Optional[CategorySEO] = None


class CategoryUpdate(BaseModel):
    """Category update request model"""
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    status: Optional[CategoryStatus] = None
    seo: Optional[CategorySEO] = None


class CategoryResponse(BaseResponse):
    """Single category response"""
    category: Optional[Category] = None


class CategoryListResponse(BaseResponse):
    """Category list response"""
    categories: List[Category] = Field(default_factory=list)
    total: int = 0


class CategoryTree(BaseModel):
    """Category tree structure for navigation"""
    category: Category
    children: List['CategoryTree'] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True


# Update forward references
CategoryTree.model_rebuild()


class CategoryTreeResponse(BaseResponse):
    """Category tree response"""
    tree: List[CategoryTree] = Field(default_factory=list)
