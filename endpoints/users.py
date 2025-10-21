"""
User management endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import Optional, List
from datetime import datetime
import logging

from core.database import get_db, get_auth
from core.dependencies import require_authenticated_user, require_admin
from core.utils import create_success_response, create_error_response
from core.models import UserUpdate, UserProfile

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/profile")
async def get_user_profile(current_user: dict = Depends(require_authenticated_user)):
    """Get current user's detailed profile"""
    return create_success_response(
        data={
            "user_id": current_user.get('id'),
            "email": current_user.get('email'),
            "name": current_user.get('name'),
            "displayName": current_user.get('displayName', current_user.get('name')),
            "phone": current_user.get('phone'),
            "address": current_user.get('address'),
            "preferences": current_user.get('preferences', {}),
            "role": current_user.get('role', 'customer'),
            "status": current_user.get('status', 'active'),
            "created_at": current_user.get('created_at'),
            "updated_at": current_user.get('updated_at')
        },
        message="Profile retrieved successfully"
    )

@router.put("/profile")
async def update_user_profile(
    profile_data: UserUpdate,
    current_user: dict = Depends(require_authenticated_user)
):
    """Update current user's profile"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Profile updated (development mode)",
            data={"user_id": current_user.get('id')}
        )
    
    try:
        update_data = profile_data.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()
        
        # Update in Firestore
        db.collection('users').document(current_user['id']).update(update_data)
        
        # If displayName is updated, also update in Firebase Auth
        if 'displayName' in update_data or 'name' in update_data:
            auth = get_auth()
            display_name = update_data.get('displayName') or update_data.get('name')
            auth.update_user(current_user['id'], display_name=display_name)
        
        logger.info(f"Profile updated for user: {current_user['id']}")
        
        return create_success_response(
            message="Profile updated successfully",
            data={"user_id": current_user['id']}
        )
        
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/profile")
async def update_user_profile_post(
    profile_data: UserUpdate,
    current_user: dict = Depends(require_authenticated_user)
):
    """Update user profile (POST method for compatibility)"""
    return await update_user_profile(profile_data, current_user)

@router.get("/me")
async def get_me(current_user: dict = Depends(require_authenticated_user)):
    """Get current user info"""
    return create_success_response(
        data={
            "id": current_user.get('id'),
            "user_id": current_user.get('id'),
            "uid": current_user.get('uid'),
            "email": current_user.get('email'),
            "displayName": current_user.get('displayName', current_user.get('name')),
            "name": current_user.get('name') or current_user.get('displayName'),
            "role": current_user.get('role', 'customer'),
            "phone": current_user.get('phone', ''),
            "avatar": current_user.get('photo_url', ''),
            "photo_url": current_user.get('photo_url', ''),
            "address": current_user.get('address', {}),
            "preferences": current_user.get('preferences', {}),
            "status": current_user.get('status', 'active'),
            "email_verified": current_user.get('email_verified', False),
            "created_at": current_user.get('created_at'),
            "updated_at": current_user.get('updated_at')
        },
        message="User profile retrieved successfully"
    )

@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(require_admin)
):
    """Get user by ID (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        user_doc = db.collection('users').document(user_id).get()
        
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user_data = user_doc.to_dict()
        user_data['id'] = user_id
        user_data['user_id'] = user_id
        
        return create_success_response(
            data=user_data,
            message="User retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user"
        )

@router.put("/{user_id}")
async def update_user_by_id(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdate = None,
    current_user: dict = Depends(require_admin)
):
    """Update user by ID (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        # Check if user exists
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        update_data = user_data.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()
        
        # Update in Firestore
        db.collection('users').document(user_id).update(update_data)
        
        logger.info(f"User updated by admin: {user_id}")
        
        return create_success_response(
            message="User updated successfully",
            data={"user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("")
async def get_users_by_role(
    role: str = Query(..., description="User role to filter by"),
    limit: int = Query(50, ge=1, le=100, description="Number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    current_user: dict = Depends(require_admin)
):
    """Get users by role (admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={"users": [], "total": 0},
            message="No database available"
        )
    
    try:
        query = db.collection('users').where('role', '==', role)
        
        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        query = query.limit(limit)
        
        users = []
        for doc in query.stream():
            user_data = doc.to_dict()
            user_data['id'] = doc.id
            user_data['user_id'] = doc.id
            users.append(user_data)
        
        return create_success_response(
            data={
                "users": users,
                "total": len(users),
                "role": role,
                "limit": limit,
                "offset": offset
            },
            message=f"Retrieved {len(users)} users with role: {role}"
        )
        
    except Exception as e:
        logger.error(f"Error getting users by role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )

@router.patch("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(require_admin)
):
    """Deactivate user account (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        # Update user status in Firestore
        db.collection('users').document(user_id).update({
            'status': 'deactivated',
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': current_user['id']
        })
        
        # Disable user in Firebase Auth
        auth = get_auth()
        auth.update_user(user_id, disabled=True)
        
        logger.info(f"User deactivated: {user_id} by admin: {current_user['id']}")
        
        return create_success_response(
            message="User deactivated successfully",
            data={"user_id": user_id}
        )
        
    except Exception as e:
        logger.error(f"Error deactivating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.patch("/{user_id}/activate")
async def activate_user(
    user_id: str = Path(..., description="User ID"),
    current_user: dict = Depends(require_admin)
):
    """Activate user account (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        # Update user status in Firestore
        db.collection('users').document(user_id).update({
            'status': 'active',
            'activated_at': datetime.utcnow(),
            'activated_by': current_user['id']
        })
        
        # Enable user in Firebase Auth
        auth = get_auth()
        auth.update_user(user_id, disabled=False)
        
        logger.info(f"User activated: {user_id} by admin: {current_user['id']}")
        
        return create_success_response(
            message="User activated successfully",
            data={"user_id": user_id}
        )
        
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
