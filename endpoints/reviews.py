"""
Review management endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from typing import Optional, List
from datetime import datetime
from firebase_admin import firestore
import logging

from core.database import get_db
from core.dependencies import require_authenticated_user, require_admin
from core.utils import create_success_response, create_error_response, generate_id, sanitize_input
from core.models import ReviewCreate, ReviewUpdate, ReviewResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/products/{product_id}")
async def get_product_reviews(
    product_id: str = Path(..., description="Product ID"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("created_at", pattern="^(created_at|rating|helpful_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """Get reviews for a specific product"""
    try:
        db = get_db()
        
        if not db:
            # Return sample reviews in development mode
            sample_reviews = [
                {
                    "id": "rev_001",
                    "product_id": product_id,
                    "user_id": "user_001",
                    "user_name": "John Doe",
                    "rating": 5,
                    "title": "Great product!",
                    "comment": "Excellent quality and fast delivery.",
                    "verified_purchase": True,
                    "helpful_count": 5,
                    "created_at": datetime.utcnow().isoformat()
                }
            ]
            return create_success_response(
                data={
                    'reviews': sample_reviews,
                    'total': 1,
                    'average_rating': 5.0
                }
            )
        
        # Query reviews
        query = db.collection('reviews').where('product_id', '==', product_id)
        
        # Apply sorting
        if sort_by == 'rating':
            query = query.order_by('rating', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
        elif sort_by == 'helpful_count':
            query = query.order_by('helpful_count', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
        else:
            query = query.order_by('created_at', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
        
        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        query = query.limit(limit)
        
        reviews = []
        total_rating = 0
        review_count = 0
        
        for doc in query.stream():
            review = doc.to_dict()
            review['id'] = doc.id
            review['review_id'] = doc.id
            reviews.append(review)
            total_rating += review.get('rating', 0)
            review_count += 1
        
        average_rating = total_rating / review_count if review_count > 0 else 0
        
        return create_success_response(
            data={
                'reviews': reviews,
                'total': review_count,
                'average_rating': round(average_rating, 1),
                'limit': limit,
                'offset': offset
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting product reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reviews"
        )

@router.post("")
async def create_review(
    review_data: ReviewCreate,
    current_user: dict = Depends(require_authenticated_user)
):
    """Create a new review"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={'review_id': 'test_review_123'},
            message="Review created (development mode)"
        )
    
    try:
        # Check if user has already reviewed this product
        existing_query = db.collection('reviews') \
            .where('product_id', '==', review_data.product_id) \
            .where('user_id', '==', current_user['id']) \
            .limit(1)
        
        existing_reviews = list(existing_query.stream())
        if existing_reviews:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this product"
            )
        
        # Check if user has purchased this product
        orders_query = db.collection('orders') \
            .where('user_id', '==', current_user['id']) \
            .where('status', 'in', ['delivered', 'completed'])
        
        verified_purchase = False
        for order_doc in orders_query.stream():
            order = order_doc.to_dict()
            for item in order.get('items', []):
                if item.get('product_id') == review_data.product_id:
                    verified_purchase = True
                    break
            if verified_purchase:
                break
        
        # Generate review ID
        review_id = generate_id("rev_")
        
        # Create review document
        review_doc = {
            'product_id': review_data.product_id,
            'user_id': current_user['id'],
            'user_name': current_user.get('name', 'Anonymous'),
            'user_email': current_user.get('email'),
            'rating': review_data.rating,
            'title': sanitize_input(review_data.title) if review_data.title else None,
            'comment': sanitize_input(review_data.comment) if review_data.comment else None,
            'images': review_data.images or [],
            'verified_purchase': verified_purchase,
            'helpful_count': 0,
            'helpful_users': [],
            'status': 'approved',  # Auto-approve for now
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.collection('reviews').document(review_id).set(review_doc)
        
        # Update product's average rating
        product_ref = db.collection('products').document(review_data.product_id)
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            current_avg = product.get('average_rating', 0)
            current_count = product.get('review_count', 0)
            
            # Calculate new average
            new_count = current_count + 1
            new_avg = ((current_avg * current_count) + review_data.rating) / new_count
            
            product_ref.update({
                'average_rating': round(new_avg, 1),
                'review_count': new_count,
                'updated_at': datetime.utcnow()
            })
        
        logger.info(f"Review created: {review_id} for product: {review_data.product_id} by user: {current_user['id']}")
        
        return create_success_response(
            data={'review_id': review_id},
            message="Review created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{review_id}")
async def update_review(
    review_id: str = Path(..., description="Review ID"),
    review_data: ReviewUpdate = Body(...),
    current_user: dict = Depends(require_authenticated_user)
):
    """Update an existing review"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Review updated (development mode)"
        )
    
    try:
        doc_ref = db.collection('reviews').document(review_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review = doc.to_dict()
        
        # Check if user owns the review
        if review['user_id'] != current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own reviews"
            )
        
        # Prepare update data
        update_data = {}
        if review_data.rating is not None:
            update_data['rating'] = review_data.rating
        if review_data.title is not None:
            update_data['title'] = sanitize_input(review_data.title)
        if review_data.comment is not None:
            update_data['comment'] = sanitize_input(review_data.comment)
        if review_data.images is not None:
            update_data['images'] = review_data.images
        
        update_data['updated_at'] = datetime.utcnow()
        update_data['edited'] = True
        
        doc_ref.update(update_data)
        
        # Update product's average rating if rating changed
        if review_data.rating and review_data.rating != review['rating']:
            product_ref = db.collection('products').document(review['product_id'])
            product_doc = product_ref.get()
            
            if product_doc.exists:
                product = product_doc.to_dict()
                current_avg = product.get('average_rating', 0)
                current_count = product.get('review_count', 0)
                
                if current_count > 0:
                    # Recalculate average
                    total_rating = (current_avg * current_count) - review['rating'] + review_data.rating
                    new_avg = total_rating / current_count
                    
                    product_ref.update({
                        'average_rating': round(new_avg, 1),
                        'updated_at': datetime.utcnow()
                    })
        
        logger.info(f"Review updated: {review_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Review updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{review_id}")
async def delete_review(
    review_id: str = Path(..., description="Review ID"),
    current_user: dict = Depends(require_authenticated_user)
):
    """Delete a review"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Review deleted (development mode)"
        )
    
    try:
        doc_ref = db.collection('reviews').document(review_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review = doc.to_dict()
        
        # Check if user owns the review or is admin
        if review['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Update product's average rating
        product_ref = db.collection('products').document(review['product_id'])
        product_doc = product_ref.get()
        
        if product_doc.exists:
            product = product_doc.to_dict()
            current_avg = product.get('average_rating', 0)
            current_count = product.get('review_count', 0)
            
            if current_count > 1:
                # Recalculate average
                total_rating = (current_avg * current_count) - review['rating']
                new_count = current_count - 1
                new_avg = total_rating / new_count
                
                product_ref.update({
                    'average_rating': round(new_avg, 1),
                    'review_count': new_count,
                    'updated_at': datetime.utcnow()
                })
            else:
                # No more reviews
                product_ref.update({
                    'average_rating': 0,
                    'review_count': 0,
                    'updated_at': datetime.utcnow()
                })
        
        # Delete the review
        doc_ref.delete()
        
        logger.info(f"Review deleted: {review_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Review deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{review_id}/helpful")
async def mark_review_helpful(
    review_id: str = Path(..., description="Review ID"),
    current_user: dict = Depends(require_authenticated_user)
):
    """Mark a review as helpful"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Review marked as helpful (development mode)"
        )
    
    try:
        doc_ref = db.collection('reviews').document(review_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        review = doc.to_dict()
        
        # Check if user has already marked this review as helpful
        helpful_users = review.get('helpful_users', [])
        
        if current_user['id'] in helpful_users:
            # Remove the helpful mark
            helpful_users.remove(current_user['id'])
            helpful_count = max(0, review.get('helpful_count', 0) - 1)
            message = "Helpful mark removed"
        else:
            # Add the helpful mark
            helpful_users.append(current_user['id'])
            helpful_count = review.get('helpful_count', 0) + 1
            message = "Review marked as helpful"
        
        doc_ref.update({
            'helpful_users': helpful_users,
            'helpful_count': helpful_count,
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Review helpful status updated: {review_id} by user: {current_user['id']}")
        
        return create_success_response(
            message=message,
            data={'helpful_count': helpful_count}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error marking review as helpful: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/{review_id}/response")
async def respond_to_review(
    review_id: str = Path(..., description="Review ID"),
    response_data: ReviewResponse = Body(...),
    current_user: dict = Depends(require_authenticated_user)
):
    """Respond to a review (seller/admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Response added (development mode)"
        )
    
    try:
        # Check if user is seller or admin
        if current_user.get('role') not in ['seller', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only sellers and admins can respond to reviews"
            )
        
        doc_ref = db.collection('reviews').document(review_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Review not found"
            )
        
        # Add seller response
        doc_ref.update({
            'seller_response': sanitize_input(response_data.response),
            'seller_response_at': datetime.utcnow(),
            'seller_response_by': current_user['id'],
            'seller_name': current_user.get('name', 'Seller'),
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Seller response added to review: {review_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Response added successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error responding to review: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
