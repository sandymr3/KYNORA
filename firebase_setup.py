import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import json
import os

class FirestoreSetup:
    def __init__(self, service_account_path):
        """
        Initialize Firebase Admin SDK
        """
        try:
            # Initialize Firebase Admin SDK
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            print("✅ Firebase Admin SDK initialized successfully!")
        except Exception as e:
            print(f"❌ Error initializing Firebase: {e}")
            raise

    def create_sample_data(self):
        """
        Create sample data for all collections
        """
        current_time = datetime.now()
        
        # Sample data structure
        sample_data = {
            'users': [
                {
                    'uid': 'admin_user_001',
                    'email': 'admin@handcraft.com',
                    'displayName': 'Admin User',
                    'photoURL': 'https://example.com/admin.jpg',
                    'role': 'admin',
                    'phone': '+91-9876543210',
                    'address': {
                        'street': '123 Admin Street',
                        'city': 'Mumbai',
                        'state': 'Maharashtra',
                        'zipCode': '400001',
                        'country': 'India'
                    },
                    'preferences': {
                        'currency': 'INR',
                        'language': 'en',
                        'notifications': {
                            'email': True,
                            'sms': True,
                            'push': True
                        }
                    },
                    'createdAt': current_time,
                    'updatedAt': current_time,
                    'isActive': True,
                    'lastLoginAt': current_time
                },
                {
                    'uid': 'seller_user_001',
                    'email': 'seller@artisan.com',
                    'displayName': 'Master Artisan',
                    'photoURL': 'https://example.com/seller.jpg',
                    'role': 'seller',
                    'phone': '+91-9876543211',
                    'address': {
                        'street': 'Artisan Lane',
                        'city': 'Varanasi',
                        'state': 'Uttar Pradesh',
                        'zipCode': '221001',
                        'country': 'India'
                    },
                    'preferences': {
                        'currency': 'INR',
                        'language': 'hi',
                        'notifications': {
                            'email': True,
                            'sms': False,
                            'push': True
                        }
                    },
                    'createdAt': current_time,
                    'updatedAt': current_time,
                    'isActive': True,
                    'lastLoginAt': current_time
                },
                {
                    'uid': 'buyer_user_001',
                    'email': 'buyer@example.com',
                    'displayName': 'John Customer',
                    'photoURL': 'https://example.com/buyer.jpg',
                    'role': 'buyer',
                    'phone': '+91-9876543212',
                    'address': {
                        'street': '456 Customer Street',
                        'city': 'Delhi',
                        'state': 'Delhi',
                        'zipCode': '110001',
                        'country': 'India'
                    },
                    'preferences': {
                        'currency': 'INR',
                        'language': 'en',
                        'notifications': {
                            'email': True,
                            'sms': True,
                            'push': True
                        }
                    },
                    'createdAt': current_time,
                    'updatedAt': current_time,
                    'isActive': True,
                    'lastLoginAt': current_time
                }
            ],
            'categories': [
                {
                    'id': 'textiles',
                    'name': 'Textiles & Fabrics',
                    'description': 'Handwoven textiles and fabrics',
                    'parentId': None,
                    'image': 'https://example.com/textiles.jpg',
                    'isActive': True,
                    'sortOrder': 1,
                    'seo': {
                        'slug': 'textiles-fabrics',
                        'metaTitle': 'Handwoven Textiles & Fabrics',
                        'metaDescription': 'Beautiful handcrafted textiles and fabrics'
                    },
                    'createdAt': current_time
                },
                {
                    'id': 'pottery',
                    'name': 'Pottery & Ceramics',
                    'description': 'Handcrafted pottery and ceramic items',
                    'parentId': None,
                    'image': 'https://example.com/pottery.jpg',
                    'isActive': True,
                    'sortOrder': 2,
                    'seo': {
                        'slug': 'pottery-ceramics',
                        'metaTitle': 'Handcrafted Pottery & Ceramics',
                        'metaDescription': 'Beautiful handmade pottery and ceramic items'
                    },
                    'createdAt': current_time
                },
                {
                    'id': 'sarees',
                    'name': 'Sarees',
                    'description': 'Traditional handwoven sarees',
                    'parentId': 'textiles',
                    'image': 'https://example.com/sarees.jpg',
                    'isActive': True,
                    'sortOrder': 1,
                    'seo': {
                        'slug': 'handwoven-sarees',
                        'metaTitle': 'Handwoven Traditional Sarees',
                        'metaDescription': 'Beautiful handwoven traditional sarees'
                    },
                    'createdAt': current_time
                }
            ],
            'warehouses': [
                {
                    'id': 'WH001',
                    'name': 'Main Warehouse - Mumbai',
                    'address': {
                        'street': 'Industrial Estate Block A',
                        'city': 'Mumbai',
                        'state': 'Maharashtra',
                        'zipCode': '400050',
                        'country': 'India'
                    },
                    'contact': {
                        'phone': '+91-22-12345678',
                        'email': 'warehouse@handcraft.com',
                        'manager': 'Warehouse Manager'
                    },
                    'capacity': {
                        'totalSpace': 1000,
                        'usedSpace': 750,
                        'availableSpace': 250
                    },
                    'zones': [
                        {
                            'id': 'A',
                            'name': 'Textiles Zone',
                            'description': 'For textile products'
                        },
                        {
                            'id': 'B',
                            'name': 'Pottery Zone',
                            'description': 'For pottery and ceramics'
                        }
                    ],
                    'isActive': True,
                    'createdAt': current_time
                }
            ],
            'suppliers': [
                {
                    'name': 'Artisan Collective Varanasi',
                    'contactPerson': 'Master Artisan Sharma',
                    'email': 'contact@artisancollective.com',
                    'phone': '+91-9876543210',
                    'address': {
                        'street': 'Artisan Village, Sarnath Road',
                        'city': 'Varanasi',
                        'state': 'Uttar Pradesh',
                        'zipCode': '221001',
                        'country': 'India'
                    },
                    'bankDetails': {
                        'accountName': 'Artisan Collective',
                        'accountNumber': '1234567890',
                        'ifscCode': 'SBIN0001234',
                        'bankName': 'State Bank of India'
                    },
                    'businessDetails': {
                        'gstNumber': '09ABCDE1234F1Z5',
                        'panNumber': 'ABCDE1234F',
                        'businessType': 'Handcraft Manufacturing'
                    },
                    'paymentTerms': 'Net 30 days',
                    'isActive': True,
                    'rating': 4.5,
                    'productsSupplied': ['textiles', 'pottery'],
                    'createdAt': current_time
                }
            ],
            'products': [
                {
                    'title': 'Handwoven Silk Saree - Banarasi',
                    'description': 'Beautiful handcrafted silk saree from Varanasi with intricate gold work',
                    'category': 'textiles',
                    'subcategory': 'sarees',
                    'tags': ['handwoven', 'silk', 'traditional', 'banarasi'],
                    'sellerId': 'seller_user_001',
                    'sellerInfo': {
                        'name': 'Master Artisan',
                        'location': 'Varanasi, UP'
                    },
                    'pricing': {
                        'basePrice': 8000,
                        'salePrice': 7200,
                        'currency': 'INR',
                        'isOnSale': True,
                        'saleEndDate': current_time + timedelta(days=30)
                    },
                    'inventory': {
                        'sku': 'BSS001',
                        'totalStock': 5,
                        'reservedStock': 1,
                        'availableStock': 4,
                        'lowStockThreshold': 2,
                        'trackInventory': True
                    },
                    'media': {
                        'images': [
                            {
                                'url': 'https://example.com/saree1-front.jpg',
                                'alt': 'Front view of Banarasi silk saree',
                                'isPrimary': True
                            },
                            {
                                'url': 'https://example.com/saree1-detail.jpg',
                                'alt': 'Detail view of gold work',
                                'isPrimary': False
                            }
                        ],
                        'videos': []
                    },
                    'specifications': {
                        'material': 'Pure Silk',
                        'dimensions': '6m x 1.2m',
                        'weight': '900g',
                        'careInstructions': 'Dry clean only'
                    },
                    'shipping': {
                        'weight': 0.9,
                        'dimensions': {
                            'length': 35,
                            'width': 25,
                            'height': 8
                        },
                        'shippingClass': 'premium'
                    },
                    'seo': {
                        'metaTitle': 'Handwoven Banarasi Silk Saree - Premium Quality',
                        'metaDescription': 'Beautiful handwoven Banarasi silk saree with intricate gold work',
                        'slug': 'handwoven-banarasi-silk-saree-bss001'
                    },
                    'status': 'active',
                    'featured': True,
                    'createdAt': current_time,
                    'updatedAt': current_time
                }
            ]
        }
        
        return sample_data

    def create_collections(self):
        """
        Create all Firestore collections with sample data
        """
        print("🚀 Starting database setup...")
        
        sample_data = self.create_sample_data()
        
        # Create collections with sample data
        collections_created = 0
        
        try:
            # Create Users
            print("📝 Creating Users collection...")
            for user_data in sample_data['users']:
                doc_ref = self.db.collection('users').document(user_data['uid'])
                doc_ref.set(user_data)
            print("✅ Users collection created")
            collections_created += 1
            
            # Create Categories
            print("📝 Creating Categories collection...")
            for category_data in sample_data['categories']:
                doc_ref = self.db.collection('categories').document(category_data['id'])
                doc_ref.set(category_data)
            print("✅ Categories collection created")
            collections_created += 1
            
            # Create Warehouses
            print("📝 Creating Warehouses collection...")
            for warehouse_data in sample_data['warehouses']:
                doc_ref = self.db.collection('warehouses').document(warehouse_data['id'])
                doc_ref.set(warehouse_data)
            print("✅ Warehouses collection created")
            collections_created += 1
            
            # Create Suppliers
            print("📝 Creating Suppliers collection...")
            for supplier_data in sample_data['suppliers']:
                doc_ref = self.db.collection('suppliers').add(supplier_data)
            print("✅ Suppliers collection created")
            collections_created += 1
            
            # Create Products
            print("📝 Creating Products collection...")
            for product_data in sample_data['products']:
                doc_ref = self.db.collection('products').add(product_data)
            print("✅ Products collection created")
            collections_created += 1
            
            # Create empty collections for future use
            empty_collections = [
                'orders', 'inventory', 'carts', 'reviews', 'notifications'
            ]
            
            for collection_name in empty_collections:
                print(f"📝 Creating {collection_name} collection...")
                # Create a temporary document to initialize the collection
                temp_doc = {
                    'initialized': True,
                    'createdAt': datetime.now(),
                    'note': f'This is a placeholder document to initialize the {collection_name} collection'
                }
                doc_ref = self.db.collection(collection_name).document('_init')
                doc_ref.set(temp_doc)
                print(f"✅ {collection_name} collection created")
                collections_created += 1
            
            print(f"\n🎉 Database setup completed successfully!")
            print(f"📊 Total collections created: {collections_created}")
            print("\n📋 Collections created:")
            print("   • users (with 3 sample users)")
            print("   • categories (with 3 sample categories)")  
            print("   • warehouses (with 1 sample warehouse)")
            print("   • suppliers (with 1 sample supplier)")
            print("   • products (with 1 sample product)")
            print("   • orders (empty, ready for use)")
            print("   • inventory (empty, ready for use)")
            print("   • carts (empty, ready for use)")
            print("   • reviews (empty, ready for use)")
            print("   • notifications (empty, ready for use)")
            
        except Exception as e:
            print(f"❌ Error creating collections: {e}")
            raise

    def setup_security_rules(self):
        """
        Display security rules that need to be set up manually
        """
        print("\n🔒 SECURITY RULES SETUP:")
        print("Please manually add these security rules to your Firestore:")
        print("-" * 60)
        
        security_rules = '''
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      allow read: if request.auth != null && request.auth.token.role == 'admin';
    }
    
    // Products - public read, seller/admin write
    match /products/{productId} {
      allow read: if resource.data.status == 'active';
      allow write: if request.auth != null && 
        (request.auth.token.role == 'admin' || 
         request.auth.token.role == 'seller');
    }
    
    // Orders - customer and admin access
    match /orders/{orderId} {
      allow read, write: if request.auth != null && 
        (request.auth.uid == resource.data.customerId || 
         request.auth.token.role == 'admin');
    }
    
    // Categories - public read, admin write
    match /categories/{categoryId} {
      allow read: if true;
      allow write: if request.auth != null && request.auth.token.role == 'admin';
    }
    
    // Inventory - warehouse manager and admin only
    match /inventory/{inventoryId} {
      allow read, write: if request.auth != null && 
        (request.auth.token.role == 'warehouse_manager' || 
         request.auth.token.role == 'admin');
    }
    
    // Warehouses - admin and warehouse manager access
    match /warehouses/{warehouseId} {
      allow read, write: if request.auth != null && 
        (request.auth.token.role == 'admin' || 
         request.auth.token.role == 'warehouse_manager');
    }
    
    // Reviews - public read, authenticated write
    match /reviews/{reviewId} {
      allow read: if resource.data.status == 'approved';
      allow create: if request.auth != null;
      allow update, delete: if request.auth != null && 
        (request.auth.uid == resource.data.customerId || 
         request.auth.token.role == 'admin');
    }
    
    // Notifications - user can read their own
    match /notifications/{notificationId} {
      allow read, update: if request.auth != null && 
        request.auth.uid == resource.data.userId;
      allow create: if request.auth != null && 
        request.auth.token.role in ['admin', 'seller'];
    }
    
    // Carts - user can access their own cart
    match /carts/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Suppliers - admin only
    match /suppliers/{supplierId} {
      allow read, write: if request.auth != null && request.auth.token.role == 'admin';
    }
  }
}
        '''
        print(security_rules)

def main():
    """
    Main function to run the database setup
    """
    print("🔥 Firestore E-Commerce Database Setup")
    print("=" * 50)
    
    # Check for service account file
    service_account_path = input("Enter path to your Firebase service account JSON file: ").strip()
    
    if not os.path.exists(service_account_path):
        print(f"❌ Service account file not found: {service_account_path}")
        return
    
    try:
        # Initialize setup
        setup = FirestoreSetup(service_account_path)
        
        # Create collections
        setup.create_collections()
        
        # Display security rules
        setup.setup_security_rules()
        
        print("\n✨ Next Steps:")
        print("1. Set up the security rules in Firebase Console")
        print("2. Configure Firebase indexes for better performance")
        print("3. Set up Firebase Authentication")
        print("4. Configure your FastAPI application to use these collections")
        print("5. Set up Redis for caching (optional)")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")

if __name__ == "__main__":
    main()