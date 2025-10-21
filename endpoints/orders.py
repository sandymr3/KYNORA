"""
Order management endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from firebase_admin import firestore
import logging

from core.database import get_db
from core.dependencies import require_authenticated_user, require_admin
from core.utils import (
    create_success_response, create_error_response, 
    generate_id, generate_order_number, calculate_order_total
)
from core.models import OrderCreate, OrderStatusUpdate, OrderCancel

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("")
async def create_order(
    order_data: OrderCreate,
    current_user: dict = Depends(require_authenticated_user)
):
    """Create new order"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={
                'order_id': 'test_order_123',
                'order_number': 'ORD-TEST-123'
            },
            message="Order created (development mode)"
        )
    
    try:
        # Generate order ID and number
        order_id = generate_id("ord_")
        order_number = generate_order_number()
        
        # Calculate totals
        totals = calculate_order_total(order_data.items, shipping=10.0, tax_rate=0.08)
        
        # Create order document
        order_doc = {
            'order_number': order_number,
            'user_id': current_user['id'],
            'user_email': current_user.get('email'),
            'user_name': current_user.get('name'),
            
            'items': [item.dict() for item in order_data.items],
            'shipping_address': order_data.shipping_address.dict(),
            'billing_address': order_data.billing_address.dict() if order_data.billing_address else order_data.shipping_address.dict(),
            
            'payment_method': order_data.payment_method,
            'shipping_method': order_data.shipping_method,
            
            'subtotal': totals['subtotal'],
            'tax': totals['tax'],
            'shipping': totals['shipping'],
            'total': totals['total'],
            
            'status': 'pending',
            'payment_status': 'pending',
            'fulfillment_status': 'unfulfilled',
            
            'notes': order_data.notes,
            'coupon_code': order_data.coupon_code,
            
            'timeline': [{
                'event': 'order_created',
                'timestamp': datetime.utcnow(),
                'description': 'Order created'
            }],
            
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Save to Firestore
        db.collection('orders').document(order_id).set(order_doc)
        
        # Clear user's cart
        cart_ref = db.collection('carts').document(current_user['id'])
        cart_ref.update({
            'items': [],
            'updated_at': datetime.utcnow()
        })
        
        # Update product inventory (in production, use transactions)
        for item in order_data.items:
            product_ref = db.collection('products').document(item.product_id)
            product_ref.update({
                'inventory_quantity': firestore.Increment(-item.quantity),
                'updated_at': datetime.utcnow()
            })
        
        logger.info(f"Order created: {order_id} for user: {current_user['id']}")
        
        return create_success_response(
            data={
                'order_id': order_id,
                'order_number': order_number,
                'total': totals['total']
            },
            message="Order created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating order: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/my-orders")
async def get_my_orders(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(require_authenticated_user)
):
    """Get user's order history"""
    try:
        db = get_db()
        
        if not db:
            return create_success_response(
                data={'orders': [], 'total': 0}
            )
        
        # Build query
        query = db.collection('orders').where('user_id', '==', current_user['id'])
        
        if status:
            query = query.where('status', '==', status)
        
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING)
        
        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        query = query.limit(limit)
        
        orders = []
        for doc in query.stream():
            order = doc.to_dict()
            order['id'] = doc.id
            order['order_id'] = doc.id
            orders.append(order)
        
        return create_success_response(
            data={
                'orders': orders,
                'total': len(orders),
                'limit': limit,
                'offset': offset
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting user orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders"
        )

@router.get("/{order_id}")
async def get_order(
    order_id: str = Path(..., description="Order ID"),
    include_items: bool = Query(True),
    current_user: dict = Depends(require_authenticated_user)
):
    """Get order by ID"""
    try:
        db = get_db()
        
        if not db:
            return create_error_response("Database not available", "DB_ERROR")
        
        doc = db.collection('orders').document(order_id).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = doc.to_dict()
        
        # Check if user owns the order or is admin
        if order['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        order['id'] = doc.id
        order['order_id'] = doc.id
        
        if not include_items:
            order.pop('items', None)
        
        return create_success_response(data=order)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order"
        )

@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str = Path(..., description="Order ID"),
    status_data: OrderStatusUpdate = Body(...),
    current_user: dict = Depends(require_admin)
):
    """Update order status (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = doc.to_dict()
        
        # Prepare update
        update_data = {
            'status': status_data.status,
            'updated_at': datetime.utcnow()
        }
        
        # Add optional fields
        if status_data.reason:
            update_data['status_reason'] = status_data.reason
        if status_data.tracking_number:
            update_data['tracking_number'] = status_data.tracking_number
        if status_data.expected_delivery:
            update_data['expected_delivery'] = status_data.expected_delivery
        
        # Update fulfillment status based on order status
        if status_data.status == 'shipped':
            update_data['fulfillment_status'] = 'partial'
        elif status_data.status == 'delivered':
            update_data['fulfillment_status'] = 'fulfilled'
        
        # Add to timeline
        timeline = order.get('timeline', [])
        timeline.append({
            'event': f'status_changed_to_{status_data.status}',
            'timestamp': datetime.utcnow(),
            'description': f'Order status changed to {status_data.status}',
            'user_id': current_user['id'],
            'user_name': current_user.get('name'),
            'reason': status_data.reason
        })
        update_data['timeline'] = timeline
        
        doc_ref.update(update_data)
        
        logger.info(f"Order status updated: {order_id} to {status_data.status} by user: {current_user['id']}")
        
        return create_success_response(
            message=f"Order status updated to {status_data.status}",
            data={'order_id': order_id, 'new_status': status_data.status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.patch("/{order_id}/cancel")
async def cancel_order(
    order_id: str = Path(..., description="Order ID"),
    cancel_data: OrderCancel = Body(...),
    current_user: dict = Depends(require_authenticated_user)
):
    """Cancel order"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = doc.to_dict()
        
        # Check if user owns the order or is admin
        if order['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        # Check if order can be cancelled
        if order['status'] in ['shipped', 'delivered', 'cancelled']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel order with status: {order['status']}"
            )
        
        # Update order
        timeline = order.get('timeline', [])
        timeline.append({
            'event': 'order_cancelled',
            'timestamp': datetime.utcnow(),
            'description': f'Order cancelled: {cancel_data.reason}',
            'user_id': current_user['id'],
            'user_name': current_user.get('name')
        })
        
        doc_ref.update({
            'status': 'cancelled',
            'cancel_reason': cancel_data.reason,
            'cancelled_at': datetime.utcnow(),
            'cancelled_by': current_user['id'],
            'timeline': timeline,
            'updated_at': datetime.utcnow()
        })
        
        # Restore inventory
        for item in order.get('items', []):
            product_ref = db.collection('products').document(item['product_id'])
            product_ref.update({
                'inventory_quantity': firestore.Increment(item['quantity']),
                'updated_at': datetime.utcnow()
            })
        
        logger.info(f"Order cancelled: {order_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Order cancelled successfully",
            data={'order_id': order_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/{order_id}/tracking")
async def get_order_tracking(
    order_id: str = Path(..., description="Order ID"),
    current_user: dict = Depends(require_authenticated_user)
):
    """Get order tracking information"""
    try:
        db = get_db()
        
        if not db:
            return create_error_response("Database not available", "DB_ERROR")
        
        doc = db.collection('orders').document(order_id).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = doc.to_dict()
        
        # Check if user owns the order or is admin
        if order['user_id'] != current_user['id'] and current_user.get('role') != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        tracking_info = {
            'order_id': order_id,
            'order_number': order.get('order_number'),
            'status': order.get('status'),
            'tracking_number': order.get('tracking_number'),
            'carrier': order.get('carrier', 'Standard Shipping'),
            'expected_delivery': order.get('expected_delivery'),
            'timeline': order.get('timeline', [])
        }
        
        return create_success_response(data=tracking_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order tracking: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tracking information"
        )

@router.post("/{order_id}/timeline")
async def add_order_timeline_event(
    order_id: str = Path(..., description="Order ID"),
    event: str = Body(..., description="Event name"),
    description: str = Body(..., description="Event description"),
    metadata: Optional[Dict[str, Any]] = Body(None, description="Event metadata"),
    current_user: dict = Depends(require_admin)
):
    """Add timeline event to order (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        doc_ref = db.collection('orders').document(order_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        order = doc.to_dict()
        timeline = order.get('timeline', [])
        
        # Add new event
        timeline_event = {
            'event': event,
            'timestamp': datetime.utcnow(),
            'description': description,
            'user_id': current_user['id'],
            'user_name': current_user.get('name')
        }
        
        if metadata:
            timeline_event['metadata'] = metadata
        
        timeline.append(timeline_event)
        
        doc_ref.update({
            'timeline': timeline,
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Timeline event added to order: {order_id} - {event}")
        
        return create_success_response(
            message="Timeline event added successfully",
            data={'order_id': order_id, 'event': event}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding timeline event: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
