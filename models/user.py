"""User models and schemas"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
from models.base import BaseDocument, BaseResponse


class UserRole(str, Enum):
    """User role enumeration"""
    CUSTOMER = "customer"
    SELLER = "seller"
    ADMIN = "admin"
    MANAGER = "manager"


class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class Address(BaseModel):
    """Address model"""
    street: str
    city: str
    state: str
    zip_code: str
    country: str = Field(default="USA")


class UserPreferences(BaseModel):
    """User preferences model"""
    notifications: bool = True
    newsletter: bool = False
    language: str = Field(default="en")
    currency: str = Field(default="USD")


class UserMetadata(BaseModel):
    """User metadata model"""
    last_login: Optional[datetime] = None
    login_count: int = 0
    ip_address: Optional[str] = None


    full_name: str
    display_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.CUSTOMER)
    avatar: Optional[str] = None
    phone: Optional[str] = None
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    email_verified: bool = False
    address: Optional[Address] = None
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    metadata: UserMetadata = Field(default_factory=UserMetadata)
    
    @validator('display_name', always=True)
    def set_display_name(cls, v, values):
        """Set display name from name if not provided"""
        if v is None and 'full_name' in values:
            return values['full_name'].split()[0] if values['full_name'] else None
        return v
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format"""
        data = self.dict(exclude={'user_id'})
        # Convert nested models to dicts
        if data.get('address'):
            data['address'] = self.address.dict() if self.address else None
        if data.get('preferences'):
            data['preferences'] = self.preferences.dict()
        if data.get('metadata'):
            data['metadata'] = self.metadata.dict()
        return data


    full_name: str
    phone: Optional[str] = None
    
    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """User update request model"""
    full_name: Optional[str] = None
    display_name: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    address: Optional[Address] = None
    preferences: Optional[UserPreferences] = None


class UserLogin(BaseModel):
    """User login request model"""
    email: EmailStr
    password: str


class UserResponse(BaseResponse):
    """User response model"""
    user: Optional[User] = None


class TokenData(BaseModel):
    """Token data model"""
    user_id: str
    email: str
    role: UserRole
    exp: Optional[datetime] = None


class TokenResponse(BaseResponse):
    """Token response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="Expiration time in seconds")
    user: Optional[User] = None


class PasswordReset(BaseModel):
    """Password reset request model"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation model"""
    token: str
    new_password: str = Field(..., min_length=8)
    
    @validator('new_password')
    def validate_password(cls, v):
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(char.isupper() for char in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(char.islower() for char in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(char.isdigit() for char in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserPublicProfile(BaseModel):
    """Public user profile model (for reviews, etc.)"""
    user_id: str
    display_name: str
    avatar: Optional[str] = None
    verified: bool = False
