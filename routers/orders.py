"""Order Management API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import logging

from services.order_service import OrderService
from models.order import (
    OrderCreate, OrderResponse, OrderListResponse,
    OrderCancel, OrderStatus
)
from utils.auth import get_current_active_user, require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])
order_service = OrderService()


@router.post("", response_model=OrderResponse)
async def create_order(
    order_data: OrderCreate,
    current_user = Depends(get_current_active_user)
):
    """Create order from cart"""
    try:
        result = await order_service.create_order(
            user_id=current_user.user_id,
            order_data=order_data
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return OrderResponse(
            success=True,
            message=result["message"],
            order=result["order"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create order"
        )


@router.get("", response_model=OrderListResponse)
async def get_user_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[OrderStatus] = None,
    current_user = Depends(get_current_active_user)
):
    """Get user's orders"""
    try:
        result = await order_service.get_user_orders(
            user_id=current_user.user_id,
            page=page,
            limit=limit,
            status=status
        )
        
        return OrderListResponse(
            success=True,
            message="Orders retrieved successfully",
            orders=result.get("orders", []),
            page=result.get("page", page),
            limit=result.get("limit", limit),
            total=result.get("total", 0),
            pages=result.get("pages", 1),
            has_next=result.get("has_next", False),
            has_prev=result.get("has_prev", False)
        )
        
    except Exception as e:
        logger.error(f"Error getting orders: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orders"
        )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get order details"""
    try:
        # Get order (validates user access)
        order = await order_service.get_order(
            order_id=order_id,
            user_id=current_user.user_id if current_user.role != 'admin' else None
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return OrderResponse(
            success=True,
            message="Order retrieved successfully",
            order=order
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve order"
        )


@router.patch("/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    cancel_data: OrderCancel,
    current_user = Depends(get_current_active_user)
):
    """Cancel order"""
    try:
        # Check if user owns the order
        order = await order_service.get_order(order_id, current_user.user_id)
        
        if not order and current_user.role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        result = await order_service.cancel_order(
            order_id=order_id,
            reason=cancel_data.reason,
            user_id=current_user.user_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling order: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel order"
        )


@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: str,
    status: OrderStatus,
    notes: Optional[str] = None,
    current_user = Depends(require_admin)
):
    """Update order status (admin only)"""
    try:
        result = await order_service.update_status(
            order_id=order_id,
            status=status,
            notes=notes,
            user_id=current_user.user_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return {
            "success": True,
            "message": result["message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update order status"
        )


@router.get("/{order_id}/tracking")
async def get_order_tracking(
    order_id: str,
    current_user = Depends(get_current_active_user)
):
    """Get order tracking information"""
    try:
        # Get order
        order = await order_service.get_order(
            order_id=order_id,
            user_id=current_user.user_id if current_user.role != 'admin' else None
        )
        
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )
        
        return {
            "success": True,
            "order_id": order_id,
            "order_number": order.order_number,
            "status": order.status,
            "fulfillment_status": order.fulfillment_status,
            "shipping": order.shipping.dict(),
            "timeline": [event.dict() for event in order.timeline]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tracking info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tracking information"
        )
