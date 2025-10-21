"""User profile and management API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import logging
from datetime import datetime

from config.firebase import db
from models.user import User, UserUpdate, UserResponse, UserListResponse
from models.base import PaginationParams
from utils.auth import get_current_user, require_admin
from utils.helpers import Helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user=Depends(get_current_user)):
    """Get current user profile"""
    try:
        # Get full user data from Firestore
        user_doc = db.collection('users').document(current_user.user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        user_data = user_doc.to_dict()
        user_data['user_id'] = current_user.user_id
        user = User(**user_data)
        
        return UserResponse(
            success=True,
            message="User profile retrieved",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user=Depends(get_current_user)
):
    """Update current user profile"""
    try:
        # Get existing user
        user_doc = db.collection('users').document(current_user.user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        
        # Don't allow role or sensitive fields update
        sensitive_fields = ['role', 'user_id', 'email', 'isActive', 'created_at']
        for field in sensitive_fields:
            update_data.pop(field, None)
        
        update_data['updated_at'] = datetime.utcnow()
        
        # Update in Firestore
        db.collection('users').document(current_user.user_id).update(update_data)
        
        # Get updated user
        updated_doc = db.collection('users').document(current_user.user_id).get()
        updated_data = updated_doc.to_dict()
        updated_data['user_id'] = current_user.user_id
        updated_user = User(**updated_data)
        
        return UserResponse(
            success=True,
            message="Profile updated successfully",
            user=updated_user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_profile(user_id: str):
    """Get public user profile"""
    try:
        # Get user data
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = user_doc.to_dict()
        
        # Return only public information
        public_data = {
            'user_id': user_id,
            'displayName': user_data.get('displayName', 'User'),
            'avatar': user_data.get('avatar'),
            'role': user_data.get('role', 'customer'),
            'created_at': user_data.get('created_at'),
            'isActive': user_data.get('isActive', True)
        }
        
        # Add seller-specific public info
        if user_data.get('role') == 'seller':
            public_data.update({
                'businessName': user_data.get('businessName'),
                'businessDescription': user_data.get('businessDescription'),
                'rating': user_data.get('rating'),
                'totalSales': user_data.get('totalSales', 0)
            })
        
        user = User(**public_data)
        
        return UserResponse(
            success=True,
            message="User profile retrieved",
            user=user
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user profile"
        )


# Admin endpoints
@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    current_user=Depends(require_admin)
):
    """List all users (admin only)"""
    try:
        # Build query
        query = db.collection('users')
        
        if role:
            query = query.where('role', '==', role)
        if is_active is not None:
            query = query.where('isActive', '==', is_active)
        
        # Get all matching users
        all_docs = list(query.stream())
        total = len(all_docs)
        
        # Filter by search if provided
        if search:
            search_lower = search.lower()
            all_docs = [
                doc for doc in all_docs
                if search_lower in doc.to_dict().get('displayName', '').lower()
                or search_lower in doc.to_dict().get('email', '').lower()
            ]
            total = len(all_docs)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to User objects
        users = []
        for doc in paginated_docs:
            user_data = doc.to_dict()
            user_data['user_id'] = doc.id
            users.append(User(**user_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        return UserListResponse(
            success=True,
            message="Users retrieved successfully",
            users=users,
            **pagination
        )
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.patch("/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str = Query(..., regex="^(customer|seller|admin)$"),
    current_user=Depends(require_admin)
):
    """Update user role (admin only)"""
    try:
        # Get user
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update role
        db.collection('users').document(user_id).update({
            'role': role,
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": f"User role updated to {role}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user role: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user role"
        )


@router.patch("/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user=Depends(require_admin)
):
    """Activate or deactivate user (admin only)"""
    try:
        # Get user
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update status
        db.collection('users').document(user_id).update({
            'isActive': is_active,
            'updated_at': datetime.utcnow()
        })
        
        status_text = "activated" if is_active else "deactivated"
        
        return {
            "success": True,
            "message": f"User {status_text} successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user status"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user=Depends(require_admin)
):
    """Delete user account (admin only)"""
    try:
        # Get user
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Soft delete - just deactivate
        db.collection('users').document(user_id).update({
            'isActive': False,
            'deleted_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "User account deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )
