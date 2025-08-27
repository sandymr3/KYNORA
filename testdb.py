"""
Comprehensive Database Test Suite for KYNORA E-commerce API
Tests all database retrieval functions to verify their working status
"""

import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
import dotenv
dotenv.load_dotenv()

# Import Firebase Admin and initialize
import firebase_admin
from firebase_admin import credentials

# Initialize Firebase Admin SDK
try:
    # Check if Firebase is already initialized
    firebase_admin.get_app()
except ValueError:
    # Create service account credentials from environment variables
    firebase_credentials = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("FIREBASE_PRIVATE_KEY") else None,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
    }
    
    # Initialize Firebase
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'projectId': os.getenv("FIRESTORE_PROJECT_ID")
    })

# Import our database handler
from firestore_ecommerce_db import FirestoreEcommerceDB

class DatabaseTester:
    def __init__(self):
        self.db = FirestoreEcommerceDB()
        self.test_results = []
        
    def log_test(self, test_name: str, success: bool, message: str = "", data: Any = None):
        """Log test results"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        if data and success:
            result['data_count'] = len(data) if isinstance(data, list) else 1
        self.test_results.append(result)
        
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {test_name}: {message}")
        
    def test_user_operations(self):
        """Test all user-related retrieval functions"""
        print("\n[INFO] Testing User Operations...")
        
        # Test get_user_profile
        try:
            result = self.db.get_user_profile("test_user_123")
            if result['success'] or 'not found' in result.get('error', '').lower():
                self.log_test("get_user_profile", True, "Function working (user may not exist)")
            else:
                self.log_test("get_user_profile", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_profile", False, str(e))
            
        # Test get_users_by_role
        try:
            result = self.db.get_users_by_role("customer", limit=5)
            if result['success']:
                users = result['data']['users']
                self.log_test("get_users_by_role", True, f"Retrieved {len(users)} users", users)
            else:
                self.log_test("get_users_by_role", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_users_by_role", False, str(e))
    
    def test_product_operations(self):
        """Test all product-related retrieval functions"""
        print("\n[INFO] Testing Product Operations...")
        
        # Test get_product
        try:
            result = self.db.get_product("test_product_123", increment_view=False)
            if result['success'] or 'not found' in result.get('error', '').lower():
                self.log_test("get_product", True, "Function working (product may not exist)")
            else:
                self.log_test("get_product", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_product", False, str(e))
            
        # Test get_active_products
        try:
            result = self.db.get_active_products(limit=5)
            if result['success']:
                products = result['data']['products']
                self.log_test("get_active_products", True, f"Retrieved {len(products)} active products", products)
            else:
                self.log_test("get_active_products", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_active_products", False, str(e))
            
        # Test get_products_with_filters
        try:
            filters = {'min_price': 10.0, 'max_price': 1000.0}
            result = self.db.get_products_with_filters(filters, limit=5)
            if result['success']:
                products = result['data']['products']
                self.log_test("get_products_with_filters", True, f"Retrieved {len(products)} filtered products", products)
            else:
                self.log_test("get_products_with_filters", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_products_with_filters", False, str(e))
            
        # Test search_products
        try:
            result = self.db.search_products("test", limit=5)
            if result['success']:
                products = result['data']['products']
                self.log_test("search_products", True, f"Found {len(products)} products matching 'test'", products)
            else:
                self.log_test("search_products", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("search_products", False, str(e))
            
        # Test get_featured_products
        try:
            result = self.db.get_featured_products(limit=5)
            if result['success']:
                products = result['data']['featured_products']
                self.log_test("get_featured_products", True, f"Retrieved {len(products)} featured products", products)
            else:
                self.log_test("get_featured_products", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_featured_products", False, str(e))
            
        # Test get_popular_products
        try:
            result = self.db.get_popular_products(limit=5, metric='sales')
            if result['success']:
                products = result['data']['popular_products']
                self.log_test("get_popular_products", True, f"Retrieved {len(products)} popular products", products)
            else:
                self.log_test("get_popular_products", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_popular_products", False, str(e))
    
    def test_order_operations(self):
        """Test all order-related retrieval functions"""
        print("\n[INFO] Testing Order Operations...")
        
        # Test get_order
        try:
            result = self.db.get_order("test_order_123", include_items=True, include_timeline=True)
            if result['success'] or 'not found' in result.get('error', '').lower():
                self.log_test("get_order", True, "Function working (order may not exist)")
            else:
                self.log_test("get_order", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_order", False, str(e))
            
        # Test get_user_orders
        try:
            result = self.db.get_user_orders("test_user_123", limit=5)
            if result['success']:
                orders = result['data']['orders']
                self.log_test("get_user_orders", True, f"Retrieved {len(orders)} user orders", orders)
            else:
                self.log_test("get_user_orders", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_orders", False, str(e))
            
        # Test get_seller_orders
        try:
            result = self.db.get_seller_orders("test_seller_123", limit=5)
            if result['success']:
                orders = result['data']['orders']
                self.log_test("get_seller_orders", True, f"Retrieved {len(orders)} seller orders", orders)
            else:
                self.log_test("get_seller_orders", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_seller_orders", False, str(e))
    
    def test_category_operations(self):
        """Test all category-related retrieval functions"""
        print("\n[INFO] Testing Category Operations...")
        
        # Test list_categories (root categories)
        try:
            result = self.db.list_categories()
            if result['success']:
                categories = result['data']['categories']
                self.log_test("list_categories", True, f"Retrieved {len(categories)} root categories", categories)
            else:
                self.log_test("list_categories", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("list_categories", False, str(e))
            
        # Test list_categories (subcategories)
        try:
            result = self.db.list_categories(parent_id="test_parent_123")
            if result['success']:
                categories = result['data']['categories']
                self.log_test("list_categories_with_parent", True, f"Retrieved {len(categories)} subcategories", categories)
            else:
                self.log_test("list_categories_with_parent", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("list_categories_with_parent", False, str(e))
    
    def test_inventory_operations(self):
        """Test all inventory-related retrieval functions"""
        print("\n[INFO] Testing Inventory Operations...")
        
        # Test get_product_inventory
        try:
            result = self.db.get_product_inventory("test_product_123")
            if result['success']:
                inventory = result['data']['inventory_records']
                total_stock = result['data']['total_stock']
                self.log_test("get_product_inventory", True, f"Retrieved inventory: {len(inventory)} records, {total_stock} total stock", inventory)
            else:
                self.log_test("get_product_inventory", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_product_inventory", False, str(e))
            
        # Test get_low_stock_items
        try:
            result = self.db.get_low_stock_items(limit=10)
            if result['success']:
                items = result['data']['low_stock_items']
                self.log_test("get_low_stock_items", True, f"Retrieved {len(items)} low stock items", items)
            else:
                self.log_test("get_low_stock_items", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_low_stock_items", False, str(e))
            
        # Test get_warehouse_inventory
        try:
            result = self.db.get_warehouse_inventory("test_warehouse_123", limit=10)
            if result['success']:
                inventory = result['data']['inventory_records']
                self.log_test("get_warehouse_inventory", True, f"Retrieved {len(inventory)} warehouse inventory records", inventory)
            else:
                self.log_test("get_warehouse_inventory", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_warehouse_inventory", False, str(e))
    
    def test_warehouse_operations(self):
        """Test all warehouse-related retrieval functions"""
        print("\n[INFO] Testing Warehouse Operations...")
        
        # Test list_warehouses
        try:
            result = self.db.list_warehouses(active_only=True)
            if result['success']:
                warehouses = result['data']['warehouses']
                self.log_test("list_warehouses", True, f"Retrieved {len(warehouses)} active warehouses", warehouses)
            else:
                self.log_test("list_warehouses", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("list_warehouses", False, str(e))
            
        # Test get_warehouse_details
        try:
            result = self.db.get_warehouse_details("test_warehouse_123")
            if result['success'] or 'not found' in result.get('error', '').lower():
                self.log_test("get_warehouse_details", True, "Function working (warehouse may not exist)")
            else:
                self.log_test("get_warehouse_details", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_warehouse_details", False, str(e))
    
    def test_cart_operations(self):
        """Test all cart-related retrieval functions"""
        print("\n[INFO] Testing Cart Operations...")
        
        # Test get_user_cart
        try:
            result = self.db.get_user_cart("test_user_123")
            if result['success']:
                cart = result['data']
                items_count = len(cart.get('items', []))
                self.log_test("get_user_cart", True, f"Retrieved cart with {items_count} items", cart)
            else:
                self.log_test("get_user_cart", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_cart", False, str(e))
    
    def test_review_operations(self):
        """Test all review-related retrieval functions"""
        print("\n[INFO] Testing Review Operations...")
        
        # Test get_product_reviews
        try:
            result = self.db.get_product_reviews("test_product_123", status='approved', limit=5)
            if result['success']:
                reviews = result['data']['reviews']
                self.log_test("get_product_reviews", True, f"Retrieved {len(reviews)} product reviews", reviews)
            else:
                self.log_test("get_product_reviews", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_product_reviews", False, str(e))
            
        # Test get_user_reviews
        try:
            result = self.db.get_user_reviews("test_user_123", limit=5)
            if result['success']:
                reviews = result['data']['reviews']
                self.log_test("get_user_reviews", True, f"Retrieved {len(reviews)} user reviews", reviews)
            else:
                self.log_test("get_user_reviews", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_reviews", False, str(e))
    
    def test_notification_operations(self):
        """Test all notification-related retrieval functions"""
        print("\n[INFO] Testing Notification Operations...")
        
        # Test get_user_notifications
        try:
            result = self.db.get_user_notifications("test_user_123", unread_only=False, limit=5)
            if result['success']:
                notifications = result['data']['notifications']
                self.log_test("get_user_notifications", True, f"Retrieved {len(notifications)} notifications", notifications)
            else:
                self.log_test("get_user_notifications", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_notifications", False, str(e))
            
        # Test get_user_notifications (unread only)
        try:
            result = self.db.get_user_notifications("test_user_123", unread_only=True, limit=5)
            if result['success']:
                notifications = result['data']['notifications']
                self.log_test("get_user_notifications_unread", True, f"Retrieved {len(notifications)} unread notifications", notifications)
            else:
                self.log_test("get_user_notifications_unread", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_user_notifications_unread", False, str(e))
    
    def test_supplier_operations(self):
        """Test all supplier-related retrieval functions"""
        print("\n[INFO] Testing Supplier Operations...")
        
        # Test list_suppliers
        try:
            result = self.db.list_suppliers(active_only=True)
            if result['success']:
                suppliers = result['data']['suppliers']
                self.log_test("list_suppliers", True, f"Retrieved {len(suppliers)} active suppliers", suppliers)
            else:
                self.log_test("list_suppliers", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("list_suppliers", False, str(e))
            
        # Test get_supplier_by_id
        try:
            result = self.db.get_supplier_by_id("test_supplier_123")
            if result['success'] or 'not found' in result.get('error', '').lower():
                self.log_test("get_supplier_by_id", True, "Function working (supplier may not exist)")
            else:
                self.log_test("get_supplier_by_id", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_supplier_by_id", False, str(e))
    
    def test_dashboard_operations(self):
        """Test all dashboard and analytics retrieval functions"""
        print("\n[INFO] Testing Dashboard & Analytics Operations...")
        
        # Test get_dashboard_stats (admin view)
        try:
            result = self.db.get_dashboard_stats()
            if result['success']:
                stats = result['data']
                self.log_test("get_dashboard_stats_admin", True, f"Retrieved admin dashboard stats", stats)
            else:
                self.log_test("get_dashboard_stats_admin", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_dashboard_stats_admin", False, str(e))
            
        # Test get_dashboard_stats (seller view)
        try:
            result = self.db.get_dashboard_stats(seller_id="test_seller_123")
            if result['success']:
                stats = result['data']
                self.log_test("get_dashboard_stats_seller", True, f"Retrieved seller dashboard stats", stats)
            else:
                self.log_test("get_dashboard_stats_seller", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_dashboard_stats_seller", False, str(e))
            
        # Test get_sales_stats
        try:
            start_date = datetime.now() - timedelta(days=30)
            end_date = datetime.now()
            result = self.db.get_sales_stats("test_seller_123", start_date, end_date)
            if result['success']:
                stats = result['data']
                self.log_test("get_sales_stats", True, f"Retrieved sales stats for 30 days", stats)
            else:
                self.log_test("get_sales_stats", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_sales_stats", False, str(e))
            
        # Test get_low_stock_alerts
        try:
            result = self.db.get_low_stock_alerts(limit=10)
            if result['success']:
                alerts = result['data']['low_stock_alerts']
                self.log_test("get_low_stock_alerts", True, f"Retrieved {len(alerts)} low stock alerts", alerts)
            else:
                self.log_test("get_low_stock_alerts", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("get_low_stock_alerts", False, str(e))
    
    def test_utility_operations(self):
        """Test utility functions"""
        print("\n[INFO] Testing Utility Operations...")
        
        # Test health_check
        try:
            result = self.db.health_check()
            if result['success']:
                self.log_test("health_check", True, "Database connection healthy")
            else:
                self.log_test("health_check", False, result.get('error', 'Unknown error'))
        except Exception as e:
            self.log_test("health_check", False, str(e))
    
    def run_all_tests(self):
        """Run all database retrieval function tests"""
        print("Starting Comprehensive Database Retrieval Function Tests...")
        print("=" * 70)
        
        # Run all test categories
        self.test_user_operations()
        self.test_product_operations()
        self.test_order_operations()
        self.test_category_operations()
        self.test_inventory_operations()
        self.test_warehouse_operations()
        self.test_cart_operations()
        self.test_review_operations()
        self.test_notification_operations()
        self.test_supplier_operations()
        self.test_dashboard_operations()
        self.test_utility_operations()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 70)
        print("TEST RESULTS SUMMARY")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\nFailed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status = "PASS" if result['success'] else "FAIL"
            data_info = f" ({result.get('data_count', 0)} records)" if result.get('data_count') is not None else ""
            print(f"  [{status}] {result['test']}{data_info}: {result['message']}")
        
        # Save results to file
        with open('test_results.json', 'w') as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nDetailed results saved to 'test_results.json'")

def main():
    """Main function to run the database tests"""
    try:
        tester = DatabaseTester()
        tester.run_all_tests()
    except Exception as e:
        print(f"Critical Error: {str(e)}")
        print("Make sure Firebase is properly configured and serviceAccount.json exists")

if __name__ == "__main__":
    main()