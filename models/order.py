"""Order models and schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse, PaginatedResponse


class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(str, Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class FulfillmentStatus(str, Enum):
    """Fulfillment status enumeration"""
    PENDING = "pending"
    PARTIALLY_SHIPPED = "partially_shipped"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class PaymentMethod(str, Enum):
    """Payment method enumeration"""
    CARD = "card"
    PAYPAL = "paypal"
    COD = "cod"  # Cash on Delivery
    BANK_TRANSFER = "bank_transfer"


class ShippingMethod(str, Enum):
    """Shipping method enumeration"""
    STANDARD = "standard"
    EXPRESS = "express"
    OVERNIGHT = "overnight"


class Carrier(str, Enum):
    """Shipping carrier enumeration"""
    USPS = "USPS"
    FEDEX = "FedEx"
    UPS = "UPS"
    DHL = "DHL"
    OTHER = "Other"


class OrderAddress(BaseModel):
    """Order address model"""
    recipient_name: str
    phone: str
    street: str
    city: str
    state: str
    zip_code: str
    country: str = Field(default="USA")
    
    def to_string(self) -> str:
        """Convert address to string format"""
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}, {self.country}"


class ProductSnapshot(BaseModel):
    """Product snapshot at order time"""
    title: str
    image: Optional[str] = None
    price: float
    sku: str


class OrderItem(BaseModel):
    """Order item model"""
    order_item_id: str
    product_id: str
    product_snapshot: ProductSnapshot
    quantity: int = Field(..., ge=1)
    price: float = Field(..., ge=0, description="Price at order time")
    discount: float = Field(default=0.0, ge=0)
    tax: float = Field(default=0.0, ge=0)
    subtotal: float = Field(..., ge=0)
    selected_variants: Optional[Dict[str, str]] = None
    fulfillment_status: FulfillmentStatus = Field(default=FulfillmentStatus.PENDING)
    
    def calculate_subtotal(self) -> float:
        """Calculate item subtotal"""
        return (self.price * self.quantity) - self.discount + self.tax


class OrderPricing(BaseModel):
    """Order pricing breakdown"""
    subtotal: float = Field(..., ge=0)
    discount: float = Field(default=0.0, ge=0)
    tax: float = Field(default=0.0, ge=0)
    shipping_cost: float = Field(default=0.0, ge=0)
    total: float = Field(..., ge=0)
    
    def calculate_total(self) -> float:
        """Calculate order total"""
        return self.subtotal - self.discount + self.tax + self.shipping_cost


class OrderPayment(BaseModel):
    """Order payment information"""
    payment_method: PaymentMethod
    payment_id: Optional[str] = Field(None, description="Payment gateway ID")
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    amount_paid: float = Field(default=0.0, ge=0)


class OrderShipping(BaseModel):
    """Order shipping information"""
    shipping_method: ShippingMethod
    carrier: Optional[Carrier] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    actual_delivery: Optional[datetime] = None
    shipped_at: Optional[datetime] = None


class TimelineEvent(BaseModel):
    """Order timeline event"""
    event: str
    description: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    triggered_by: Optional[str] = Field(None, description="User ID who triggered the event")


class RefundDetails(BaseModel):
    """Order refund details"""
    refund_amount: float = Field(..., ge=0)
    refund_reason: str
    refunded_at: datetime = Field(default_factory=datetime.utcnow)
    refund_status: str = Field(default="completed")
    refund_transaction_id: Optional[str] = None


class Order(BaseDocument):
    """Order model for Firestore"""
    order_id: str = Field(..., description="Order ID")
    order_number: str = Field(..., description="Human-readable order number")
    user_id: str
    seller_ids: List[str] = Field(default_factory=list, description="List of seller IDs")
    
    items: List[OrderItem]
    
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    payment_status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    fulfillment_status: FulfillmentStatus = Field(default=FulfillmentStatus.PENDING)
    
    shipping_address: OrderAddress
    billing_address: OrderAddress
    
    pricing: OrderPricing
    payment: OrderPayment
    shipping: OrderShipping
    
    customer_notes: Optional[str] = None
    internal_notes: Optional[str] = Field(None, description="Admin notes")
    
    timeline: List[TimelineEvent] = Field(default_factory=list)
    refund_details: Optional[RefundDetails] = None
    
    cancelled_at: Optional[datetime] = None
    cancelled_reason: Optional[str] = None
    
    def add_timeline_event(self, event: str, description: str, user_id: Optional[str] = None):
        """Add event to order timeline"""
        self.timeline.append(TimelineEvent(
            event=event,
            description=description,
            triggered_by=user_id
        ))
    
    def can_cancel(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [OrderStatus.PENDING, OrderStatus.CONFIRMED]
    
    def can_refund(self) -> bool:
        """Check if order can be refunded"""
        return self.payment_status == PaymentStatus.PAID and self.status != OrderStatus.REFUNDED
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'order_id'})
        # Convert nested models to dicts
        data['shipping_address'] = self.shipping_address.dict()
        data['billing_address'] = self.billing_address.dict()
        data['pricing'] = self.pricing.dict()
        data['payment'] = self.payment.dict()
        data['shipping'] = self.shipping.dict()
        data['items'] = [item.dict() for item in self.items]
        data['timeline'] = [event.dict() for event in self.timeline]
        if self.refund_details:
            data['refund_details'] = self.refund_details.dict()
        return data


class OrderCreate(BaseModel):
    """Order creation request model"""
    shipping_address: OrderAddress
    billing_address: OrderAddress
    payment_method: PaymentMethod
    shipping_method: ShippingMethod
    customer_notes: Optional[str] = None
    use_cart_items: bool = Field(default=True, description="Create order from cart items")


class OrderUpdate(BaseModel):
    """Order update request model (admin)"""
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    fulfillment_status: Optional[FulfillmentStatus] = None
    internal_notes: Optional[str] = None
    shipping: Optional[OrderShipping] = None


class OrderCancel(BaseModel):
    """Order cancellation request"""
    reason: str


class OrderRefund(BaseModel):
    """Order refund request"""
    refund_amount: float = Field(..., ge=0)
    refund_reason: str


class OrderResponse(BaseResponse):
    """Single order response"""
    order: Optional[Order] = None


class OrderListResponse(PaginatedResponse):
    """Order list response with pagination"""
    orders: List[Order] = Field(default_factory=list)


class OrderFilter(BaseModel):
    """Order filter parameters"""
    user_id: Optional[str] = None
    status: Optional[OrderStatus] = None
    payment_status: Optional[PaymentStatus] = None
    fulfillment_status: Optional[FulfillmentStatus] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_amount: Optional[float] = Field(None, ge=0)
    max_amount: Optional[float] = Field(None, ge=0)
    order_number: Optional[str] = None


class OrderSummary(BaseModel):
    """Order summary for dashboard"""
    total_orders: int = 0
    pending_orders: int = 0
    processing_orders: int = 0
    completed_orders: int = 0
    cancelled_orders: int = 0
    total_revenue: float = 0.0
    average_order_value: float = 0.0
