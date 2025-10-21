"""Cart Service - Business logic for shopping cart operations"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from config.firebase import db
from models.cart import Cart, CartItem, CartItemVariant, AppliedCoupon
from models.product import Product
from utils.helpers import Helpers

logger = logging.getLogger(__name__)


class CartService:
    """Service for cart operations"""
    
    def __init__(self):
        self.db = db
        self.carts_collection = 'carts'
        self.products_collection = 'products'
    
    async def get_cart(self, user_id: str) -> Optional[Cart]:
        """
        Get user's cart with product details
        
        Args:
            user_id: User ID
            
        Returns:
            Cart object or None
        """
        try:
            # Get cart document
            cart_doc = self.db.collection(self.carts_collection).document(user_id).get()
            
            if not cart_doc.exists:
                # Create new cart if doesn't exist
                return await self.create_cart(user_id)
            
            cart_data = cart_doc.to_dict()
            cart = Cart(**cart_data)
            
            # Populate product info for each item
            for item in cart.items:
                product_doc = self.db.collection(self.products_collection).document(item.product_id).get()
                if product_doc.exists:
                    product_data = product_doc.to_dict()
                    from models.product import ProductQuickView
                    item.product_info = ProductQuickView(
                        product_id=item.product_id,
                        title=product_data.get('title'),
                        slug=product_data.get('slug'),
                        price=product_data.get('price'),
                        compare_at_price=product_data.get('compare_at_price'),
                        thumbnail=product_data.get('thumbnail'),
                        rating_average=product_data.get('rating_average', 0),
                        is_on_sale=product_data.get('is_on_sale', False),
                        in_stock=product_data.get('inventory_quantity', 0) > 0
                    )
            
            # Recalculate totals
            cart.calculate_totals()
            
            return cart
            
        except Exception as e:
            logger.error(f"Error getting cart: {str(e)}")
            return None
    
    async def create_cart(self, user_id: str) -> Cart:
        """
        Create a new cart for user
        
        Args:
            user_id: User ID
            
        Returns:
            New Cart object
        """
        try:
            cart = Cart(
                cart_id=user_id,
                user_id=user_id,
                items=[],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return cart
            
        except Exception as e:
            logger.error(f"Error creating cart: {str(e)}")
            raise
    
    async def add_item(
        self, 
        user_id: str, 
        product_id: str, 
        quantity: int, 
        variants: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Add item to cart with inventory validation
        
        Args:
            user_id: User ID
            product_id: Product ID
            quantity: Quantity to add
            variants: Selected variants
            
        Returns:
            Response with success status
        """
        try:
            # Get product
            product_doc = self.db.collection(self.products_collection).document(product_id).get()
            if not product_doc.exists:
                return {"success": False, "message": "Product not found"}
            
            product_data = product_doc.to_dict()
            
            # Check inventory
            available_quantity = product_data.get('inventory_quantity', 0)
            if available_quantity < quantity:
                return {
                    "success": False, 
                    "message": f"Only {available_quantity} items available"
                }
            
            # Get or create cart
            cart = await self.get_cart(user_id)
            if not cart:
                cart = await self.create_cart(user_id)
            
            # Create variant object
            variant_obj = CartItemVariant(**variants) if variants else None
            
            # Add item to cart
            cart_item = cart.add_item(
                product_id=product_id,
                quantity=quantity,
                price=product_data.get('price'),
                variants=variant_obj
            )
            
            # Update cart totals
            cart.calculate_totals()
            cart.updated_at = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return {
                "success": True,
                "message": "Item added to cart",
                "cart_item_id": cart_item.cart_item_id,
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error adding item to cart: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def update_quantity(
        self, 
        user_id: str, 
        cart_item_id: str, 
        quantity: int
    ) -> Dict[str, Any]:
        """
        Update cart item quantity
        
        Args:
            user_id: User ID
            cart_item_id: Cart item ID
            quantity: New quantity
            
        Returns:
            Response with success status
        """
        try:
            # Get cart
            cart = await self.get_cart(user_id)
            if not cart:
                return {"success": False, "message": "Cart not found"}
            
            # Find item
            item = next((i for i in cart.items if i.cart_item_id == cart_item_id), None)
            if not item:
                return {"success": False, "message": "Item not found in cart"}
            
            # Check inventory
            product_doc = self.db.collection(self.products_collection).document(item.product_id).get()
            if product_doc.exists:
                available = product_doc.to_dict().get('inventory_quantity', 0)
                if available < quantity:
                    return {
                        "success": False,
                        "message": f"Only {available} items available"
                    }
            
            # Update quantity
            updated_item = cart.update_item_quantity(cart_item_id, quantity)
            if not updated_item:
                return {"success": False, "message": "Failed to update quantity"}
            
            # Update totals
            cart.calculate_totals()
            cart.updated_at = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return {
                "success": True,
                "message": "Quantity updated",
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error updating quantity: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def remove_item(self, user_id: str, cart_item_id: str) -> Dict[str, Any]:
        """
        Remove item from cart
        
        Args:
            user_id: User ID
            cart_item_id: Cart item ID
            
        Returns:
            Response with success status
        """
        try:
            # Get cart
            cart = await self.get_cart(user_id)
            if not cart:
                return {"success": False, "message": "Cart not found"}
            
            # Remove item
            removed = cart.remove_item(cart_item_id)
            if not removed:
                return {"success": False, "message": "Item not found in cart"}
            
            # Update totals
            cart.calculate_totals()
            cart.updated_at = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return {
                "success": True,
                "message": "Item removed from cart",
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error removing item: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def clear_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Clear entire cart
        
        Args:
            user_id: User ID
            
        Returns:
            Response with success status
        """
        try:
            # Get cart
            cart = await self.get_cart(user_id)
            if not cart:
                return {"success": False, "message": "Cart not found"}
            
            # Clear items
            cart.clear()
            cart.updated_at = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return {
                "success": True,
                "message": "Cart cleared",
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error clearing cart: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def apply_coupon(self, user_id: str, coupon_code: str) -> Dict[str, Any]:
        """
        Apply coupon to cart
        
        Args:
            user_id: User ID
            coupon_code: Coupon code
            
        Returns:
            Response with success status
        """
        try:
            # Get cart
            cart = await self.get_cart(user_id)
            if not cart:
                return {"success": False, "message": "Cart not found"}
            
            if cart.is_empty():
                return {"success": False, "message": "Cart is empty"}
            
            # TODO: Validate coupon code from coupons collection
            # For demo, create a sample coupon
            coupon = AppliedCoupon(
                coupon_code=coupon_code.upper(),
                discount_amount=10.0,
                discount_type="percentage",
                description="10% off your order"
            )
            
            cart.applied_coupon = coupon
            cart.calculate_totals()
            cart.updated_at = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.carts_collection).document(user_id).set(
                cart.to_firestore()
            )
            
            return {
                "success": True,
                "message": "Coupon applied successfully",
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error applying coupon: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def validate_cart(self, user_id: str) -> Dict[str, Any]:
        """
        Validate cart items (check inventory, prices)
        
        Args:
            user_id: User ID
            
        Returns:
            Validation result with any issues found
        """
        try:
            cart = await self.get_cart(user_id)
            if not cart:
                return {"valid": False, "message": "Cart not found"}
            
            if cart.is_empty():
                return {"valid": False, "message": "Cart is empty"}
            
            issues = []
            
            for item in cart.items:
                # Check product exists and is active
                product_doc = self.db.collection(self.products_collection).document(item.product_id).get()
                
                if not product_doc.exists:
                    issues.append(f"Product {item.product_id} no longer exists")
                    continue
                
                product_data = product_doc.to_dict()
                
                # Check if product is active
                if product_data.get('status') != 'active':
                    issues.append(f"{product_data.get('title')} is no longer available")
                
                # Check inventory
                available = product_data.get('inventory_quantity', 0)
                if available < item.quantity:
                    issues.append(f"Only {available} units of {product_data.get('title')} available")
                
                # Check price changes
                current_price = product_data.get('price')
                if current_price != item.price_at_addition:
                    issues.append(f"Price of {product_data.get('title')} has changed")
            
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "cart": cart
            }
            
        except Exception as e:
            logger.error(f"Error validating cart: {str(e)}")
            return {"valid": False, "message": str(e)}
