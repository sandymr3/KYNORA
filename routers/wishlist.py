"""Wishlist API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import logging

from models.wishlist import (
    Wishlist, WishlistAddRequest, 
    WishlistResponse, WishlistProductsResponse
)
from models.product import Product
from core.database import get_firestore_client
from utils.auth import get_current_active_user
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wishlist", tags=["Wishlist"])


@router.get("", response_model=WishlistProductsResponse)
async def get_wishlist(current_user = Depends(get_current_active_user)):
    """Get user's wishlist with populated product details"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get or create wishlist
        wishlist_ref = db.collection('wishlists').document(current_user.user_id)
        wishlist_doc = wishlist_ref.get()
        
        if not wishlist_doc.exists:
            # Create new wishlist
            wishlist_data = {
                'user_id': current_user.user_id,
                'items': [],
                'is_public': False,
                'name': 'My Wishlist',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            wishlist_ref.set(wishlist_data)
            return WishlistProductsResponse(
                success=True,
                message="Empty wishlist created",
                wishlist=Wishlist(**wishlist_data),
                products=[],
                total_items=0
            )
        
        wishlist_data = wishlist_doc.to_dict()
        wishlist = Wishlist(**wishlist_data)
        
        # Populate product details
        products = []
        for item in wishlist.items:
            product_doc = db.collection('products').document(item.product_id).get()
            if product_doc.exists:
                product_data = product_doc.to_dict()
                product_data['product_id'] = product_doc.id
                product_data['wishlist_notes'] = item.notes
                product_data['wishlist_priority'] = item.priority
                product_data['wishlist_added_at'] = item.added_at
                products.append(product_data)
        
        return WishlistProductsResponse(
            success=True,
            message="Wishlist retrieved successfully",
            wishlist=wishlist,
            products=products,
            total_items=len(products)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting wishlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve wishlist"
        )


@router.post("/add", response_model=WishlistResponse)
async def add_to_wishlist(
    request: WishlistAddRequest,
    current_user = Depends(get_current_active_user)
):
    """Add product to wishlist"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Check if product exists
        product_doc = db.collection('products').document(request.product_id).get()
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Get or create wishlist
        wishlist_ref = db.collection('wishlists').document(current_user.user_id)
        wishlist_doc = wishlist_ref.get()
        
        if wishlist_doc.exists:
            wishlist_data = wishlist_doc.to_dict()
            wishlist = Wishlist(**wishlist_data)
        else:
            wishlist = Wishlist(
                user_id=current_user.user_id,
                items=[],
                is_public=False,
                name='My Wishlist'
            )
        
        # Add item to wishlist
        if wishlist.add_item(
            product_id=request.product_id,
            notes=request.notes,
            priority=request.priority or 0
        ):
            # Save to Firestore
            wishlist.updated_at = datetime.utcnow()
            wishlist_ref.set(wishlist.to_firestore())
            
            return WishlistResponse(
                success=True,
                message="Product added to wishlist",
                wishlist=wishlist,
                total_items=len(wishlist.items)
            )
        else:
            return WishlistResponse(
                success=False,
                message="Product already in wishlist",
                wishlist=wishlist,
                total_items=len(wishlist.items)
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to wishlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add to wishlist"
        )


@router.delete("/{product_id}")
async def remove_from_wishlist(
    product_id: str,
    current_user = Depends(get_current_active_user)
):
    """Remove product from wishlist"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get wishlist
        wishlist_ref = db.collection('wishlists').document(current_user.user_id)
        wishlist_doc = wishlist_ref.get()
        
        if not wishlist_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Wishlist not found"
            )
        
        wishlist_data = wishlist_doc.to_dict()
        wishlist = Wishlist(**wishlist_data)
        
        # Remove item
        if wishlist.remove_item(product_id):
            # Save to Firestore
            wishlist.updated_at = datetime.utcnow()
            wishlist_ref.set(wishlist.to_firestore())
            
            return {
                "success": True,
                "message": "Product removed from wishlist",
                "total_items": len(wishlist.items)
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found in wishlist"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from wishlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove from wishlist"
        )


@router.delete("")
async def clear_wishlist(current_user = Depends(get_current_active_user)):
    """Clear entire wishlist"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Clear wishlist
        wishlist_ref = db.collection('wishlists').document(current_user.user_id)
        wishlist_ref.set({
            'user_id': current_user.user_id,
            'items': [],
            'is_public': False,
            'name': 'My Wishlist',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Wishlist cleared successfully"
        }
        
    except Exception as e:
        logger.error(f"Error clearing wishlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear wishlist"
        )


@router.get("/check/{product_id}")
async def check_wishlist_item(
    product_id: str,
    current_user = Depends(get_current_active_user)
):
    """Check if product is in wishlist"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get wishlist
        wishlist_ref = db.collection('wishlists').document(current_user.user_id)
        wishlist_doc = wishlist_ref.get()
        
        if not wishlist_doc.exists:
            return {
                "success": True,
                "in_wishlist": False
            }
        
        wishlist_data = wishlist_doc.to_dict()
        wishlist = Wishlist(**wishlist_data)
        
        return {
            "success": True,
            "in_wishlist": wishlist.has_product(product_id)
        }
        
    except Exception as e:
        logger.error(f"Error checking wishlist: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check wishlist"
        )
