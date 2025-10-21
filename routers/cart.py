"""Shopping Cart API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from services.cart_service import CartService
from models.cart import (
    CartResponse, CartAddItem, CartUpdateItem, 
    CartApplyCoupon, CartSummaryResponse, CartSummary
)
from utils.auth import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cart", tags=["Cart"])
cart_service = CartService()


@router.get("", response_model=CartResponse)
async def get_cart(current_user = Depends(get_current_active_user)):
    """Get user's cart"""
    try:
        cart = await cart_service.get_cart(current_user.user_id)
        
        if not cart:
            cart = await cart_service.create_cart(current_user.user_id)
        
        return CartResponse(
            success=True,
            message="Cart retrieved successfully",
            cart=cart
        )
        
    except Exception as e:
        logger.error(f"Error getting cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cart"
        )


@router.post("/items", response_model=CartResponse)
async def add_to_cart(
    item_data: CartAddItem,
    current_user = Depends(get_current_active_user)
):
    """Add item to cart"""
    try:
        result = await cart_service.add_item(
            user_id=current_user.user_id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            variants=item_data.selected_variants.dict() if item_data.selected_variants else None
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return CartResponse(
            success=True,
            message=result["message"],
            cart=result["cart"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding item to cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add item to cart"
        )


@router.put("/items/{cart_item_id}", response_model=CartResponse)
async def update_cart_item(
    cart_item_id: str,
    update_data: CartUpdateItem,
    current_user = Depends(get_current_active_user)
):
    """Update cart item quantity"""
    try:
        result = await cart_service.update_quantity(
            user_id=current_user.user_id,
            cart_item_id=cart_item_id,
            quantity=update_data.quantity
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return CartResponse(
            success=True,
            message=result["message"],
            cart=result["cart"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cart item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update cart item"
        )


@router.delete("/items/{cart_item_id}", response_model=CartResponse)
async def remove_from_cart(
    cart_item_id: str,
    current_user = Depends(get_current_active_user)
):
    """Remove item from cart"""
    try:
        result = await cart_service.remove_item(
            user_id=current_user.user_id,
            cart_item_id=cart_item_id
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["message"]
            )
        
        return CartResponse(
            success=True,
            message=result["message"],
            cart=result["cart"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing item from cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove item from cart"
        )


@router.delete("", response_model=CartResponse)
async def clear_cart(current_user = Depends(get_current_active_user)):
    """Clear entire cart"""
    try:
        result = await cart_service.clear_cart(current_user.user_id)
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return CartResponse(
            success=True,
            message=result["message"],
            cart=result["cart"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cart"
        )


@router.get("/summary", response_model=CartSummaryResponse)
async def get_cart_summary(current_user = Depends(get_current_active_user)):
    """Get cart summary with totals"""
    try:
        cart = await cart_service.get_cart(current_user.user_id)
        
        if not cart:
            cart = await cart_service.create_cart(current_user.user_id)
        
        summary = CartSummary(
            item_count=cart.get_item_count(),
            subtotal=cart.subtotal,
            total=cart.total,
            has_coupon=cart.applied_coupon is not None
        )
        
        return CartSummaryResponse(
            success=True,
            message="Cart summary retrieved",
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Error getting cart summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cart summary"
        )


@router.post("/coupon", response_model=CartResponse)
async def apply_coupon(
    coupon_data: CartApplyCoupon,
    current_user = Depends(get_current_active_user)
):
    """Apply coupon to cart"""
    try:
        result = await cart_service.apply_coupon(
            user_id=current_user.user_id,
            coupon_code=coupon_data.coupon_code
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["message"]
            )
        
        return CartResponse(
            success=True,
            message=result["message"],
            cart=result["cart"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying coupon: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to apply coupon"
        )


@router.post("/validate")
async def validate_cart(current_user = Depends(get_current_active_user)):
    """Validate cart items (check inventory and prices)"""
    try:
        result = await cart_service.validate_cart(current_user.user_id)
        
        return {
            "success": True,
            "valid": result["valid"],
            "issues": result.get("issues", []),
            "message": result.get("message", "Cart validated")
        }
        
    except Exception as e:
        logger.error(f"Error validating cart: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate cart"
        )
