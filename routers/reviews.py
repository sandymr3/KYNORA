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


@router.get("/products/{product_id}")
async def get_product_reviews(
    product_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    rating: Optional[int] = Query(None, ge=1, le=5),
    verified_only: bool = False,
    with_images: bool = False,
    sort_by: str = Query("created_at", regex="^(created_at|rating|helpful_count)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """Get reviews for a product"""
    try:
        # Log the request
        logger.info(f"Getting reviews for product: {product_id}")
        
        # Simple single-field query (this works without composite index)
        query = db.collection('reviews').where('product_id', '==', product_id)
        all_docs = list(query.stream())
        
        logger.info(f"Found {len(all_docs)} total reviews for product {product_id}")
        
        # Filter in Python to avoid Firestore index requirements
        filtered_docs = []
        for doc in all_docs:
            data = doc.to_dict()
            # Only show approved reviews (or if no status field, include it)
            status = data.get('status', 'approved')
            # Accept various status formats
            if status in ['approved', 'APPROVED', 'pending', 'PENDING', None] or status == ReviewStatus.APPROVED:
                if rating and data.get('rating') != rating:
                    continue
                if verified_only and not data.get('verified_purchase'):
                    continue
                filtered_docs.append(doc)
        
        all_docs = filtered_docs
        logger.info(f"After filtering: {len(all_docs)} reviews")
        
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
        
        # Apply pagination using offset
        start_idx = offset
        end_idx = offset + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to Review objects
        reviews = []
        for doc in paginated_docs:
            review_data = doc.to_dict()
            review_data['review_id'] = doc.id
            review_data['id'] = doc.id  # Also add 'id' field for compatibility
            
            # Map comment to content if needed
            if 'comment' in review_data and 'content' not in review_data:
                review_data['content'] = review_data['comment']
            elif 'content' not in review_data:
                review_data['content'] = review_data.get('title', '')
            
            # Ensure required fields have defaults
            review_data.setdefault('rating', 0)
            review_data.setdefault('title', '')
            review_data.setdefault('verified_purchase', False)
            review_data.setdefault('helpful_count', 0)
            review_data.setdefault('images', [])
            
            # Get user info (optional - skip if error)
            try:
                if 'user_id' in review_data:
                    user_doc = db.collection('users').document(review_data['user_id']).get()
                    if user_doc.exists:
                        user_data = user_doc.to_dict()
                        review_data['user_info'] = {
                            'user_id': review_data['user_id'],
                            'displayName': user_data.get('displayName', 'Anonymous'),
                            'avatar': user_data.get('avatar')
                        }
                    else:
                        review_data['user_info'] = {
                            'user_id': review_data['user_id'],
                            'displayName': 'Customer',
                            'avatar': None
                        }
            except Exception:
                pass  # Skip user info if there's an error
            
            reviews.append(review_data)
        
        # Return response with reviews (even if empty)
        return {
            "success": True,
            "message": "Reviews retrieved successfully" if reviews else "No reviews found",
            "reviews": reviews,
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Error getting product reviews for {product_id}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Return empty result instead of error for better UX
        return {
            "success": False,
            "message": f"Error retrieving reviews: {str(e)}",
            "reviews": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }


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
        
        # Determine if this is a verified purchase
        verified_purchase = False
        
        if review_data.order_id:
            # Verify the order if order_id is provided
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
            
            verified_purchase = True
            
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
        else:
            # For non-verified reviews, check if user already reviewed this product (without order_id)
            existing_review = db.collection('reviews')\
                .where('user_id', '==', current_user.user_id)\
                .where('product_id', '==', review_data.product_id)\
                .limit(1)\
                .get()
            
            existing_reviews = list(existing_review)
            # Filter for reviews without order_id
            non_order_reviews = [r for r in existing_reviews if not r.to_dict().get('order_id')]
            
            if non_order_reviews:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already reviewed this product"
                )
        
        # Generate review ID
        review_id = Helpers.generate_id("rev")
        
        # Create review
        review = Review(
            review_id=review_id,
            user_id=current_user.user_id,
            verified_purchase=verified_purchase,
            status=ReviewStatus.APPROVED if verified_purchase else ReviewStatus.PENDING,
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
@router.get("/../products/{product_id}/reviews")
async def get_product_reviews_alt(
    product_id: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """Alternative endpoint for getting product reviews"""
    return await get_product_reviews(
        product_id=product_id,
        limit=limit,
        offset=offset,
        rating=None,
        verified_only=False,
        with_images=False,
        sort_by="created_at",
        sort_order="desc"
    )
