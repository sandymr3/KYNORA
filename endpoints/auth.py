"""
Authentication endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, status, Body
from typing import Optional, Dict
from datetime import datetime
import logging

from core.database import get_db, get_auth
from core.dependencies import get_current_user, require_authenticated_user
from core.utils import create_success_response, create_error_response, validate_email
from core.models import UserCreate

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/status")
async def check_auth_status(current_user: Optional[Dict] = Depends(get_current_user)):
    """Check authentication status"""
    if current_user:
        return create_success_response(
            data={
                "authenticated": True,
                "user_id": current_user.get('id'),
                "email": current_user.get('email'),
                "name": current_user.get('name'),
                "displayName": current_user.get('displayName', current_user.get('name')),
                "role": current_user.get('role', 'customer')
            },
            message="User is authenticated"
        )
    
    return create_success_response(
        data={"authenticated": False},
        message="User is not authenticated"
    )

@router.get("/me")
async def get_current_user_profile(current_user: Dict = Depends(require_authenticated_user)):
    """Get current authenticated user's profile"""
    return create_success_response(
        data={
            "id": current_user.get('id'),
            "user_id": current_user.get('id'),
            "uid": current_user.get('uid'),
            "email": current_user.get('email'),
            "name": current_user.get('name') or current_user.get('displayName'),
            "displayName": current_user.get('displayName', current_user.get('name')),
            "phone": current_user.get('phone', ''),
            "avatar": current_user.get('photo_url', ''),
            "photo_url": current_user.get('photo_url', ''),
            "address": current_user.get('address', {}),
            "preferences": current_user.get('preferences', {}),
            "role": current_user.get('role', 'customer'),
            "status": current_user.get('status', 'active'),
            "email_verified": current_user.get('email_verified', False),
            "created_at": current_user.get('created_at'),
            "updated_at": current_user.get('updated_at')
        },
        message="Profile retrieved successfully"
    )

@router.post("/test")
async def test_authentication(current_user: Dict = Depends(require_authenticated_user)):
    """Test authentication endpoint"""
    return create_success_response(
        data={
            "authenticated": True,
            "user_id": current_user.get('id'),
            "email": current_user.get('email'),
            "role": current_user.get('role', 'customer'),
            "timestamp": datetime.utcnow().isoformat()
        },
        message="Authentication test successful"
    )

@router.post("/register")
async def register_user(user_data: UserCreate):
    """Register new user account"""
    db = get_db()
    
    if not db:
        # Development mode without database
        return create_success_response(
            data={
                "user_id": "test_user_id",
                "email": user_data.email,
                "message": "User registered (development mode)"
            }
        )
    
    try:
        # Validate email
        if not validate_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Create user in Firebase Auth
        auth = get_auth()
        user = auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.name
        )
        
        # Create user document in Firestore
        user_doc = {
            'email': user_data.email,
            'name': user_data.name,
            'displayName': user_data.name,
            'phone': user_data.phone,
            'address': user_data.address,
            'role': 'customer',
            'status': 'active',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.collection('users').document(user.uid).set(user_doc)
        
        logger.info(f"New user registered: {user.uid} - {user_data.email}")
        
        return create_success_response(
            data={
                'user_id': user.uid,
                'email': user_data.email
            },
            message="User registered successfully"
        )
        
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/logout")
async def logout(current_user: Dict = Depends(require_authenticated_user)):
    """Logout endpoint (mainly for frontend state management)"""
    logger.info(f"User logged out: {current_user.get('id')} - {current_user.get('email')}")
    
    return create_success_response(
        message="Logged out successfully",
        data={"user_id": current_user.get('id')}
    )

@router.post("/verify-email")
async def send_verification_email(
    email: str = Body(..., embed=True),
    current_user: Dict = Depends(require_authenticated_user)
):
    """Send email verification link"""
    try:
        auth = get_auth()
        
        # Generate verification link
        link = auth.generate_email_verification_link(email)
        
        # In production, send this link via email
        # For now, return it in response (development only)
        logger.info(f"Email verification link generated for: {email}")
        
        return create_success_response(
            message="Verification email sent",
            data={"email": email, "link": link}  # Remove 'link' in production
        )
        
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send verification email"
        )

@router.post("/reset-password")
async def send_password_reset_email(email: str = Body(..., embed=True)):
    """Send password reset email"""
    try:
        if not validate_email(email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        auth = get_auth()
        
        # Generate password reset link
        link = auth.generate_password_reset_link(email)
        
        # In production, send this link via email
        # For now, return success (development)
        logger.info(f"Password reset link generated for: {email}")
        
        return create_success_response(
            message="Password reset email sent",
            data={"email": email}
        )
        
    except Exception as e:
        logger.error(f"Error sending password reset email: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send password reset email"
        )
