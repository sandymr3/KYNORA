"""Authentication API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta
import logging

from config.firebase import firebase_config, db
from config.settings import settings
from models.user import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    PasswordReset, User, UserRole
)
from utils.auth import (
    create_access_token, create_refresh_token, 
    verify_token, get_current_user, hash_password
)
from utils.validators import Validators

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    try:
        # Validate email
        if not Validators.validate_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        
        # Check if user exists
        users_ref = db.collection('users')
        existing = users_ref.where('email', '==', user_data.email).limit(1).stream()
        if list(existing):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists"
            )
        
        # Create user in Firebase Auth
        try:
            firebase_user = firebase_config.create_user(
                email=user_data.email,
                password=user_data.password,
                display_name=user_data.name
            )
            user_id = firebase_user.uid
        except Exception as e:
            logger.error(f"Firebase Auth error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to create user: {str(e)}"
            )
        
        # Create user document in Firestore
        user = User(
            user_id=user_id,
            email=user_data.email,
            name=user_data.name,
            display_name=user_data.name.split()[0],
            phone=user_data.phone,
            role=UserRole.CUSTOMER
        )
        
        # Save to Firestore
        users_ref.document(user_id).set(user.to_firestore())
        
        return UserResponse(
            success=True,
            message="User registered successfully",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login with email and password"""
    try:
        # Get user from Firestore
        users_ref = db.collection('users')
        user_docs = users_ref.where('email', '==', credentials.email).limit(1).stream()
        user_doc = next(user_docs, None)
        
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        user_data = user_doc.to_dict()
        user_data['user_id'] = user_doc.id
        user = User(**user_data)
        
        # TODO: Verify password with Firebase Auth
        # For now, we'll create tokens directly
        
        # Create tokens
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "sub": user.user_id,
                "email": user.email,
                "role": user.role.value
            },
            expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(
            data={
                "sub": user.user_id,
                "email": user.email,
                "role": user.role.value
            }
        )
        
        # Update last login
        users_ref.document(user.user_id).update({
            'metadata.last_login': user_data.get('metadata', {}).get('last_login'),
            'metadata.login_count': user_data.get('metadata', {}).get('login_count', 0) + 1
        })
        
        return TokenResponse(
            success=True,
            message="Login successful",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(refresh_token: str):
    """Refresh access token"""
    try:
        # Verify refresh token
        token_data = verify_token(refresh_token)
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        access_token = create_access_token(
            data={
                "sub": token_data.user_id,
                "email": token_data.email,
                "role": token_data.role
            },
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            success=True,
            message="Token refreshed",
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.jwt_access_token_expire_minutes * 60
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user = Depends(get_current_user)):
    """Get current user profile"""
    try:
        # Get user from Firestore
        user_doc = db.collection('users').document(current_user.user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = user_doc.to_dict()
        user_data['user_id'] = user_doc.id
        user = User(**user_data)
        
        return UserResponse(
            success=True,
            message="User profile retrieved",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile"
        )


@router.post("/logout")
async def logout(current_user = Depends(get_current_user)):
    """Logout user (client should remove tokens)"""
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/forgot-password")
async def forgot_password(data: PasswordReset):
    """Request password reset"""
    try:
        # Check if user exists
        users_ref = db.collection('users')
        user_docs = users_ref.where('email', '==', data.email).limit(1).stream()
        
        if not list(user_docs):
            # Don't reveal if user exists
            return {
                "success": True,
                "message": "If the email exists, a reset link has been sent"
            }
        
        # TODO: Send password reset email via Firebase Auth
        
        return {
            "success": True,
            "message": "If the email exists, a reset link has been sent"
        }
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process request"
        )
