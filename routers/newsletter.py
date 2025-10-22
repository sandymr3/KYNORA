"""Newsletter subscription API endpoints"""

from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import Optional
import logging
import secrets
from datetime import datetime, timedelta

from models.newsletter import (
    NewsletterSubscriber, NewsletterSignupRequest,
    NewsletterResponse, SubscriptionStatus,
    NewsletterUpdateRequest, NewsletterUnsubscribeRequest,
    NewsletterBulkResponse
)
from core.database import get_firestore_client
from utils.auth import get_current_user_optional, require_admin

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/newsletter", tags=["Newsletter"])


@router.post("/subscribe", response_model=NewsletterResponse)
async def subscribe_to_newsletter(
    request: NewsletterSignupRequest,
    client_request: Request,
    current_user = Depends(get_current_user_optional)
):
    """Subscribe to newsletter"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Check if email already subscribed
        subscriber_ref = db.collection('newsletter_subscribers').document(request.email)
        subscriber_doc = subscriber_ref.get()
        
        if subscriber_doc.exists:
            subscriber_data = subscriber_doc.to_dict()
            
            # If previously unsubscribed, reactivate
            if subscriber_data.get('status') == SubscriptionStatus.UNSUBSCRIBED:
                subscriber_data['status'] = SubscriptionStatus.ACTIVE
                subscriber_data['subscribed_at'] = datetime.utcnow()
                subscriber_data['unsubscribed_at'] = None
                subscriber_ref.update(subscriber_data)
                
                return NewsletterResponse(
                    success=True,
                    message="Successfully resubscribed to newsletter",
                    subscriber=NewsletterSubscriber(**subscriber_data)
                )
            else:
                return NewsletterResponse(
                    success=False,
                    message="Email already subscribed to newsletter",
                    subscriber=NewsletterSubscriber(**subscriber_data)
                )
        
        # Create new subscriber
        confirmation_token = secrets.token_urlsafe(32)
        
        subscriber = NewsletterSubscriber(
            email=request.email,
            name=request.name,
            user_id=current_user.user_id if current_user else None,
            status=SubscriptionStatus.PENDING,  # Will be active after email confirmation
            preferences=request.preferences if request.preferences else None,
            source=request.source,
            ip_address=client_request.client.host if client_request.client else None,
            confirmation_token=confirmation_token
        )
        
        # Save to Firestore
        subscriber_ref.set(subscriber.to_firestore())
        
        # In production, send confirmation email here
        # For now, auto-confirm for testing
        subscriber_ref.update({
            'status': SubscriptionStatus.ACTIVE,
            'confirmed': True,
            'confirmed_at': datetime.utcnow()
        })
        
        subscriber.status = SubscriptionStatus.ACTIVE
        subscriber.confirmed = True
        
        return NewsletterResponse(
            success=True,
            message="Successfully subscribed to newsletter",
            subscriber=subscriber
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subscribing to newsletter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to newsletter"
        )


@router.post("/unsubscribe")
async def unsubscribe_from_newsletter(request: NewsletterUnsubscribeRequest):
    """Unsubscribe from newsletter"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get subscriber
        subscriber_ref = db.collection('newsletter_subscribers').document(request.email)
        subscriber_doc = subscriber_ref.get()
        
        if not subscriber_doc.exists:
            return {
                "success": False,
                "message": "Email not found in newsletter subscribers"
            }
        
        # Update subscription status
        subscriber_ref.update({
            'status': SubscriptionStatus.UNSUBSCRIBED,
            'unsubscribed_at': datetime.utcnow(),
            'unsubscribe_reason': request.reason
        })
        
        return {
            "success": True,
            "message": "Successfully unsubscribed from newsletter"
        }
        
    except Exception as e:
        logger.error(f"Error unsubscribing from newsletter: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe from newsletter"
        )


@router.put("/preferences")
async def update_newsletter_preferences(
    request: NewsletterUpdateRequest,
    current_user = Depends(get_current_user_optional)
):
    """Update newsletter preferences"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Determine email to use
        if current_user and current_user.email:
            email = current_user.email
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Please log in to update preferences"
            )
        
        # Get subscriber
        subscriber_ref = db.collection('newsletter_subscribers').document(email)
        subscriber_doc = subscriber_ref.get()
        
        if not subscriber_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not subscribed to newsletter"
            )
        
        # Update preferences
        subscriber_ref.update({
            'preferences': request.preferences.dict(),
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Newsletter preferences updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.get("/status")
async def check_subscription_status(
    email: Optional[str] = Query(None),
    current_user = Depends(get_current_user_optional)
):
    """Check newsletter subscription status"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Determine email to check
        check_email = email or (current_user.email if current_user else None)
        
        if not check_email:
            return {
                "success": False,
                "subscribed": False,
                "message": "No email provided"
            }
        
        # Get subscriber
        subscriber_doc = db.collection('newsletter_subscribers').document(check_email).get()
        
        if not subscriber_doc.exists:
            return {
                "success": True,
                "subscribed": False,
                "status": None
            }
        
        subscriber_data = subscriber_doc.to_dict()
        
        return {
            "success": True,
            "subscribed": subscriber_data.get('status') == SubscriptionStatus.ACTIVE,
            "status": subscriber_data.get('status'),
            "preferences": subscriber_data.get('preferences', {})
        }
        
    except Exception as e:
        logger.error(f"Error checking subscription: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check subscription status"
        )


@router.get("/admin/stats", response_model=NewsletterBulkResponse)
async def get_newsletter_stats(
    current_user = Depends(require_admin)
):
    """Get newsletter statistics (admin only)"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get all subscribers
        subscribers_ref = db.collection('newsletter_subscribers')
        all_subscribers = subscribers_ref.stream()
        
        total_count = 0
        active_count = 0
        recent_count = 0
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        for doc in all_subscribers:
            data = doc.to_dict()
            total_count += 1
            
            if data.get('status') == SubscriptionStatus.ACTIVE:
                active_count += 1
            
            subscribed_at = data.get('subscribed_at')
            if subscribed_at and subscribed_at > week_ago:
                recent_count += 1
        
        return NewsletterBulkResponse(
            success=True,
            message="Newsletter statistics retrieved",
            total_subscribers=total_count,
            active_subscribers=active_count,
            recent_signups=recent_count
        )
        
    except Exception as e:
        logger.error(f"Error getting newsletter stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )
