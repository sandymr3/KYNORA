"""Recently Viewed Products API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging
from datetime import datetime

from models.recently_viewed import RecentlyViewed, RecentlyViewedResponse
from core.database import get_firestore_client
from utils.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recently-viewed", tags=["Recently Viewed"])


@router.post("/{product_id}")
async def track_product_view(
    product_id: str,
    current_user = Depends(get_current_active_user)
):
    """Track that a user viewed a product"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Check if product exists
        product_doc = db.collection('products').document(product_id).get()
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Get or create recently viewed document
        viewed_ref = db.collection('recently_viewed').document(current_user.user_id)
        viewed_doc = viewed_ref.get()
        
        if viewed_doc.exists:
            recently_viewed = RecentlyViewed(**viewed_doc.to_dict())
        else:
            recently_viewed = RecentlyViewed(
                user_id=current_user.user_id,
                products=[]
            )
        
        # Add product to recently viewed
        recently_viewed.add_product(product_id)
        recently_viewed.updated_at = datetime.utcnow()
        
        # Save to Firestore
        viewed_ref.set(recently_viewed.to_firestore())
        
        return {
            "success": True,
            "message": "Product view tracked",
            "total_viewed": len(recently_viewed.products)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking product view: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track product view"
        )


@router.get("", response_model=RecentlyViewedResponse)
async def get_recently_viewed(
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_active_user)
):
    """Get user's recently viewed products"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get recently viewed document
        viewed_ref = db.collection('recently_viewed').document(current_user.user_id)
        viewed_doc = viewed_ref.get()
        
        if not viewed_doc.exists:
            return RecentlyViewedResponse(
                success=True,
                message="No recently viewed products",
                products=[],
                total_items=0
            )
        
        recently_viewed = RecentlyViewed(**viewed_doc.to_dict())
        
        # Get product details
        product_ids = recently_viewed.get_product_ids(limit)
        products = []
        
        for product_id in product_ids:
            product_doc = db.collection('products').document(product_id).get()
            if product_doc.exists:
                product_data = product_doc.to_dict()
                product_data['product_id'] = product_doc.id
                
                # Add view metadata
                for viewed_product in recently_viewed.products:
                    if viewed_product.product_id == product_id:
                        product_data['viewed_at'] = viewed_product.viewed_at
                        product_data['view_count'] = viewed_product.view_count
                        break
                
                products.append(product_data)
        
        return RecentlyViewedResponse(
            success=True,
            message="Recently viewed products retrieved",
            products=products,
            total_items=len(products)
        )
        
    except Exception as e:
        logger.error(f"Error getting recently viewed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recently viewed products"
        )


@router.delete("")
async def clear_recently_viewed(current_user = Depends(get_current_active_user)):
    """Clear user's recently viewed products"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Clear recently viewed
        viewed_ref = db.collection('recently_viewed').document(current_user.user_id)
        viewed_ref.set({
            'user_id': current_user.user_id,
            'products': [],
            'max_items': 20,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Recently viewed products cleared"
        }
        
    except Exception as e:
        logger.error(f"Error clearing recently viewed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear recently viewed products"
        )


# Public endpoint for anonymous tracking (stores in session/cookies on frontend)
@router.post("/anonymous/{product_id}")
async def track_anonymous_view(product_id: str):
    """Track anonymous product view (for non-logged-in users)"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Just update view count for the product
        product_ref = db.collection('products').document(product_id)
        product_doc = product_ref.get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Increment view count
        current_views = product_doc.to_dict().get('view_count', 0)
        product_ref.update({'view_count': current_views + 1})
        
        return {
            "success": True,
            "message": "Anonymous view tracked",
            "product_id": product_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking anonymous view: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to track view"
        )
