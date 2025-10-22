"""Product models and schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse, PaginatedResponse


class ProductStatus(str, Enum):
    """Product status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ProductDimensions(BaseModel):
    """Product dimensions model"""
    length: float = Field(..., description="Length in cm")
    width: float = Field(..., description="Width in cm")
    height: float = Field(..., description="Height in cm")


class ProductSEO(BaseModel):
    """Product SEO metadata"""
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    meta_keywords: List[str] = Field(default_factory=list)


class Product(BaseDocument):
    """Product model for artisan/handmade products"""
    product_id: str = Field(..., description="Product ID")
    title: str
    slug: str
    description: str
    short_description: str = Field(..., max_length=100)
    price: float = Field(..., ge=0)
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price for discounts")
    cost_price: Optional[float] = Field(None, ge=0, description="Seller cost (admin only)")
    
    # Categories for artisan products
    category_id: str  # e.g., "pottery", "handmade-toys", "crafts", "art"
    subcategory_id: Optional[str] = None
    seller_id: str
    artisan_name: Optional[str] = Field(None, description="Name of the artisan/craftsperson")
    
    images: List[str] = Field(default_factory=list, description="Product image URLs")
    thumbnail: Optional[str] = None
    
    # Artisan product specifications
    material: Optional[str] = Field(None, description="Primary material (e.g., clay, wood, fabric)")
    crafting_method: Optional[str] = Field(None, description="How it's made (e.g., hand-thrown, carved, sewn)")
    customizable: bool = Field(default=False, description="Can be customized on request")
    made_to_order: bool = Field(default=False, description="Made to order vs ready stock")
    processing_time: Optional[int] = Field(None, description="Days needed to make/process if made to order")
    
    # Additional artisan details
    care_instructions: Optional[str] = Field(None, description="How to care for the product")
    origin_location: Optional[str] = Field(None, description="Where the product is made")
    is_eco_friendly: bool = Field(default=False, description="Made with eco-friendly materials/processes")
    is_handmade: bool = Field(default=True, description="Handmade vs machine made")
    uniqueness_note: Optional[str] = Field(None, description="Note about product variations")
    
    specifications: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    inventory_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    sku: str
    barcode: Optional[str] = None
    
    weight: Optional[float] = Field(None, ge=0, description="Weight in grams")
    dimensions: Optional[ProductDimensions] = None
    
    status: ProductStatus = Field(default=ProductStatus.DRAFT)
    is_featured: bool = False
    is_on_sale: bool = False
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None
    
    view_count: int = Field(default=0, ge=0)
    sales_count: int = Field(default=0, ge=0)
    rating_average: float = Field(default=0.0, ge=0, le=5)
    rating_count: int = Field(default=0, ge=0)
    
    seo: ProductSEO = Field(default_factory=ProductSEO)
    deleted_at: Optional[datetime] = None
    
    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format"""
        import re
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v
    
    @validator('compare_at_price')
    def validate_compare_price(cls, v, values):
        """Ensure compare_at_price is greater than price"""
        if v is not None and 'price' in values:
            if v <= values['price']:
                raise ValueError('Compare at price must be greater than price')
        return v
    
    @validator('sale_end_date')
    def validate_sale_dates(cls, v, values):
        """Ensure sale_end_date is after sale_start_date"""
        if v is not None and 'sale_start_date' in values and values['sale_start_date'] is not None:
            if v <= values['sale_start_date']:
                raise ValueError('Sale end date must be after sale start date')
        return v
    
    def calculate_discount_percentage(self) -> float:
        """Calculate discount percentage"""
        if self.compare_at_price and self.compare_at_price > self.price:
            return round((1 - self.price / self.compare_at_price) * 100, 2)
        return 0.0
    
    def is_in_stock(self) -> bool:
        """Check if product is in stock"""
        return self.inventory_quantity > 0
    
    def is_low_stock(self) -> bool:
        """Check if product has low stock"""
        return 0 < self.inventory_quantity <= self.low_stock_threshold
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'product_id'})
        if data.get('dimensions'):
            data['dimensions'] = self.dimensions.dict() if self.dimensions else None
        if data.get('seo'):
            data['seo'] = self.seo.dict()
        return data


class ProductCreate(BaseModel):
    """Product creation request model for artisan products"""
    title: str
    slug: str
    description: str
    short_description: str = Field(..., max_length=100)
    price: float = Field(..., ge=0)
    compare_at_price: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    
    category_id: str
    subcategory_id: Optional[str] = None
    artisan_name: Optional[str] = None
    
    # Artisan product specifications
    material: Optional[str] = None
    crafting_method: Optional[str] = None
    customizable: bool = Field(default=False)
    made_to_order: bool = Field(default=False)
    processing_time: Optional[int] = None
    
    # Additional artisan details
    care_instructions: Optional[str] = None
    origin_location: Optional[str] = None
    is_eco_friendly: bool = Field(default=False)
    is_handmade: bool = Field(default=True)
    uniqueness_note: Optional[str] = None
    
    images: List[str] = Field(default_factory=list)
    specifications: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    
    inventory_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=10, ge=0)
    sku: str
    barcode: Optional[str] = None
    
    weight: Optional[float] = Field(None, ge=0)
    dimensions: Optional[ProductDimensions] = None
    
    status: ProductStatus = Field(default=ProductStatus.DRAFT)
    seo: Optional[ProductSEO] = None


class ProductUpdate(BaseModel):
    """Product update request model for artisan products"""
    title: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=100)
    price: Optional[float] = Field(None, ge=0)
    compare_at_price: Optional[float] = Field(None, ge=0)
    cost_price: Optional[float] = Field(None, ge=0)
    
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    artisan_name: Optional[str] = None
    
    # Artisan product specifications
    material: Optional[str] = None
    crafting_method: Optional[str] = None
    customizable: Optional[bool] = None
    made_to_order: Optional[bool] = None
    processing_time: Optional[int] = None
    
    # Additional artisan details
    care_instructions: Optional[str] = None
    origin_location: Optional[str] = None
    is_eco_friendly: Optional[bool] = None
    is_handmade: Optional[bool] = None
    uniqueness_note: Optional[str] = None
    
    images: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    inventory_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    sku: Optional[str] = None
    barcode: Optional[str] = None
    
    weight: Optional[float] = Field(None, ge=0)
    dimensions: Optional[ProductDimensions] = None
    
    status: Optional[ProductStatus] = None
    is_featured: Optional[bool] = None
    is_on_sale: Optional[bool] = None
    sale_start_date: Optional[datetime] = None
    sale_end_date: Optional[datetime] = None
    
    seo: Optional[ProductSEO] = None


class ProductResponse(BaseResponse):
    """Single product response"""
    product: Optional[Product] = None


class ProductListResponse(PaginatedResponse):
    """Product list response with pagination"""
    products: List[Product] = Field(default_factory=list)


class ProductFilter(BaseModel):
    """Product filter parameters"""
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    seller_id: Optional[str] = None
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    in_stock: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_on_sale: Optional[bool] = None
    tags: Optional[List[str]] = None
    status: Optional[ProductStatus] = None
    search: Optional[str] = None
    
    @validator('max_price')
    def validate_price_range(cls, v, values):
        """Ensure max_price is greater than min_price"""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('Maximum price must be greater than minimum price')
        return v


class ProductQuickView(BaseModel):
    """Product quick view model (minimal data)"""
    product_id: str
    title: str
    slug: str
    price: float
    compare_at_price: Optional[float] = None
    thumbnail: Optional[str] = None
    rating_average: float = 0.0
    is_on_sale: bool = False
    in_stock: bool = True
