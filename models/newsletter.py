"""Newsletter subscription models"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse


class SubscriptionStatus(str, Enum):
    """Newsletter subscription status"""
    ACTIVE = "active"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    PENDING = "pending"


class NewsletterPreferences(BaseModel):
    """Newsletter preferences"""
    new_products: bool = Field(default=True, description="Receive new product announcements")
    promotions: bool = Field(default=True, description="Receive promotional offers")
    artisan_stories: bool = Field(default=True, description="Receive artisan stories and features")
    workshops: bool = Field(default=True, description="Receive workshop and event notifications")
    weekly_digest: bool = Field(default=True, description="Receive weekly digest")


class NewsletterSubscriber(BaseDocument):
    """Newsletter subscriber model"""
    email: EmailStr
    name: Optional[str] = None
    user_id: Optional[str] = Field(None, description="Associated user ID if logged in")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    preferences: NewsletterPreferences = Field(default_factory=NewsletterPreferences)
    
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    unsubscribed_at: Optional[datetime] = None
    
    source: Optional[str] = Field(None, description="Where they subscribed from")
    ip_address: Optional[str] = Field(None, description="IP address at signup")
    
    confirmed: bool = Field(default=False, description="Email confirmed")
    confirmation_token: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    
    tags: List[str] = Field(default_factory=list, description="Subscriber tags for segmentation")
    
    def to_firestore(self):
        """Convert to Firestore document"""
        data = self.dict(exclude={'email'})  # Use email as document ID
        data['preferences'] = self.preferences.dict()
        return data


class NewsletterSignupRequest(BaseModel):
    """Newsletter signup request"""
    email: EmailStr
    name: Optional[str] = None
    preferences: Optional[NewsletterPreferences] = None
    source: Optional[str] = Field(None, description="Signup source (footer, popup, checkout, etc.)")


class NewsletterUpdateRequest(BaseModel):
    """Update newsletter preferences"""
    preferences: NewsletterPreferences


class NewsletterUnsubscribeRequest(BaseModel):
    """Unsubscribe request"""
    email: EmailStr
    reason: Optional[str] = None


class NewsletterResponse(BaseResponse):
    """Newsletter subscription response"""
    subscriber: Optional[NewsletterSubscriber] = None


class NewsletterBulkResponse(BaseResponse):
    """Bulk newsletter operations response"""
    total_subscribers: int = 0
    active_subscribers: int = 0
    recent_signups: int = 0
