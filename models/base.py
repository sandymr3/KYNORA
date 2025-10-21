"""Base models with common fields"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


class BaseDocument(BaseModel):
    """Base model for all Firestore documents"""
    created_at: datetime
    updated_at: datetime
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.created_at:
            self.created_at = datetime.utcnow()
        if not self.updated_at:
            self.updated_at = datetime.utcnow()
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        validate_assignment = True
        use_enum_values = True
        arbitrary_types_allowed = True


class BaseResponse(BaseModel):
    """Base response model"""
    success: bool
    
    class Config:
        """Pydantic configuration"""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    limit: int = 20
    sort_by: Optional[str] = None
    sort_order: str = "desc"


class PaginatedResponse(BaseResponse):
    """Paginated response model"""
    page: int
    limit: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool
