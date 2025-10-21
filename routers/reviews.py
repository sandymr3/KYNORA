"""Review API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import logging
from datetime import datetime

from config.firebase import db
from models.review import (
    Review, ReviewCreate, ReviewUpdate,
    ReviewResponse, ReviewListResponse, ReviewStats,
    ReviewStatsResponse, ReviewSellerResponse, ReviewStatus
)
from models.base import PaginationParams
from utils.auth import get_current_user, optional_user
from utils.helpers import Helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/products/{product_id}", response_model=ReviewListResponse)
async def get_product_reviews(
    product_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    rating: Optional[int] = Query(None, ge=1, le=5),
    verified_only: bool = False,
    with_images: bool = False,
    sort_by: str = Query("created_at", regex="^(created_at|rating|helpful_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """Get reviews for a product"""
    try:
        # Build query
        query = db.collection('reviews').where('product_id', '==', product_id)
        
        # Only show approved reviews to public
        query = query.where('status', '==', ReviewStatus.APPROVED)
        
        if rating:
            query = query.where('rating', '==', rating)
        if verified_only:
            query = query.where('verified_purchase', '==', True)
        
        # Get all matching reviews
        all_docs = list(query.stream())
        
        # Filter by images if requested
        if with_images:
            all_docs = [doc for doc in all_docs if doc.to_dict().get('images', [])]
        
        total = len(all_docs)
        
        # Sort reviews
        def get_sort_key(doc):
            data = doc.to_dict()
            if sort_by == 'rating':
                return data.get('rating', 0)
            elif sort_by == 'helpful_count':
                return data.get('helpful_count', 0)
            else:  # created_at
                return data.get('created_at', datetime.min)
        
        all_docs.sort(key=get_sort_key, reverse=(sort_order == 'desc'))
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to Review objects
        reviews = []
        for doc in paginated_docs:
            review_data = doc.to_dict()
            review_data['review_id'] = doc.id
            
            # Get user info
            user_doc = db.collection('users').document(review_data['user_id']).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                review_data['user_info'] = {
                    'user_id': review_data['user_id'],
                    'displayName': user_data.get('displayName', 'Anonymous'),
                    'avatar': user_data.get('avatar')
                }
            
            reviews.append(Review(**review_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        return ReviewListResponse(
            success=True,
            message="Reviews retrieved successfully",
            reviews=reviews,
            **pagination
        )
        
    except Exception as e:
        logger.error(f"Error getting product reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reviews"
        )


@router.get("/products/{product_id}/stats", response_model=ReviewStatsResponse)
async def get_product_review_stats(product_id: str):
    """Get review statistics for a product"""
    try:
        # Get all approved reviews for the product
        query = db.collection('reviews')\
            .where('product_id', '==', product_id)\
            .where('status', '==', ReviewStatus.APPROVED)
        
        reviews = list(query.stream())
        
        # Calculate statistics
        stats = ReviewStats(product_id=product_id)
        
        for doc in reviews:
            review_data = doc.to_dict()
            rating = review_data.get('rating', 0)
            
            stats.total_reviews += 1
            stats.rating_distribution[str(rating)] += 1
            
            if review_data.get('verified_purchase'):
                stats.verified_purchase_count += 1
            
            if review_data.get('images'):
                stats.with_images_count += 1
        
        # Calculate average rating
        stats.average_rating = stats.calculate_average()
        
        return ReviewStatsResponse(
            success=True,
            message="Review statistics retrieved",
            stats=stats
        )
        
    except Exception as e:
        logger.error(f"Error getting review stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve review statistics"
        )


@router.post("", response_model=ReviewResponse)
async def create_review(
    review_data: ReviewCreate,
    current_user=Depends(get_current_user)
):
    """Create a product review"""
    try:
        # Check if product exists
        product_doc = db.collection('products').document(review_data.product_id).get()
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if order exists and belongs to user
        order_doc = db.collection('orders').document(review_data.order_id).get()
        if not order_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order_data = order_doc.to_dict()
        if order_data.get('user_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only review products from your own orders"
            )
        
        # Check if order contains the product
        order_items = order_data.get('items', [])
        product_in_order = any(
            item.get('product_id') == review_data.product_id 
            for item in order_items
        )
        
        if not product_in_order:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found in order"
            )
        
        # Check if user already reviewed this product for this order
        existing_review = db.collection('reviews')\
            .where('user_id', '==', current_user.user_id)\
            .where('product_id', '==', review_data.product_id)\
            .where('order_id', '==', review_data.order_id)\
            .limit(1)\
            .get()
        
        if list(existing_review):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this product for this order"
            )
        
        # Generate review ID
        review_id = Helpers.generate_id("rev")
        
        # Create review
        review = Review(
            review_id=review_id,
            user_id=current_user.user_id,
            verified_purchase=True,  # Since we verified the order
            status=ReviewStatus.APPROVED,  # Auto-approve verified purchases
            **review_data.dict()
        )
        
        # Save to Firestore
        db.collection('reviews').document(review_id).set(
            review.to_firestore()
        )
        
        # Update product review stats (simplified)
        product_ref = db.collection('products').document(review_data.product_id)
        product_data = product_doc.to_dict()
        current_rating = product_data.get('average_rating', 0)
        current_count = product_data.get('review_count', 0)
        
        # Calculate new average
        new_count = current_count + 1
        new_rating = ((current_rating * current_count) + review.rating) / new_count
        
        product_ref.update({
            'average_rating': round(new_rating, 2),
            'review_count': new_count
        })
        
        return ReviewResponse(
            success=True,
            message="Review created successfully",
            review=review
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review"
        )


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: str,
    review_update: ReviewUpdate,
    current_user=Depends(get_current_user)
):
    """Update a review"""
    try:
        # Get review
        review_doc = db.collection('reviews').document(review_id).get()
        
        if not review_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review_data = review_doc.to_dict()
        
        # Check ownership
        if review_data.get('user_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews"
            )
        
        # Update fields
        update_data = review_update.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()
        
        # Update in Firestore
        db.collection('reviews').document(review_id).update(update_data)
        
        # Get updated review
        updated_doc = db.collection('reviews').document(review_id).get()
        updated_data = updated_doc.to_dict()
        updated_data['review_id'] = review_id
        updated_review = Review(**updated_data)
        
        return ReviewResponse(
            success=True,
            message="Review updated successfully",
            review=updated_review
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update review"
        )


@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    current_user=Depends(get_current_user)
):
    """Delete a review"""
    try:
        # Get review
        review_doc = db.collection('reviews').document(review_id).get()
        
        if not review_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review_data = review_doc.to_dict()
        
        # Check ownership or admin
        if review_data.get('user_id') != current_user.user_id and current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own reviews"
            )
        
        # Delete review
        db.collection('reviews').document(review_id).delete()
        
        # Update product review stats (simplified)
        product_id = review_data.get('product_id')
        if product_id:
            product_ref = db.collection('products').document(product_id)
            product_doc = product_ref.get()
            
            if product_doc.exists:
                product_data = product_doc.to_dict()
                current_rating = product_data.get('average_rating', 0)
                current_count = max(0, product_data.get('review_count', 0) - 1)
                
                # Recalculate average (simplified - in production, recalculate from all reviews)
                if current_count > 0:
                    # This is a simplification - in production, recalculate from all remaining reviews
                    new_rating = current_rating
                else:
                    new_rating = 0
                
                product_ref.update({
                    'average_rating': round(new_rating, 2),
                    'review_count': current_count
                })
        
        return {
            "success": True,
            "message": "Review deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete review"
        )


@router.post("/{review_id}/helpful")
async def mark_review_helpful(
    review_id: str,
    is_helpful: bool = True,
    current_user=Depends(optional_user)
):
    """Mark a review as helpful or not helpful"""
    try:
        # Get review
        review_ref = db.collection('reviews').document(review_id)
        review_doc = review_ref.get()
        
        if not review_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Track user's helpful votes (simplified - in production use separate collection)
        if current_user:
            user_id = current_user.user_id
        else:
            # For anonymous users, we'd normally use session or IP tracking
            user_id = "anonymous"
        
        # Update helpful count (simplified - in production track individual votes)
        review_data = review_doc.to_dict()
        current_count = review_data.get('helpful_count', 0)
        
        if is_helpful:
            new_count = current_count + 1
        else:
            new_count = max(0, current_count - 1)
        
        review_ref.update({'helpful_count': new_count})
        
        return {
            "success": True,
            "message": "Review marked as helpful",
            "helpful_count": new_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking review helpful: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark review as helpful"
        )


# Alternative endpoint path for product reviews (matches frontend expectation)
@router.get("/../products/{product_id}/reviews", response_model=ReviewListResponse)
async def get_product_reviews_alt(
    product_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Alternative endpoint for getting product reviews"""
    return await get_product_reviews(
        product_id=product_id,
        page=page,
        limit=limit,
        rating=None,
        verified_only=False,
        with_images=False,
        sort_by="created_at",
        sort_order="desc"
    )
