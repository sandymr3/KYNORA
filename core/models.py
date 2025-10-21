"""
Pydantic models for KYNORA backend
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime

# ==================== USER MODELS ====================

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    displayName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    displayName: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    role: str = "customer"
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# ==================== PRODUCT MODELS ====================

class ProductCreate(BaseModel):
    title: str
    description: str
    price: float = Field(gt=0)
    category_id: str
    subcategory_id: Optional[str] = None
    images: List[str] = []
    inventory_quantity: int = Field(ge=0, default=0)
    tags: List[str] = []
    is_featured: bool = False
    specifications: Optional[Dict[str, Any]] = None
    variants: Optional[List[Dict[str, Any]]] = None
    seller_id: Optional[str] = None

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    images: Optional[List[str]] = None
    inventory_quantity: Optional[int] = Field(None, ge=0)
    is_featured: Optional[bool] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None
    variants: Optional[List[Dict[str, Any]]] = None

# ==================== CART MODELS ====================

class CartItemAdd(BaseModel):
    product_id: str
    quantity: int = Field(ge=1, default=1)
    variant_id: Optional[str] = None
    customization: Optional[Dict[str, Any]] = None

class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0)

class CartSync(BaseModel):
    guest_cart_items: List[Dict[str, Any]]

# ==================== ORDER MODELS ====================

class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float
    quantity: int
    variant_id: Optional[str] = None
    image: Optional[str] = None
    customization: Optional[Dict[str, Any]] = None

class ShippingAddress(BaseModel):
    name: str
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    postal_code: str
    country: str
    phone: Optional[str] = None

class OrderCreate(BaseModel):
    items: List[OrderItem]
    shipping_address: ShippingAddress
    billing_address: Optional[ShippingAddress] = None
    payment_method: str
    shipping_method: str
    notes: Optional[str] = None
    coupon_code: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|confirmed|processing|shipped|delivered|cancelled)$")
    reason: Optional[str] = None
    tracking_number: Optional[str] = None
    expected_delivery: Optional[str] = None

class OrderCancel(BaseModel):
    reason: str

# ==================== REVIEW MODELS ====================

class ReviewCreate(BaseModel):
    product_id: str
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None
    images: Optional[List[str]] = None

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    comment: Optional[str] = None
    images: Optional[List[str]] = None

class ReviewResponse(BaseModel):
    response: str

# ==================== CATEGORY MODELS ====================

class CategoryCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

# ==================== WISHLIST MODELS ====================

class WishlistItemAdd(BaseModel):
    product_id: str
    variant_id: Optional[str] = None

# ==================== COUPON MODELS ====================

class CouponCreate(BaseModel):
    code: str
    description: str
    discount_type: str = Field(..., pattern="^(percentage|fixed)$")
    discount_value: float = Field(gt=0)
    min_purchase: Optional[float] = Field(None, ge=0)
    max_discount: Optional[float] = Field(None, ge=0)
    usage_limit: Optional[int] = Field(None, ge=1)
    valid_from: datetime
    valid_to: datetime
    applicable_products: Optional[List[str]] = None
    applicable_categories: Optional[List[str]] = None

class CouponValidate(BaseModel):
    code: str
    order_total: float
    products: Optional[List[str]] = None
    categories: Optional[List[str]] = None
