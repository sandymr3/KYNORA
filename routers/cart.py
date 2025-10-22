"""Shopping Cart API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from datetime import datetime

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
        # Get or create cart
        cart_doc = cart_service.db.collection('carts').document(current_user.user_id).get()
        
        if not cart_doc.exists:
            # Create new cart
            logger.info(f"Creating new cart for user {current_user.user_id}")
            cart_data = {
                'cart_id': current_user.user_id,
                'user_id': current_user.user_id,
                'items': [],
                'subtotal': 0.0,
                'tax': 0.0,
                'discount': 0.0,
                'total': 0.0,
                'item_count': 0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            cart_service.db.collection('carts').document(current_user.user_id).set(cart_data)
            logger.info(f"Cart created successfully for user {current_user.user_id}")
            cart = cart_data
        else:
            cart = cart_doc.to_dict()
            logger.info(f"Retrieved existing cart for user {current_user.user_id} with {len(cart.get('items', []))} items")
            
            # Populate product info for items
            for item in cart.get('items', []):
                product_doc = cart_service.db.collection('products').document(item['product_id']).get()
                if product_doc.exists:
                    product_data = product_doc.to_dict()
                    item['product_info'] = {
                        'title': product_data.get('title'),
                        'price': product_data.get('price'),
                        'thumbnail': product_data.get('thumbnail', product_data.get('images', [''])[0] if product_data.get('images') else ''),
                        'in_stock': product_data.get('inventory_quantity', 0) > 0
                    }
        
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
        # Get current cart
        cart_doc = cart_service.db.collection('carts').document(current_user.user_id).get()
        
        if not cart_doc.exists:
            # Create new cart
            cart_data = {
                'cart_id': current_user.user_id,
                'user_id': current_user.user_id,
                'items': [],
                'subtotal': 0.0,
                'tax': 0.0,
                'discount': 0.0,
                'total': 0.0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
        else:
            cart_data = cart_doc.to_dict()
        
        # Get product details
        product_doc = cart_service.db.collection('products').document(item_data.product_id).get()
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check if product is in stock
        if product_data.get('inventory_quantity', 0) < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient stock"
            )
        
        # Check if item already in cart
        existing_item = None
        for idx, item in enumerate(cart_data.get('items', [])):
            if item['product_id'] == item_data.product_id:
                existing_item = idx
                break
        
        # Create cart item
        cart_item = {
            'cart_item_id': f"item_{datetime.utcnow().timestamp()}",
            'product_id': item_data.product_id,
            'quantity': item_data.quantity,
            'price': product_data.get('price', 0),
            'subtotal': product_data.get('price', 0) * item_data.quantity,
            'product_info': {
                'title': product_data.get('title'),
                'price': product_data.get('price'),
                'thumbnail': product_data.get('thumbnail', product_data.get('images', [''])[0] if product_data.get('images') else ''),
                'in_stock': True
            }
        }
        
        if existing_item is not None:
            # Update existing item
            cart_data['items'][existing_item]['quantity'] += item_data.quantity
            cart_data['items'][existing_item]['subtotal'] = cart_data['items'][existing_item]['price'] * cart_data['items'][existing_item]['quantity']
        else:
            # Add new item
            cart_data['items'].append(cart_item)
        
        # Recalculate totals
        subtotal = sum(item.get('subtotal', 0) for item in cart_data['items'])
        cart_data['subtotal'] = subtotal
        cart_data['total'] = subtotal + cart_data.get('tax', 0) - cart_data.get('discount', 0)
        cart_data['item_count'] = sum(item.get('quantity', 0) for item in cart_data['items'])
        cart_data['updated_at'] = datetime.utcnow()
        
        # Save cart
        cart_service.db.collection('carts').document(current_user.user_id).set(cart_data)
        
        return CartResponse(
            success=True,
            message="Item added to cart successfully",
            cart=cart_data
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
        # Get current cart
        cart_doc = cart_service.db.collection('carts').document(current_user.user_id).get()
        if not cart_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        cart_data = cart_doc.to_dict()
        
        # Find item to update
        item_found = False
        for item in cart_data.get('items', []):
            if item.get('cart_item_id') == cart_item_id or item.get('product_id') == cart_item_id:
                # Update quantity
                if update_data.quantity <= 0:
                    # Remove item if quantity is 0
                    cart_data['items'] = [i for i in cart_data['items'] if i.get('cart_item_id') != cart_item_id and i.get('product_id') != cart_item_id]
                else:
                    item['quantity'] = update_data.quantity
                    item['subtotal'] = item['price'] * update_data.quantity
                item_found = True
                break
        
        if not item_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )
        
        # Recalculate totals
        subtotal = sum(item.get('subtotal', 0) for item in cart_data['items'])
        cart_data['subtotal'] = subtotal
        cart_data['total'] = subtotal + cart_data.get('tax', 0) - cart_data.get('discount', 0)
        cart_data['item_count'] = sum(item.get('quantity', 0) for item in cart_data['items'])
        cart_data['updated_at'] = datetime.utcnow()
        
        # Save cart
        cart_service.db.collection('carts').document(current_user.user_id).set(cart_data)
        
        return CartResponse(
            success=True,
            message="Cart updated successfully",
            cart=cart_data
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
        # Get current cart
        cart_doc = cart_service.db.collection('carts').document(current_user.user_id).get()
        if not cart_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        cart_data = cart_doc.to_dict()
        
        # Remove item
        original_length = len(cart_data.get('items', []))
        cart_data['items'] = [i for i in cart_data['items'] if i.get('cart_item_id') != cart_item_id and i.get('product_id') != cart_item_id]
        
        if len(cart_data['items']) == original_length:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )
        
        # Recalculate totals
        subtotal = sum(item.get('subtotal', 0) for item in cart_data['items'])
        cart_data['subtotal'] = subtotal
        cart_data['total'] = subtotal + cart_data.get('tax', 0) - cart_data.get('discount', 0)
        cart_data['item_count'] = sum(item.get('quantity', 0) for item in cart_data['items'])
        cart_data['updated_at'] = datetime.utcnow()
        
        # Save cart
        cart_service.db.collection('carts').document(current_user.user_id).set(cart_data)
        
        return CartResponse(
            success=True,
            message="Item removed from cart",
            cart=cart_data
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
        # Reset cart to empty
        cart_data = {
            'cart_id': current_user.user_id,
            'user_id': current_user.user_id,
            'items': [],
            'subtotal': 0.0,
            'tax': 0.0,
            'discount': 0.0,
            'total': 0.0,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Save empty cart
        cart_service.db.collection('carts').document(current_user.user_id).set(cart_data)
        
        return CartResponse(
            success=True,
            message="Cart cleared successfully",
            cart=cart_data
        )
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
