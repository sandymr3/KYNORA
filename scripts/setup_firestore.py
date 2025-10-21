#!/usr/bin/env python3
"""
KYNORA Firebase Firestore Setup Script
Initializes database with collections and sample data
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
import logging
import uuid

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.firebase import db
from config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FirestoreSetup:
    """Firestore database initialization"""
    
    def __init__(self):
        self.db = db
        
    def create_users_collection(self, seed_data=True):
        """Create users collection"""
        try:
            logger.info("📝 Creating users collection...")
            
            # Admin user
            admin = {
                'user_id': 'admin_001',
                'email': settings.admin_email,
                'name': 'Admin User',
                'display_name': 'Admin',
                'role': 'admin',
                'avatar': 'https://i.pravatar.cc/300',
                'phone': '+1-555-0100',
                'status': 'active',
                'email_verified': True,
                'address': {
                    'street': '123 Admin St',
                    'city': 'New York',
                    'state': 'NY',
                    'zip_code': '10001',
                    'country': 'USA'
                },
                'preferences': {
                    'notifications': True,
                    'newsletter': True,
                    'language': 'en',
                    'currency': 'USD'
                },
                'metadata': {
                    'last_login': datetime.utcnow(),
                    'login_count': 1,
                    'ip_address': '127.0.0.1'
                },
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            self.db.collection('users').document('admin_001').set(admin)
            
            if seed_data:
                # Sample customer
                customer = admin.copy()
                customer.update({
                    'user_id': 'customer_001',
                    'email': 'customer@example.com',
                    'name': 'John Doe',
                    'display_name': 'John',
                    'role': 'customer'
                })
                self.db.collection('users').document('customer_001').set(customer)
                
                # Sample seller
                seller = admin.copy()
                seller.update({
                    'user_id': 'seller_001',
                    'email': 'seller@example.com',
                    'name': 'Jane Smith',
                    'display_name': 'Jane',
                    'role': 'seller'
                })
                self.db.collection('users').document('seller_001').set(seller)
                
            logger.info("✅ Users collection created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_categories_collection(self):
        """Create categories collection"""
        try:
            logger.info("📝 Creating categories...")
            
            categories = [
                ('electronics', 'Electronics', None, 0),
                ('fashion', 'Fashion', None, 0),
                ('home-garden', 'Home & Garden', None, 0),
                ('sports', 'Sports & Outdoors', None, 0),
                ('smartphones', 'Smartphones', 'electronics', 1),
                ('laptops', 'Laptops', 'electronics', 1),
                ('audio', 'Audio', 'electronics', 1),
                ('mens-fashion', "Men's Fashion", 'fashion', 1),
                ('womens-fashion', "Women's Fashion", 'fashion', 1),
            ]
            
            for cat_id, name, parent, level in categories:
                doc = {
                    'category_id': cat_id,
                    'name': name,
                    'slug': cat_id,
                    'description': f'{name} category',
                    'parent_id': parent,
                    'level': level,
                    'path': f'{parent}/{cat_id}' if parent else cat_id,
                    'product_count': 0,
                    'display_order': 0,
                    'status': 'active',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
                self.db.collection('categories').document(cat_id).set(doc)
            
            logger.info("✅ Categories created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_products_collection(self):
        """Create sample products"""
        try:
            logger.info("📝 Creating products...")
            
            products = [
                {
                    'product_id': 'prod_001',
                    'title': 'Premium Wireless Headphones',
                    'slug': 'premium-wireless-headphones',
                    'description': 'High-quality wireless headphones with ANC',
                    'short_description': 'Wireless headphones with ANC',
                    'price': 299.99,
                    'compare_at_price': 399.99,
                    'category_id': 'electronics',
                    'subcategory_id': 'audio',
                    'seller_id': 'seller_001',
                    'images': ['https://via.placeholder.com/800'],
                    'thumbnail': 'https://via.placeholder.com/300',
                    'specifications': {
                        'brand': 'AudioTech',
                        'battery': '30 hours',
                        'bluetooth': '5.2'
                    },
                    'tags': ['wireless', 'headphones', 'audio'],
                    'inventory_quantity': 50,
                    'low_stock_threshold': 10,
                    'sku': 'WH-001',
                    'status': 'active',
                    'is_featured': True,
                    'is_on_sale': True,
                    'view_count': 150,
                    'sales_count': 42,
                    'rating_average': 4.5,
                    'rating_count': 28,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                },
                {
                    'product_id': 'prod_002',
                    'title': 'Laptop Stand',
                    'slug': 'laptop-stand',
                    'description': 'Ergonomic aluminum laptop stand',
                    'short_description': 'Aluminum laptop stand',
                    'price': 79.99,
                    'compare_at_price': 99.99,
                    'category_id': 'electronics',
                    'seller_id': 'seller_001',
                    'images': ['https://via.placeholder.com/800'],
                    'thumbnail': 'https://via.placeholder.com/300',
                    'specifications': {'material': 'Aluminum'},
                    'tags': ['laptop', 'stand', 'office'],
                    'inventory_quantity': 120,
                    'sku': 'LS-001',
                    'status': 'active',
                    'is_featured': False,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                },
                {
                    'product_id': 'prod_003',
                    'title': 'Classic T-Shirt',
                    'slug': 'classic-tshirt',
                    'description': '100% cotton t-shirt',
                    'short_description': 'Cotton t-shirt',
                    'price': 29.99,
                    'category_id': 'fashion',
                    'subcategory_id': 'mens-fashion',
                    'seller_id': 'admin_001',
                    'images': ['https://via.placeholder.com/800'],
                    'thumbnail': 'https://via.placeholder.com/300',
                    'specifications': {'material': 'Cotton'},
                    'tags': ['tshirt', 'cotton', 'mens'],
                    'inventory_quantity': 200,
                    'sku': 'TS-001',
                    'status': 'active',
                    'is_featured': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            ]
            
            for product in products:
                # Add default values
                product.setdefault('cost_price', 0)
                product.setdefault('low_stock_threshold', 10)
                product.setdefault('weight', 100)
                product.setdefault('view_count', 0)
                product.setdefault('sales_count', 0)
                product.setdefault('rating_average', 0)
                product.setdefault('rating_count', 0)
                product.setdefault('is_on_sale', False)
                product.setdefault('seo', {})
                
                self.db.collection('products').document(product['product_id']).set(product)
            
            logger.info("✅ Products created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_empty_collections(self):
        """Create empty collections"""
        try:
            logger.info("📝 Creating empty collections...")
            
            collections = ['carts', 'orders', 'reviews', 'wishlists', 'notifications', 
                          'coupons', 'shipping_methods', 'payment_methods', 'settings']
            
            for collection in collections:
                # Create and delete placeholder to ensure collection exists
                doc_ref = self.db.collection(collection).document('_placeholder')
                doc_ref.set({'created': True, 'created_at': datetime.utcnow()})
                doc_ref.delete()
                
            logger.info("✅ Empty collections created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_sample_orders(self):
        """Create sample orders for testing"""
        try:
            logger.info("📝 Creating sample orders...")
            
            # Sample order
            order = {
                'order_id': 'ord_001',
                'order_number': 'ORD-20241020-0001',
                'user_id': 'customer_001',
                'user_email': 'customer@example.com',
                'user_name': 'John Doe',
                
                'items': [
                    {
                        'product_id': 'prod_001',
                        'title': 'Premium Wireless Headphones',
                        'price': 299.99,
                        'quantity': 1,
                        'image': 'https://via.placeholder.com/100'
                    }
                ],
                
                'shipping_address': {
                    'name': 'John Doe',
                    'address_line1': '123 Main St',
                    'city': 'New York',
                    'state': 'NY',
                    'postal_code': '10001',
                    'country': 'USA',
                    'phone': '+1-555-0100'
                },
                
                'billing_address': {
                    'name': 'John Doe',
                    'address_line1': '123 Main St',
                    'city': 'New York',
                    'state': 'NY',
                    'postal_code': '10001',
                    'country': 'USA'
                },
                
                'payment_method': 'credit_card',
                'shipping_method': 'standard',
                
                'subtotal': 299.99,
                'tax': 24.00,
                'shipping': 10.00,
                'total': 333.99,
                
                'status': 'delivered',
                'payment_status': 'paid',
                'fulfillment_status': 'fulfilled',
                
                'timeline': [
                    {
                        'event': 'order_created',
                        'timestamp': datetime.utcnow() - timedelta(days=5),
                        'description': 'Order created'
                    },
                    {
                        'event': 'payment_confirmed',
                        'timestamp': datetime.utcnow() - timedelta(days=5),
                        'description': 'Payment confirmed'
                    },
                    {
                        'event': 'order_shipped',
                        'timestamp': datetime.utcnow() - timedelta(days=3),
                        'description': 'Order shipped'
                    },
                    {
                        'event': 'order_delivered',
                        'timestamp': datetime.utcnow() - timedelta(days=1),
                        'description': 'Order delivered'
                    }
                ],
                
                'tracking_number': 'TRACK123456789',
                'created_at': datetime.utcnow() - timedelta(days=5),
                'updated_at': datetime.utcnow()
            }
            
            self.db.collection('orders').document('ord_001').set(order)
            
            logger.info("✅ Sample orders created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_sample_reviews(self):
        """Create sample reviews"""
        try:
            logger.info("📝 Creating sample reviews...")
            
            reviews = [
                {
                    'review_id': 'rev_001',
                    'product_id': 'prod_001',
                    'user_id': 'customer_001',
                    'user_name': 'John Doe',
                    'rating': 5,
                    'title': 'Excellent headphones!',
                    'comment': 'Amazing sound quality and battery life. Worth every penny!',
                    'verified_purchase': True,
                    'helpful_count': 12,
                    'helpful_users': [],
                    'status': 'approved',
                    'created_at': datetime.utcnow() - timedelta(days=2),
                    'updated_at': datetime.utcnow()
                },
                {
                    'review_id': 'rev_002',
                    'product_id': 'prod_001',
                    'user_id': 'user_002',
                    'user_name': 'Jane Smith',
                    'rating': 4,
                    'title': 'Great but pricey',
                    'comment': 'Good quality but a bit expensive for what you get.',
                    'verified_purchase': True,
                    'helpful_count': 5,
                    'helpful_users': [],
                    'status': 'approved',
                    'created_at': datetime.utcnow() - timedelta(days=7),
                    'updated_at': datetime.utcnow()
                }
            ]
            
            for review in reviews:
                self.db.collection('reviews').document(review['review_id']).set(review)
            
            logger.info("✅ Sample reviews created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_sample_coupons(self):
        """Create sample coupons"""
        try:
            logger.info("📝 Creating sample coupons...")
            
            coupons = [
                {
                    'coupon_id': 'coupon_001',
                    'code': 'WELCOME10',
                    'description': '10% off for new customers',
                    'discount_type': 'percentage',
                    'discount_value': 10,
                    'min_purchase': 50.00,
                    'max_discount': 20.00,
                    'usage_limit': 100,
                    'used_count': 0,
                    'valid_from': datetime.utcnow(),
                    'valid_to': datetime.utcnow() + timedelta(days=30),
                    'applicable_products': [],
                    'applicable_categories': [],
                    'status': 'active',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                },
                {
                    'coupon_id': 'coupon_002',
                    'code': 'SUMMER20',
                    'description': '$20 off on orders over $100',
                    'discount_type': 'fixed',
                    'discount_value': 20,
                    'min_purchase': 100.00,
                    'usage_limit': 50,
                    'used_count': 0,
                    'valid_from': datetime.utcnow(),
                    'valid_to': datetime.utcnow() + timedelta(days=60),
                    'applicable_products': [],
                    'applicable_categories': ['electronics'],
                    'status': 'active',
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            ]
            
            for coupon in coupons:
                self.db.collection('coupons').document(coupon['coupon_id']).set(coupon)
            
            logger.info("✅ Sample coupons created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_analytics_collection(self):
        """Create analytics structure"""
        try:
            logger.info("📝 Creating analytics...")
            
            today = datetime.utcnow().strftime('%Y-%m-%d')
            analytics = {
                'date': today,
                'sales': {
                    'total_revenue': 0,
                    'total_orders': 0,
                    'average_order_value': 0,
                    'new_orders': 0,
                    'cancelled_orders': 0
                },
                'products': {
                    'total_views': 0,
                    'total_sales': 0,
                    'top_products': [],
                    'low_stock_alerts': []
                },
                'users': {
                    'new_signups': 0,
                    'active_users': 0,
                    'returning_users': 0
                },
                'created_at': datetime.utcnow()
            }
            
            self.db.collection('analytics').document(f'daily_{today}').set(analytics)
            logger.info("✅ Analytics created")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def create_firestore_indexes(self):
        """Create Firestore indexes (note: actual indexes need to be created in Firebase Console)"""
        try:
            logger.info("📝 Index recommendations...")
            
            indexes = [
                "Products: (category_id, status, created_at DESC)",
                "Products: (is_featured, status, view_count DESC)",
                "Products: (status, view_count DESC)",
                "Orders: (user_id, created_at DESC)",
                "Orders: (status, created_at DESC)",
                "Reviews: (product_id, created_at DESC)",
                "Reviews: (product_id, rating, created_at DESC)",
                "Categories: (parent_id, status, display_order)",
                "Carts: (user_id, updated_at DESC)",
                "Coupons: (code, status, valid_from, valid_to)"
            ]
            
            logger.info("⚠️ Note: These indexes should be created in Firebase Console:")
            for index in indexes:
                logger.info(f"  - {index}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed: {e}")
            return False
    
    def verify_setup(self):
        """Verify all collections"""
        try:
            logger.info("🔍 Verifying setup...")
            
            collections = [
                'users', 'products', 'categories', 
                'carts', 'orders', 'reviews', 
                'wishlists', 'notifications', 'analytics',
                'coupons', 'shipping_methods', 'payment_methods', 'settings'
            ]
            
            for collection in collections:
                docs = list(self.db.collection(collection).limit(1).stream())
                if docs:
                    logger.info(f"✅ {collection}: OK ({len(docs)} docs found)")
                else:
                    logger.warning(f"⚠️ {collection}: Empty")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
    
    def run_full_setup(self, seed_data=True):
        """Run complete setup"""
        logger.info("="*50)
        logger.info("🚀 KYNORA Firestore Setup Started")
        logger.info("="*50)
        
        steps = [
            ("Users", lambda: self.create_users_collection(seed_data)),
            ("Categories", self.create_categories_collection),
            ("Products", self.create_products_collection),
            ("Empty Collections", self.create_empty_collections),
            ("Sample Orders", self.create_sample_orders) if seed_data else ("Skip Orders", lambda: True),
            ("Sample Reviews", self.create_sample_reviews) if seed_data else ("Skip Reviews", lambda: True),
            ("Sample Coupons", self.create_sample_coupons) if seed_data else ("Skip Coupons", lambda: True),
            ("Analytics", self.create_analytics_collection),
            ("Firestore Indexes", self.create_firestore_indexes),
        ]
        
        for name, func in steps:
            logger.info(f"\n▶️ Creating {name}...")
            if not func():
                logger.error(f"❌ Setup failed at: {name}")
                return False
        
        self.verify_setup()
        
        logger.info("\n" + "="*50)
        logger.info("✅ Setup Complete!")
        logger.info("="*50)
        logger.info("\nNext steps:")
        logger.info("1. Copy .env.example to .env")
        logger.info("2. Add Firebase credentials to .env")
        logger.info("3. Run: python main.py")
        
        return True


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Setup Firestore Database')
    parser.add_argument('--seed', type=bool, default=True, help='Add seed data')
    args = parser.parse_args()
    
    setup = FirestoreSetup()
    success = setup.run_full_setup(seed_data=args.seed)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
