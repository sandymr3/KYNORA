"""Review models and schemas"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse, PaginatedResponse
from models.user import UserPublicProfile


class ReviewStatus(str, Enum):
    """Review status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    HIDDEN = "hidden"


class SellerResponse(BaseModel):
    """Seller response to review"""
    content: str
    responded_at: datetime = Field(default_factory=datetime.utcnow)
    responder_id: str


class Review(BaseDocument):
    """Review model for Firestore"""
    review_id: str = Field(..., description="Review ID")
    product_id: str
    user_id: str
    order_id: str = Field(..., description="Order ID for verification")
    
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: str = Field(..., max_length=100)
    content: str = Field(..., min_length=10, max_length=1000)
    images: List[str] = Field(default_factory=list, description="Review image URLs")
    
    verified_purchase: bool = Field(default=False)
    helpful_count: int = Field(default=0, ge=0)
    reported_count: int = Field(default=0, ge=0)
    
    status: ReviewStatus = Field(default=ReviewStatus.PENDING)
    seller_response: Optional[SellerResponse] = None
    
    # User info for display (populated from user)
    user_info: Optional[UserPublicProfile] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        """Validate rating is between 1 and 5"""
        if not 1 <= v <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
    
    @validator('content')
    def validate_content(cls, v):
        """Validate review content"""
        if len(v) < 10:
            raise ValueError('Review content must be at least 10 characters')
        if len(v) > 1000:
            raise ValueError('Review content must not exceed 1000 characters')
        return v
    
    def is_positive(self) -> bool:
        """Check if review is positive (4 or 5 stars)"""
        return self.rating >= 4
    
    def to_firestore(self) -> dict:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'review_id', 'user_info'})
        if self.seller_response:
            data['seller_response'] = self.seller_response.dict()
        return data


class ReviewCreate(BaseModel):
    """Review creation request model"""
    product_id: str
    order_id: str
    rating: int = Field(..., ge=1, le=5)
    title: str = Field(..., max_length=100)
    content: str = Field(..., min_length=10, max_length=1000)
    images: List[str] = Field(default_factory=list)


class ReviewUpdate(BaseModel):
    """Review update request model"""
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = Field(None, max_length=100)
    content: Optional[str] = Field(None, min_length=10, max_length=1000)
    images: Optional[List[str]] = None


class ReviewSellerResponse(BaseModel):
    """Seller response to review request"""
    content: str = Field(..., min_length=10, max_length=500)


class ReviewHelpful(BaseModel):
    """Mark review as helpful request"""
    is_helpful: bool = True


class ReviewReport(BaseModel):
    """Report review request"""
    reason: str = Field(..., min_length=10, max_length=200)


class ReviewResponse(BaseResponse):
    """Single review response"""
    review: Optional[Review] = None


class ReviewListResponse(PaginatedResponse):
    """Review list response with pagination"""
    reviews: List[Review] = Field(default_factory=list)


class ReviewFilter(BaseModel):
    """Review filter parameters"""
    product_id: Optional[str] = None
    user_id: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    verified_purchase: Optional[bool] = None
    status: Optional[ReviewStatus] = None
    has_images: Optional[bool] = None
    has_seller_response: Optional[bool] = None


class ReviewStats(BaseModel):
    """Product review statistics"""
    product_id: str
    total_reviews: int = 0
    average_rating: float = Field(default=0.0, ge=0, le=5)
    rating_distribution: dict = Field(
        default_factory=lambda: {
            "5": 0,
            "4": 0,
            "3": 0,
            "2": 0,
            "1": 0
        }
    )
    verified_purchase_count: int = 0
    with_images_count: int = 0
    
    def calculate_average(self) -> float:
        """Calculate average rating from distribution"""
        if self.total_reviews == 0:
            return 0.0
        
        total_score = sum(
            int(rating) * count 
            for rating, count in self.rating_distribution.items()
        )
        return round(total_score / self.total_reviews, 2)


class ReviewStatsResponse(BaseResponse):
    """Review statistics response"""
    stats: Optional[ReviewStats] = None
