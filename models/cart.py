"""Cart models and schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from models.base import BaseDocument, BaseResponse
from models.product import ProductQuickView


class CartItemVariant(BaseModel):
    """Cart item variant selection"""
    color: Optional[str] = None
    size: Optional[str] = None
    material: Optional[str] = None
    # Add more variant options as needed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary excluding None values"""
        return {k: v for k, v in self.dict().items() if v is not None}


class CartItem(BaseModel):
    """Cart item model"""
    cart_item_id: str = Field(..., description="Unique cart item ID")
    product_id: str
    quantity: int = Field(..., ge=1)
    selected_variants: Optional[CartItemVariant] = None
    price_at_addition: float = Field(..., ge=0, description="Product price when added to cart")
    added_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Additional product info for display (populated from product)
    product_info: Optional[ProductQuickView] = None
    
    @validator('quantity')
    def validate_quantity(cls, v):
        """Validate quantity is positive"""
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v
    
    def calculate_subtotal(self) -> float:
        """Calculate item subtotal"""
        return self.price_at_addition * self.quantity


class AppliedCoupon(BaseModel):
    """Applied coupon model"""
    coupon_code: str
    discount_amount: float = Field(..., ge=0)
    discount_type: str = Field(..., pattern='^(percentage|fixed)$')
    description: Optional[str] = None
    
    def calculate_discount(self, subtotal: float) -> float:
        """Calculate discount amount based on type"""
        if self.discount_type == 'percentage':
            return min(subtotal * (self.discount_amount / 100), subtotal)
        else:  # fixed
            return min(self.discount_amount, subtotal)


class Cart(BaseDocument):
    """Cart model for Firestore"""
    cart_id: str = Field(..., description="Cart ID (same as user_id)")
    user_id: str = Field(..., description="User ID")
    items: List[CartItem] = Field(default_factory=list)
    
    subtotal: float = Field(default=0.0, ge=0)
    estimated_tax: float = Field(default=0.0, ge=0)
    estimated_shipping: float = Field(default=0.0, ge=0)
    total: float = Field(default=0.0, ge=0)
    
    applied_coupon: Optional[AppliedCoupon] = None
    
    session_id: Optional[str] = Field(None, description="Session ID for anonymous carts")
    expires_at: Optional[datetime] = Field(None, description="Expiration for anonymous carts")
    
    def calculate_totals(self, tax_rate: float = 0.08, shipping_rate: float = 10.0) -> 'Cart':
        """
        Calculate cart totals
        
        Args:
            tax_rate: Tax rate (default 8%)
            shipping_rate: Flat shipping rate (default $10)
        """
        # Calculate subtotal
        self.subtotal = sum(item.calculate_subtotal() for item in self.items)
        
        # Apply coupon if exists
        discount = 0.0
        if self.applied_coupon:
            discount = self.applied_coupon.calculate_discount(self.subtotal)
        
        # Calculate after discount
        discounted_subtotal = self.subtotal - discount
        
        # Calculate tax and shipping
        self.estimated_tax = round(discounted_subtotal * tax_rate, 2)
        self.estimated_shipping = shipping_rate if self.items else 0.0
        
        # Calculate total
        self.total = round(discounted_subtotal + self.estimated_tax + self.estimated_shipping, 2)
        
        return self
    
    def add_item(self, product_id: str, quantity: int, price: float, 
                 variants: Optional[CartItemVariant] = None) -> CartItem:
        """Add item to cart or update quantity if exists"""
        # Check if item already exists
        for item in self.items:
            if item.product_id == product_id:
                # Check if variants match
                if item.selected_variants == variants:
                    item.quantity += quantity
                    item.updated_at = datetime.utcnow()
                    return item
        
        # Create new item
        import uuid
        new_item = CartItem(
            cart_item_id=str(uuid.uuid4()),
            product_id=product_id,
            quantity=quantity,
            price_at_addition=price,
            selected_variants=variants
        )
        self.items.append(new_item)
        return new_item
    
    def remove_item(self, cart_item_id: str) -> bool:
        """Remove item from cart"""
        original_length = len(self.items)
        self.items = [item for item in self.items if item.cart_item_id != cart_item_id]
        return len(self.items) < original_length
    
    def update_item_quantity(self, cart_item_id: str, quantity: int) -> Optional[CartItem]:
        """Update item quantity"""
        for item in self.items:
            if item.cart_item_id == cart_item_id:
                item.quantity = quantity
                item.updated_at = datetime.utcnow()
                return item
        return None
    
    def clear(self):
        """Clear all items from cart"""
        self.items = []
        self.applied_coupon = None
        self.calculate_totals()
    
    def is_empty(self) -> bool:
        """Check if cart is empty"""
        return len(self.items) == 0
    
    def get_item_count(self) -> int:
        """Get total number of items in cart"""
        return sum(item.quantity for item in self.items)
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'cart_id'})
        # Convert items to dict
        data['items'] = [item.dict(exclude={'product_info'}) for item in self.items]
        if data.get('applied_coupon'):
            data['applied_coupon'] = self.applied_coupon.dict() if self.applied_coupon else None
        return data


class CartAddItem(BaseModel):
    """Add item to cart request"""
    product_id: str
    quantity: int = Field(default=1, ge=1)
    selected_variants: Optional[CartItemVariant] = None


class CartUpdateItem(BaseModel):
    """Update cart item request"""
    quantity: int = Field(..., ge=1)


class CartApplyCoupon(BaseModel):
    """Apply coupon request"""
    coupon_code: str


class CartResponse(BaseResponse):
    """Cart response model"""
    cart: Optional[Cart] = None


class CartSummary(BaseModel):
    """Cart summary for quick display"""
    item_count: int = 0
    subtotal: float = 0.0
    total: float = 0.0
    has_coupon: bool = False


class CartSummaryResponse(BaseResponse):
    """Cart summary response"""
    summary: CartSummary
