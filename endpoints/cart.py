"""
Shopping cart endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body, status
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from core.database import get_db
from core.dependencies import require_authenticated_user
from core.utils import create_success_response, create_error_response, calculate_order_total
from core.models import CartItemAdd, CartItemUpdate, CartSync

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("")
async def get_cart(current_user: dict = Depends(require_authenticated_user)):
    """Get user's cart"""
    try:
        db = get_db()
        
        if not db:
            # Return empty cart in development mode
            return create_success_response(
                data={
                    'cart': {
                        'items': [],
                        'total': 0,
                        'item_count': 0,
                        'subtotal': 0,
                        'tax': 0,
                        'shipping': 0
                    }
                }
            )
        
        cart_doc = db.collection('carts').document(current_user['id']).get()
        
        if not cart_doc.exists:
            # Return empty cart if not exists
            return create_success_response(
                data={
                    'cart': {
                        'items': [],
                        'total': 0,
                        'item_count': 0,
                        'subtotal': 0,
                        'tax': 0,
                        'shipping': 0
                    }
                }
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        
        # Calculate totals
        totals = calculate_order_total(items)
        
        return create_success_response(
            data={
                'cart': {
                    'items': items,
                    'item_count': len(items),
                    'subtotal': totals['subtotal'],
                    'tax': totals['tax'],
                    'shipping': totals['shipping'],
                    'total': totals['total']
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cart"
        )

@router.get("/summary")
async def get_cart_summary(current_user: dict = Depends(require_authenticated_user)):
    """Get cart summary"""
    try:
        db = get_db()
        
        if not db:
            return create_success_response(
                data={
                    'items_count': 0,
                    'subtotal': 0,
                    'tax': 0,
                    'shipping': 0,
                    'total': 0
                }
            )
        
        cart_doc = db.collection('carts').document(current_user['id']).get()
        
        if not cart_doc.exists:
            return create_success_response(
                data={
                    'items_count': 0,
                    'subtotal': 0,
                    'tax': 0,
                    'shipping': 0,
                    'total': 0
                }
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        
        # Calculate totals
        totals = calculate_order_total(items)
        
        # Count total items (considering quantity)
        total_items = sum(item.get('quantity', 1) for item in items)
        
        return create_success_response(
            data={
                'items_count': total_items,
                'unique_items': len(items),
                'subtotal': totals['subtotal'],
                'tax': totals['tax'],
                'shipping': totals['shipping'],
                'total': totals['total']
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting cart summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cart summary"
        )

@router.post("/items")
async def add_to_cart(
    item: CartItemAdd,
    current_user: dict = Depends(require_authenticated_user)
):
    """Add item to cart"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Item added to cart (development mode)"
        )
    
    try:
        # Get product details
        product_doc = db.collection('products').document(item.product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product = product_doc.to_dict()
        
        # Check inventory
        if product.get('inventory_quantity', 0) < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient inventory. Only {product.get('inventory_quantity', 0)} items available."
            )
        
        # Get or create cart
        cart_ref = db.collection('carts').document(current_user['id'])
        cart_doc = cart_ref.get()
        
        if cart_doc.exists:
            cart = cart_doc.to_dict()
            items = cart.get('items', [])
            
            # Check if item already in cart
            existing_item = next(
                (i for i in items if 
                 i['product_id'] == item.product_id and 
                 i.get('variant_id') == item.variant_id),
                None
            )
            
            if existing_item:
                # Update quantity
                existing_item['quantity'] += item.quantity
                existing_item['updated_at'] = datetime.utcnow()
            else:
                # Add new item
                new_item = {
                    'product_id': item.product_id,
                    'title': product.get('title'),
                    'price': product.get('price'),
                    'image': product.get('images', [''])[0] if product.get('images') else '',
                    'quantity': item.quantity,
                    'variant_id': item.variant_id,
                    'customization': item.customization,
                    'added_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                items.append(new_item)
            
            cart_ref.update({
                'items': items,
                'updated_at': datetime.utcnow()
            })
        else:
            # Create new cart
            cart_ref.set({
                'user_id': current_user['id'],
                'items': [{
                    'product_id': item.product_id,
                    'title': product.get('title'),
                    'price': product.get('price'),
                    'image': product.get('images', [''])[0] if product.get('images') else '',
                    'quantity': item.quantity,
                    'variant_id': item.variant_id,
                    'customization': item.customization,
                    'added_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }],
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        logger.info(f"Item added to cart: {item.product_id} for user: {current_user['id']}")
        
        return create_success_response(
            message="Item added to cart successfully",
            data={'product_id': item.product_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.patch("/items/{product_id}")
async def update_cart_item(
    product_id: str,
    update: CartItemUpdate,
    current_user: dict = Depends(require_authenticated_user)
):
    """Update cart item quantity"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Cart item updated (development mode)"
        )
    
    try:
        cart_ref = db.collection('carts').document(current_user['id'])
        cart_doc = cart_ref.get()
        
        if not cart_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        
        # Find and update item
        item_found = False
        updated_items = []
        
        for item in items:
            if item['product_id'] == product_id:
                if update.quantity > 0:
                    # Update quantity
                    item['quantity'] = update.quantity
                    item['updated_at'] = datetime.utcnow()
                    updated_items.append(item)
                # If quantity is 0, don't add to updated_items (effectively removing it)
                item_found = True
            else:
                updated_items.append(item)
        
        if not item_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )
        
        cart_ref.update({
            'items': updated_items,
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Cart item updated: {product_id} for user: {current_user['id']}")
        
        return create_success_response(
            message="Cart item updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cart item: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/items/{product_id}")
async def remove_from_cart(
    product_id: str,
    variant_id: Optional[str] = Query(None),
    current_user: dict = Depends(require_authenticated_user)
):
    """Remove item from cart"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Item removed from cart (development mode)"
        )
    
    try:
        cart_ref = db.collection('carts').document(current_user['id'])
        cart_doc = cart_ref.get()
        
        if not cart_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found"
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        original_count = len(items)
        
        # Remove item
        items = [
            item for item in items 
            if not (item['product_id'] == product_id and 
                   item.get('variant_id') == variant_id)
        ]
        
        if len(items) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Item not found in cart"
            )
        
        cart_ref.update({
            'items': items,
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Item removed from cart: {product_id} for user: {current_user['id']}")
        
        return create_success_response(
            message="Item removed from cart successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/clear")
async def clear_cart(current_user: dict = Depends(require_authenticated_user)):
    """Clear all items from cart"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Cart cleared (development mode)"
        )
    
    try:
        cart_ref = db.collection('carts').document(current_user['id'])
        
        # Check if cart exists
        if not cart_ref.get().exists:
            return create_success_response(
                message="Cart is already empty"
            )
        
        cart_ref.update({
            'items': [],
            'updated_at': datetime.utcnow()
        })
        
        logger.info(f"Cart cleared for user: {current_user['id']}")
        
        return create_success_response(
            message="Cart cleared successfully"
        )
        
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/sync")
async def sync_cart(
    cart_data: CartSync,
    current_user: dict = Depends(require_authenticated_user)
):
    """Sync cart across devices (merge guest cart with user cart)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Cart synced (development mode)",
            data={'merged_items': len(cart_data.guest_cart_items)}
        )
    
    try:
        cart_ref = db.collection('carts').document(current_user['id'])
        cart_doc = cart_ref.get()
        
        if cart_doc.exists:
            cart = cart_doc.to_dict()
            existing_items = cart.get('items', [])
        else:
            existing_items = []
        
        # Create a map of existing items
        existing_map = {}
        for item in existing_items:
            key = f"{item['product_id']}_{item.get('variant_id', '')}"
            existing_map[key] = item
        
        # Merge guest items
        merged_count = 0
        for guest_item in cart_data.guest_cart_items:
            key = f"{guest_item['product_id']}_{guest_item.get('variant_id', '')}"
            
            if key in existing_map:
                # Update quantity
                existing_map[key]['quantity'] += guest_item.get('quantity', 1)
                existing_map[key]['updated_at'] = datetime.utcnow()
            else:
                # Add new item
                guest_item['added_at'] = datetime.utcnow()
                guest_item['updated_at'] = datetime.utcnow()
                existing_map[key] = guest_item
                merged_count += 1
        
        # Convert back to list
        merged_items = list(existing_map.values())
        
        # Update cart
        if cart_doc.exists:
            cart_ref.update({
                'items': merged_items,
                'updated_at': datetime.utcnow()
            })
        else:
            cart_ref.set({
                'user_id': current_user['id'],
                'items': merged_items,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        logger.info(f"Cart synced for user: {current_user['id']}, merged {merged_count} items")
        
        return create_success_response(
            message="Cart synced successfully",
            data={
                'merged_items': merged_count,
                'total_items': len(merged_items)
            }
        )
        
    except Exception as e:
        logger.error(f"Error syncing cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/validate")
async def validate_cart(current_user: dict = Depends(require_authenticated_user)):
    """Validate cart items (check availability, prices, etc.)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={'valid': True, 'issues': []},
            message="Cart validation skipped (development mode)"
        )
    
    try:
        cart_doc = db.collection('carts').document(current_user['id']).get()
        
        if not cart_doc.exists:
            return create_success_response(
                data={'valid': True, 'issues': []},
                message="Cart is empty"
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        
        issues = []
        updated_items = []
        
        for item in items:
            # Get current product details
            product_doc = db.collection('products').document(item['product_id']).get()
            
            if not product_doc.exists:
                issues.append({
                    'product_id': item['product_id'],
                    'issue': 'Product no longer available',
                    'action': 'remove'
                })
                continue
            
            product = product_doc.to_dict()
            
            # Check if product is active
            if product.get('status') != 'active':
                issues.append({
                    'product_id': item['product_id'],
                    'issue': 'Product is not available',
                    'action': 'remove'
                })
                continue
            
            # Check inventory
            if product.get('inventory_quantity', 0) < item['quantity']:
                issues.append({
                    'product_id': item['product_id'],
                    'issue': f'Only {product.get("inventory_quantity", 0)} items available',
                    'action': 'update_quantity',
                    'new_quantity': product.get('inventory_quantity', 0)
                })
                item['quantity'] = min(item['quantity'], product.get('inventory_quantity', 0))
            
            # Check price changes
            if product.get('price') != item.get('price'):
                issues.append({
                    'product_id': item['product_id'],
                    'issue': f'Price changed from ${item.get("price", 0):.2f} to ${product.get("price", 0):.2f}',
                    'action': 'update_price',
                    'old_price': item.get('price'),
                    'new_price': product.get('price')
                })
                item['price'] = product.get('price')
            
            # Update item with current product details
            item['title'] = product.get('title')
            item['image'] = product.get('images', [''])[0] if product.get('images') else item.get('image', '')
            
            updated_items.append(item)
        
        # Update cart if there were changes
        if issues:
            cart_ref = db.collection('carts').document(current_user['id'])
            cart_ref.update({
                'items': updated_items,
                'validated_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        return create_success_response(
            data={
                'valid': len(issues) == 0,
                'issues': issues,
                'updated_items': len(issues) > 0
            },
            message="Cart validated" if not issues else "Cart has issues that need attention"
        )
        
    except Exception as e:
        logger.error(f"Error validating cart: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate cart"
        )

@router.post("/preview-discounts")
async def preview_cart_discounts(
    coupon_code: Optional[str] = Body(None),
    current_user: dict = Depends(require_authenticated_user)
):
    """Preview discounts that would apply to cart"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={
                'discounts': [],
                'total_discount': 0
            }
        )
    
    try:
        # Get cart
        cart_doc = db.collection('carts').document(current_user['id']).get()
        
        if not cart_doc.exists:
            return create_success_response(
                data={'discounts': [], 'total_discount': 0},
                message="Cart is empty"
            )
        
        cart = cart_doc.to_dict()
        items = cart.get('items', [])
        
        # Calculate subtotal
        subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
        
        discounts = []
        total_discount = 0
        
        # Check for automatic discounts
        # Example: 10% off orders over $100
        if subtotal >= 100:
            discount_amount = subtotal * 0.1
            discounts.append({
                'type': 'automatic',
                'description': '10% off orders over $100',
                'amount': round(discount_amount, 2)
            })
            total_discount += discount_amount
        
        # Check coupon code if provided
        if coupon_code:
            # Query coupons collection
            coupon_query = db.collection('coupons').where('code', '==', coupon_code.upper()).limit(1)
            coupon_docs = list(coupon_query.stream())
            
            if coupon_docs:
                coupon_doc = coupon_docs[0]
                coupon = coupon_doc.to_dict()
                
                # Validate coupon
                now = datetime.utcnow()
                valid_from = coupon.get('valid_from')
                valid_to = coupon.get('valid_to')
                
                if valid_from and valid_from > now:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Coupon is not yet valid"
                    )
                
                if valid_to and valid_to < now:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Coupon has expired"
                    )
                
                if coupon.get('min_purchase', 0) > subtotal:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Minimum purchase of ${coupon.get('min_purchase', 0):.2f} required"
                    )
                
                # Calculate discount
                if coupon.get('discount_type') == 'percentage':
                    discount_amount = subtotal * (coupon.get('discount_value', 0) / 100)
                    if coupon.get('max_discount'):
                        discount_amount = min(discount_amount, coupon.get('max_discount'))
                else:
                    discount_amount = min(coupon.get('discount_value', 0), subtotal)
                
                discounts.append({
                    'type': 'coupon',
                    'code': coupon_code.upper(),
                    'description': coupon.get('description', 'Coupon discount'),
                    'amount': round(discount_amount, 2)
                })
                total_discount += discount_amount
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid coupon code"
                )
        
        return create_success_response(
            data={
                'discounts': discounts,
                'subtotal': round(subtotal, 2),
                'total_discount': round(total_discount, 2),
                'final_total': round(subtotal - total_discount, 2)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing discounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preview discounts"
        )
