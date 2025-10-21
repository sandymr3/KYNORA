"""Order Service - Business logic for order management"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from config.firebase import db
from models.order import (
    Order, OrderItem, OrderStatus, PaymentStatus, 
    FulfillmentStatus, OrderCreate, OrderPricing,
    OrderPayment, OrderShipping, ProductSnapshot
)
from models.cart import Cart
from services.cart_service import CartService
from utils.helpers import Helpers

logger = logging.getLogger(__name__)


class OrderService:
    """Service for order operations"""
    
    def __init__(self):
        self.db = db
        self.orders_collection = 'orders'
        self.products_collection = 'products'
        self.cart_service = CartService()
    
    async def create_order(self, user_id: str, order_data: OrderCreate) -> Dict[str, Any]:
        """
        Create order from cart with inventory reservation
        
        Args:
            user_id: User ID
            order_data: Order creation data
            
        Returns:
            Response with order details
        """
        try:
            # Get and validate cart
            cart = await self.cart_service.get_cart(user_id)
            if not cart or cart.is_empty():
                return {"success": False, "message": "Cart is empty"}
            
            # Validate cart items
            validation = await self.cart_service.validate_cart(user_id)
            if not validation["valid"]:
                return {
                    "success": False,
                    "message": "Cart validation failed",
                    "issues": validation["issues"]
                }
            
            # Generate order ID and number
            order_id = Helpers.generate_id("ORD")
            order_number = Helpers.generate_order_number()
            
            # Create order items from cart
            order_items = []
            seller_ids = set()
            
            for cart_item in cart.items:
                # Get product snapshot
                product_doc = self.db.collection(self.products_collection).document(
                    cart_item.product_id
                ).get()
                product_data = product_doc.to_dict()
                
                # Add seller ID
                seller_ids.add(product_data.get('seller_id'))
                
                # Create product snapshot
                snapshot = ProductSnapshot(
                    title=product_data.get('title'),
                    image=product_data.get('thumbnail'),
                    price=product_data.get('price'),
                    sku=product_data.get('sku')
                )
                
                # Create order item
                order_item = OrderItem(
                    order_item_id=Helpers.generate_id("OI"),
                    product_id=cart_item.product_id,
                    product_snapshot=snapshot,
                    quantity=cart_item.quantity,
                    price=cart_item.price_at_addition,
                    subtotal=cart_item.calculate_subtotal(),
                    selected_variants=cart_item.selected_variants.to_dict() if cart_item.selected_variants else None
                )
                order_items.append(order_item)
                
                # Reserve inventory
                await self._reserve_inventory(cart_item.product_id, cart_item.quantity)
            
            # Calculate pricing
            pricing = OrderPricing(
                subtotal=cart.subtotal,
                discount=cart.applied_coupon.calculate_discount(cart.subtotal) if cart.applied_coupon else 0,
                tax=cart.estimated_tax,
                shipping_cost=cart.estimated_shipping,
                total=cart.total
            )
            
            # Create payment info
            payment = OrderPayment(
                payment_method=order_data.payment_method,
                amount_paid=0  # Will be updated after payment
            )
            
            # Create shipping info
            shipping = OrderShipping(
                shipping_method=order_data.shipping_method
            )
            
            # Create order
            order = Order(
                order_id=order_id,
                order_number=order_number,
                user_id=user_id,
                seller_ids=list(seller_ids),
                items=order_items,
                status=OrderStatus.PENDING,
                payment_status=PaymentStatus.PENDING,
                fulfillment_status=FulfillmentStatus.PENDING,
                shipping_address=order_data.shipping_address,
                billing_address=order_data.billing_address,
                pricing=pricing,
                payment=payment,
                shipping=shipping,
                customer_notes=order_data.customer_notes,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add initial timeline event
            order.add_timeline_event(
                event="created",
                description="Order created",
                user_id=user_id
            )
            
            # Save to Firestore
            self.db.collection(self.orders_collection).document(order_id).set(
                order.to_firestore()
            )
            
            # Clear cart after successful order
            await self.cart_service.clear_cart(user_id)
            
            return {
                "success": True,
                "message": "Order created successfully",
                "order": order,
                "order_id": order_id,
                "order_number": order_number
            }
            
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _reserve_inventory(self, product_id: str, quantity: int) -> bool:
        """
        Reserve inventory for order item
        
        Args:
            product_id: Product ID
            quantity: Quantity to reserve
            
        Returns:
            Success status
        """
        try:
            product_ref = self.db.collection(self.products_collection).document(product_id)
            product_doc = product_ref.get()
            
            if product_doc.exists:
                current_inventory = product_doc.to_dict().get('inventory_quantity', 0)
                new_inventory = max(0, current_inventory - quantity)
                
                product_ref.update({
                    'inventory_quantity': new_inventory,
                    'updated_at': datetime.utcnow()
                })
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error reserving inventory: {str(e)}")
            return False
    
    async def get_order(self, order_id: str, user_id: Optional[str] = None) -> Optional[Order]:
        """
        Get order by ID
        
        Args:
            order_id: Order ID
            user_id: Optional user ID for validation
            
        Returns:
            Order object or None
        """
        try:
            order_doc = self.db.collection(self.orders_collection).document(order_id).get()
            
            if not order_doc.exists:
                return None
            
            order_data = order_doc.to_dict()
            
            # Validate user access
            if user_id and order_data.get('user_id') != user_id:
                return None
            
            return Order(**order_data)
            
        except Exception as e:
            logger.error(f"Error getting order: {str(e)}")
            return None
    
    async def get_user_orders(
        self, 
        user_id: str, 
        page: int = 1, 
        limit: int = 20,
        status: Optional[OrderStatus] = None
    ) -> Dict[str, Any]:
        """
        Get paginated user orders
        
        Args:
            user_id: User ID
            page: Page number
            limit: Items per page
            status: Optional status filter
            
        Returns:
            Paginated orders response
        """
        try:
            # Build query
            query = self.db.collection(self.orders_collection).where('user_id', '==', user_id)
            
            if status:
                query = query.where('status', '==', status.value)
            
            # Get total count
            total_docs = query.stream()
            total = len(list(total_docs))
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.order_by('created_at', direction='DESCENDING').offset(offset).limit(limit)
            
            # Get orders
            orders = []
            for doc in query.stream():
                order_data = doc.to_dict()
                order_data['order_id'] = doc.id
                orders.append(Order(**order_data))
            
            # Calculate pagination
            pagination = Helpers.calculate_pagination(total, page, limit)
            
            return {
                "success": True,
                "orders": orders,
                **pagination
            }
            
        except Exception as e:
            logger.error(f"Error getting user orders: {str(e)}")
            return {
                "success": False,
                "message": str(e),
                "orders": [],
                "total": 0
            }
    
    async def update_status(
        self, 
        order_id: str, 
        status: OrderStatus, 
        notes: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update order status with timeline event
        
        Args:
            order_id: Order ID
            status: New status
            notes: Optional notes
            user_id: User making the update
            
        Returns:
            Response with success status
        """
        try:
            # Get order
            order = await self.get_order(order_id)
            if not order:
                return {"success": False, "message": "Order not found"}
            
            # Update status
            order.status = status
            order.updated_at = datetime.utcnow()
            
            # Add timeline event
            order.add_timeline_event(
                event=f"status_changed",
                description=f"Order status changed to {status.value}. {notes or ''}",
                user_id=user_id
            )
            
            # Update payment status if needed
            if status == OrderStatus.CONFIRMED:
                order.payment_status = PaymentStatus.PAID
                order.payment.paid_at = datetime.utcnow()
            elif status == OrderStatus.CANCELLED:
                order.cancelled_at = datetime.utcnow()
                order.cancelled_reason = notes
                # Release inventory
                for item in order.items:
                    await self._release_inventory(item.product_id, item.quantity)
            elif status == OrderStatus.DELIVERED:
                order.fulfillment_status = FulfillmentStatus.DELIVERED
                order.shipping.actual_delivery = datetime.utcnow()
            
            # Save to Firestore
            self.db.collection(self.orders_collection).document(order_id).set(
                order.to_firestore()
            )
            
            return {
                "success": True,
                "message": f"Order status updated to {status.value}",
                "order": order
            }
            
        except Exception as e:
            logger.error(f"Error updating order status: {str(e)}")
            return {"success": False, "message": str(e)}
    
    async def _release_inventory(self, product_id: str, quantity: int) -> bool:
        """
        Release inventory when order is cancelled
        
        Args:
            product_id: Product ID
            quantity: Quantity to release
            
        Returns:
            Success status
        """
        try:
            product_ref = self.db.collection(self.products_collection).document(product_id)
            product_doc = product_ref.get()
            
            if product_doc.exists:
                current_inventory = product_doc.to_dict().get('inventory_quantity', 0)
                new_inventory = current_inventory + quantity
                
                product_ref.update({
                    'inventory_quantity': new_inventory,
                    'updated_at': datetime.utcnow()
                })
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error releasing inventory: {str(e)}")
            return False
    
    async def cancel_order(self, order_id: str, reason: str, user_id: str) -> Dict[str, Any]:
        """
        Cancel order and release inventory
        
        Args:
            order_id: Order ID
            reason: Cancellation reason
            user_id: User cancelling the order
            
        Returns:
            Response with success status
        """
        try:
            # Get order
            order = await self.get_order(order_id)
            if not order:
                return {"success": False, "message": "Order not found"}
            
            # Check if order can be cancelled
            if not order.can_cancel():
                return {
                    "success": False,
                    "message": f"Order cannot be cancelled in {order.status.value} status"
                }
            
            # Update status
            return await self.update_status(
                order_id=order_id,
                status=OrderStatus.CANCELLED,
                notes=reason,
                user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"Error cancelling order: {str(e)}")
            return {"success": False, "message": str(e)}
