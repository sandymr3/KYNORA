"""
Initialize cart collection and test cart operations
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import initialize_firebase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_cart_system():
    """Initialize cart collection and create test cart"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("Failed to initialize Firebase")
            return False
        
        logger.info("Setting up cart system...")
        
        # Create a test user cart
        test_user_id = "test_user_001"
        
        # Check if cart already exists
        cart_ref = db.collection('carts').document(test_user_id)
        cart_doc = cart_ref.get()
        
        if cart_doc.exists:
            logger.info(f"Cart already exists for user {test_user_id}")
            cart_data = cart_doc.to_dict()
            logger.info(f"Current cart: {cart_data}")
        else:
            # Create new cart
            cart_data = {
                'cart_id': test_user_id,
                'user_id': test_user_id,
                'items': [],
                'subtotal': 0.0,
                'tax': 0.0,
                'discount': 0.0,
                'total': 0.0,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            cart_ref.set(cart_data)
            logger.info(f"✅ Created cart for user {test_user_id}")
        
        # Add sample item to cart
        product_id = "prod_001"
        
        # Get product details
        product_doc = db.collection('products').document(product_id).get()
        if product_doc.exists:
            product_data = product_doc.to_dict()
            
            # Create cart item
            cart_item = {
                'cart_item_id': f"item_{datetime.utcnow().timestamp()}",
                'product_id': product_id,
                'quantity': 1,
                'price': product_data.get('price', 0),
                'subtotal': product_data.get('price', 0),
                'product_info': {
                    'title': product_data.get('title'),
                    'price': product_data.get('price'),
                    'thumbnail': product_data.get('thumbnail', ''),
                    'in_stock': True
                }
            }
            
            # Update cart
            cart_data['items'] = [cart_item]
            cart_data['subtotal'] = cart_item['subtotal']
            cart_data['total'] = cart_item['subtotal']
            cart_data['updated_at'] = datetime.utcnow()
            
            cart_ref.set(cart_data)
            logger.info(f"✅ Added product {product_id} to cart")
        
        # List all carts in the system
        logger.info("\n📦 ALL CARTS IN DATABASE:")
        logger.info("=" * 60)
        
        all_carts = db.collection('carts').stream()
        cart_count = 0
        
        for cart_doc in all_carts:
            cart_count += 1
            cart_data = cart_doc.to_dict()
            user_id = cart_doc.id
            items_count = len(cart_data.get('items', []))
            total = cart_data.get('total', 0)
            
            logger.info(f"\nCart {cart_count}:")
            logger.info(f"  User ID: {user_id}")
            logger.info(f"  Items: {items_count}")
            logger.info(f"  Total: ${total}")
            
            for item in cart_data.get('items', [])[:3]:  # Show first 3 items
                logger.info(f"    - {item.get('product_info', {}).get('title', 'Unknown')} x{item.get('quantity', 0)} = ${item.get('subtotal', 0)}")
        
        if cart_count == 0:
            logger.warning("No carts found in database!")
        else:
            logger.info(f"\n✅ Found {cart_count} cart(s) in database")
        
        # Test cart operations
        logger.info("\n🧪 TESTING CART OPERATIONS:")
        logger.info("=" * 60)
        
        # Get a cart
        test_cart = db.collection('carts').document(test_user_id).get()
        if test_cart.exists:
            logger.info("✅ Cart retrieval works")
        else:
            logger.error("❌ Cart retrieval failed")
        
        # Update cart
        db.collection('carts').document(test_user_id).update({
            'updated_at': datetime.utcnow()
        })
        logger.info("✅ Cart update works")
        
        logger.info("\n✅ Cart system setup complete!")
        logger.info("\n📋 Test with these commands:")
        logger.info("1. Get cart: GET http://localhost:8000/cart")
        logger.info("2. Add item: POST http://localhost:8000/cart/items")
        logger.info("3. Update item: PUT http://localhost:8000/cart/items/{cart_item_id}")
        logger.info("4. Remove item: DELETE http://localhost:8000/cart/items/{cart_item_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up cart system: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    setup_cart_system()
