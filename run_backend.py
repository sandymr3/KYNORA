#!/usr/bin/env python
"""
Enhanced Kynora E-commerce Backend with Firebase Integration
Works with Python 3.14 using simple HTTP server
Includes central authentication system similar to fastapi_ecommerce_server.py
"""
import json
import os
import sys
import logging
import traceback
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import firebase_admin
from firebase_admin import credentials, firestore, auth
from firebase_admin.firestore import SERVER_TIMESTAMP
from dotenv import load_dotenv

# Custom JSON encoder to handle Firestore types
class FirestoreJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__class__') and 'DatetimeWithNanoseconds' in str(obj.__class__):
            # Convert Firestore timestamp to ISO format string
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return super().default(obj)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
auth_logger = logging.getLogger('auth')
db_logger = logging.getLogger('database')

# Firebase configuration
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "kynora-ecommerce")

# Initialize Firebase
db = None
firebase_initialized = False

try:
    # Check if Firebase is already initialized
    firebase_admin.get_app()
    firebase_initialized = True
    db = firestore.client()
    logger.info("Firebase already initialized")
except ValueError:
    # Initialize Firebase
    try:
        if os.path.exists(FIREBASE_CREDENTIALS_PATH):
            cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {
                'projectId': FIREBASE_PROJECT_ID
            })
            db = firestore.client()
            firebase_initialized = True
            logger.info(f"✅ Firebase initialized successfully for project: {FIREBASE_PROJECT_ID}")
        else:
            logger.warning(f"⚠️ Firebase credentials not found at: {FIREBASE_CREDENTIALS_PATH}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firebase: {e}")
        logger.warning("Running in mock mode without database")

# Sample data for fallback when database is not available
SAMPLE_PRODUCTS = [
    {
        "id": "prod_001",
        "product_id": "prod_001", 
        "title": "Wireless Headphones",
        "description": "Premium wireless headphones with noise cancellation",
        "price": 199.99,
        "category_id": "electronics",
        "seller_id": "seller_001",
        "images": ["https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=300"],
        "inventory_quantity": 50,
        "tags": ["electronics", "audio"],
        "is_featured": True,
        "status": "active",
        "view_count": 120,
        "average_rating": 4.5,
        "review_count": 23
    },
    {
        "id": "prod_002",
        "product_id": "prod_002",
        "title": "Smart Watch",
        "description": "Advanced fitness tracking smartwatch",
        "price": 299.99,
        "category_id": "electronics",
        "seller_id": "seller_001",
        "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=300"],
        "inventory_quantity": 30,
        "tags": ["electronics", "wearable"],
        "is_featured": True,
        "status": "active",
        "view_count": 85,
        "average_rating": 4.3,
        "review_count": 15
    },
    {
        "id": "prod_003",
        "product_id": "prod_003",
        "title": "Laptop Backpack",
        "description": "Durable laptop backpack with USB charging port",
        "price": 79.99,
        "category_id": "accessories",
        "seller_id": "seller_002",
        "images": ["https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=300"],
        "inventory_quantity": 100,
        "tags": ["accessories", "bags"],
        "is_featured": False,
        "status": "active",
        "view_count": 45,
        "average_rating": 4.7,
        "review_count": 8
    },
    {
        "id": "prod_004",
        "product_id": "prod_004",
        "title": "Bluetooth Speaker",
        "description": "Portable waterproof Bluetooth speaker",
        "price": 59.99,
        "category_id": "electronics",
        "seller_id": "seller_001",
        "images": ["https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=300"],
        "inventory_quantity": 75,
        "tags": ["electronics", "audio", "portable"],
        "is_featured": True,
        "status": "active",
        "view_count": 200,
        "average_rating": 4.6,
        "review_count": 45
    },
    {
        "id": "prod_005",
        "product_id": "prod_005",
        "title": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with precision tracking",
        "price": 29.99,
        "category_id": "accessories",
        "seller_id": "seller_003",
        "images": ["https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=300"],
        "inventory_quantity": 150,
        "tags": ["accessories", "computer"],
        "is_featured": False,
        "status": "active",
        "view_count": 95,
        "average_rating": 4.2,
        "review_count": 18
    }
]

CATEGORIES = [
    {"id": "electronics", "name": "Electronics", "description": "Electronic devices"},
    {"id": "accessories", "name": "Accessories", "description": "Computer and phone accessories"}
]

# ==================== AUTHENTICATION SYSTEM ====================

def verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Firebase ID token and return user information.
    Similar to get_current_user in fastapi_ecommerce_server.py
    """
    if not firebase_initialized:
        # Return mock user for testing when Firebase is not available
        return {
            "id": "mock_user_id",
            "email": "test@example.com",
            "name": "Mock User",
            "role": "customer",
            "email_verified": True
        }
    
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        auth_logger.debug(f"Token verified for UID: {uid}")
        
        # Get user data from Firestore
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            # Auto-create new user profile if it doesn't exist
            if email:
                user_data = {
                    'uid': uid,
                    'email': email,
                    'displayName': decoded_token.get('name', email.split('@')[0]),
                    'photoURL': decoded_token.get('picture', ''),
                    'role': decoded_token.get('role', 'customer'),
                    'phone': decoded_token.get('phone_number', ''),
                    'address': {},
                    'preferences': {
                        'currency': 'USD',
                        'language': 'en',
                        'notifications': {
                            'email': True,
                            'sms': False,
                            'push': True
                        }
                    },
                    'createdAt': datetime.now(),
                    'updatedAt': datetime.now(),
                    'isActive': True,
                    'lastLoginAt': datetime.now(),
                    'emailVerified': decoded_token.get('email_verified', False)
                }
                
                # Create user document
                db.collection('users').document(uid).set(user_data)
                logger.info(f"Created new user profile for UID: {uid}, Email: {email}")
            else:
                # Return basic info if no email available
                return {
                    'id': uid,
                    'email': '',
                    'name': 'User',
                    'role': 'customer',
                    'email_verified': False
                }
        else:
            user_data = user_doc.to_dict()
            
            # Update last login time
            try:
                db.collection('users').document(uid).update({
                    'lastLoginAt': datetime.now()
                })
            except Exception as e:
                logger.warning(f"Failed to update last login time: {e}")
        
        # Check if account is active
        if not user_data.get('isActive', True):
            auth_logger.warning(f"Deactivated user access attempt: {uid}")
            return None
        
        # Return user info
        return {
            "id": uid,
            "email": user_data.get('email', email),
            "name": user_data.get('displayName', ''),
            "role": user_data.get('role', 'customer'),
            "email_verified": user_data.get('emailVerified', False),
            "phone": user_data.get('phone', ''),
            "photo_url": user_data.get('photoURL', '')
        }
        
    except auth.InvalidIdTokenError as e:
        auth_logger.warning(f"Invalid token: {e}")
        return None
    except auth.ExpiredIdTokenError as e:
        auth_logger.warning(f"Expired token: {e}")
        return None
    except auth.RevokedIdTokenError as e:
        auth_logger.warning(f"Revoked token: {e}")
        return None
    except Exception as e:
        auth_logger.error(f"Authentication error: {e}")
        return None

def get_auth_token(headers: Dict[str, str]) -> Optional[str]:
    """Extract authentication token from headers"""
    authorization = headers.get('Authorization', '') or headers.get('authorization', '')
    if authorization and authorization.startswith('Bearer '):
        return authorization.replace('Bearer ', '')
    return None

def create_success_response(data: Any = None, message: str = "Success") -> Dict:
    """Create standardized success response"""
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return response

def create_error_response(message: str, error_code: str = "ERROR", status_code: int = 400) -> Dict:
    """Create standardized error response"""
    return {
        "success": False,
        "error": message,
        "error_code": error_code,
        "status_code": status_code
    }

# ==================== DATABASE QUERY FUNCTIONS ====================

def get_products_from_db(filters: Dict = None) -> List[Dict]:
    """Get products from Firestore with optional filters"""
    if not db:
        # Filter sample products if database is not available
        products = SAMPLE_PRODUCTS.copy()
        if filters and filters.get('is_featured'):
            products = [p for p in products if p.get('is_featured')]
        if filters and filters.get('limit'):
            products = products[:filters['limit']]
        return products
    
    try:
        # Start with products collection
        query = db.collection('products')
        
        # For featured products, we need to handle compound index requirements
        if filters and filters.get('is_featured'):
            # Try compound query first
            try:
                query = query.where('status', '==', 'active').where('is_featured', '==', True)
            except Exception as e:
                logger.warning(f"Compound index may be missing for featured products: {e}")
                # Fall back to fetching all active products and filtering in memory
                query = db.collection('products').where('status', '==', 'active')
        else:
            query = query.where('status', '==', 'active')
        
        if filters:
            if filters.get('category_id'):
                query = query.where('category_id', '==', filters['category_id'])
            if filters.get('seller_id'):
                query = query.where('seller_id', '==', filters['seller_id'])
        
        # Add sorting (be careful with compound indexes)
        sort_by = filters.get('sort_by', 'created_at') if filters else 'created_at'
        sort_order = filters.get('sort_order', 'desc') if filters else 'desc'
        
        try:
            if sort_by == 'view_count':
                query = query.order_by('view_count', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
            elif sort_by == 'price':
                query = query.order_by('price', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
            else:
                # Default sort by created_at or fall back if it doesn't exist
                try:
                    query = query.order_by('created_at', direction=firestore.Query.DESCENDING if sort_order == 'desc' else firestore.Query.ASCENDING)
                except Exception:
                    # If created_at doesn't exist, don't sort
                    pass
        except Exception as e:
            logger.warning(f"Sorting may require compound index: {e}")
        
        # Apply limit
        limit = filters.get('limit', 20) if filters else 20
        query = query.limit(limit)
        
        products = []
        for doc in query.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            
            # Apply additional filters (especially for is_featured if compound index is missing)
            if filters:
                # Check is_featured filter if we couldn't apply it in the query
                if filters.get('is_featured') is not None:
                    if product.get('is_featured', False) != filters['is_featured']:
                        continue
                
                # Search filter
                search_query = filters.get('q', '').lower()
                if search_query:
                    if not (search_query in product.get('title', '').lower() or
                            search_query in product.get('description', '').lower()):
                        continue
                
                # Price filters
                min_price = filters.get('min_price')
                max_price = filters.get('max_price')
                if min_price is not None and product.get('price', 0) < min_price:
                    continue
                if max_price is not None and product.get('price', 0) > max_price:
                    continue
            
            products.append(product)
            
            # Stop if we have enough products (for cases where we filter in memory)
            if len(products) >= limit:
                break
        
        return products
        
    except Exception as e:
        logger.error(f"Error fetching products from database: {e}")
        # Fall back to sample data
        return SAMPLE_PRODUCTS

def get_single_product(product_id: str) -> Optional[Dict]:
    """Get single product by ID from Firestore"""
    if not db:
        return next((p for p in SAMPLE_PRODUCTS if p['id'] == product_id), None)
    
    try:
        doc = db.collection('products').document(product_id).get()
        if doc.exists:
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            return product
        return None
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        return None

def increment_product_view(product_id: str) -> Dict:
    """Increment product view count"""
    if not db:
        product = next((p for p in SAMPLE_PRODUCTS if p['id'] == product_id), None)
        if product:
            product['view_count'] = product.get('view_count', 0) + 1
            return {
                'product_id': product_id,
                'view_count': product['view_count']
            }
        return None
    
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        # Atomic increment
        doc_ref.update({
            'view_count': firestore.Increment(1),
            'updatedAt': datetime.now()
        })
        
        # Get updated count
        updated_doc = doc_ref.get()
        new_count = updated_doc.to_dict().get('view_count', 0)
        
        return {
            'product_id': product_id,
            'view_count': new_count
        }
        
    except Exception as e:
        logger.error(f"Error incrementing view count for {product_id}: {e}")
        return None

def create_product(product_data: Dict, user_id: str) -> Optional[Dict]:
    """Create a new product in Firestore"""
    if not db:
        logger.warning("Cannot create product: Database not connected")
        return None
    
    try:
        # Validate required fields
        required_fields = ['title', 'description', 'price', 'category_id']
        for field in required_fields:
            if field not in product_data or not product_data[field]:
                raise ValueError(f"Missing required field: {field}")
        
        # Prepare product document
        now = datetime.now()
        new_product = {
            'title': product_data['title'],
            'description': product_data['description'],
            'price': float(product_data['price']),
            'category_id': product_data['category_id'],
            'seller_id': product_data.get('seller_id', user_id),
            'images': product_data.get('images', []),
            'inventory_quantity': int(product_data.get('inventory_quantity', 0)),
            'tags': product_data.get('tags', []),
            'is_featured': product_data.get('is_featured', False),
            'status': product_data.get('status', 'active'),
            'view_count': 0,
            'average_rating': 0.0,
            'review_count': 0,
            'createdAt': now,
            'updatedAt': now,
            'createdBy': user_id
        }
        
        # Add product to Firestore
        doc_ref = db.collection('products').document()
        doc_ref.set(new_product)
        
        # Get the created product with ID
        created_product = new_product.copy()
        created_product['id'] = doc_ref.id
        created_product['product_id'] = doc_ref.id
        
        logger.info(f"Product created successfully: {doc_ref.id}")
        return created_product
        
    except ValueError as e:
        logger.error(f"Validation error creating product: {e}")
        raise
    except Exception as e:
        logger.error(f"Error creating product: {e}\n{traceback.format_exc()}")
        return None

class APIHandler(BaseHTTPRequestHandler):
    def handle(self):
        """Override handle to catch SSL/TLS errors"""
        try:
            super().handle()
        except Exception as e:
            # Silently ignore SSL/TLS handshake errors
            if "Bad request" not in str(e):
                logger.error(f"Error handling request: {e}")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
    
    def send_json_response(self, data, status=200):
        """Send JSON response with proper handling of Firestore types"""
        self.send_response(status)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        # Use custom encoder to handle Firestore timestamps
        self.wfile.write(json.dumps(data, cls=FirestoreJSONEncoder).encode())
    
    def get_headers_dict(self):
        """Convert headers to dictionary"""
        headers = {}
        for header in self.headers:
            headers[header] = self.headers[header]
        return headers
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)
        headers = self.get_headers_dict()
        
        # Extract current user from token if present
        token = get_auth_token(headers)
        current_user = None
        if token:
            current_user = verify_firebase_token(token)
        
        try:
            # Health check
            if path == "/" or path == "/health":
                self.send_json_response({
                    "success": True,
                    "message": "Kynora Backend API",
                    "status": "healthy",
                    "database": "connected" if db else "disconnected",
                    "firebase": "initialized" if firebase_initialized else "not initialized"
                })
                return
            
            # Products endpoints
            elif path == "/products":
                filters = {
                    'limit': int(query_params.get('limit', [20])[0]),
                    'category_id': query_params.get('category_id', [None])[0],
                    'q': query_params.get('q', [''])[0] or query_params.get('search', [''])[0],
                    'min_price': float(query_params.get('min_price', [0])[0]) if query_params.get('min_price') else None,
                    'max_price': float(query_params.get('max_price', [0])[0]) if query_params.get('max_price') else None,
                    'sort_by': query_params.get('sort_by', ['created_at'])[0],
                    'sort_order': query_params.get('sort_order', ['desc'])[0]
                }
                
                products = get_products_from_db(filters)
                self.send_json_response(create_success_response(
                    data={
                        'products': products,
                        'total': len(products)
                    }
                ))
                return
            
            elif path == "/products/featured":
                limit = int(query_params.get('limit', [10])[0])
                filters = {
                    'is_featured': True,
                    'limit': limit
                }
                
                products = get_products_from_db(filters)
                self.send_json_response(create_success_response(
                    data={'products': products}
                ))
                return
        
            elif path == "/products/popular":
                limit = int(query_params.get('limit', [10])[0])
                filters = {
                    'sort_by': 'view_count',
                    'sort_order': 'desc',
                    'limit': limit
                }
                
                products = get_products_from_db(filters)
                self.send_json_response(create_success_response(
                    data={'products': products}
                ))
                return
        
            elif path == "/products/search":
                q = query_params.get('q', [''])[0]
                limit = int(query_params.get('limit', [20])[0])
                
                filters = {
                    'q': q,
                    'limit': limit
                }
                
                products = get_products_from_db(filters)
                self.send_json_response(create_success_response(
                    data={
                        'products': products,
                        'query': q,
                        'count': len(products)
                    },
                    message=f"Found {len(products)} products"
                ))
                return
        
            elif path.startswith("/products/") and "/reviews" in path:
                # Product reviews
                product_id = path.split("/")[2]
                # TODO: Implement proper review fetching from database
                self.send_json_response(create_success_response(
                    data=[]
                ))
                return
        
            elif path.startswith("/products/"):
                # Single product
                product_id = path.split("/")[-1]
                product = get_single_product(product_id)
                
                if product:
                    self.send_json_response(create_success_response(
                        data=product
                    ))
                else:
                    self.send_json_response(
                        create_error_response("Product not found", "NOT_FOUND"),
                        404
                    )
                return
        
            # Categories
            elif path == "/categories":
                # TODO: Fetch from database when categories collection is available
                self.send_json_response(create_success_response(
                    data={'categories': CATEGORIES}
                ))
                return
        
            # Auth endpoints
            elif path == "/auth/me":
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                self.send_json_response(create_success_response(
                    data=current_user
                ))
                return
            
            # Cart endpoints
            elif path == "/cart" or path == "/cart/summary":
                # TODO: Implement proper cart fetching for authenticated users
                self.send_json_response(create_success_response(
                    data={
                        "cart": {"items": [], "total": 0},
                        "items_count": 0,
                        "subtotal": 0,
                        "total": 0
                    }
                ))
                return
            
            # Orders
            elif path == "/orders/my-orders":
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                # TODO: Fetch orders from database
                self.send_json_response(create_success_response(
                    data={'orders': []}
                ))
                return
            
            # Users
            elif path == "/users/me":
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                self.send_json_response(create_success_response(
                    data={'user': current_user}
                ))
                return
            
            # Reviews
            elif path.startswith("/reviews/products/"):
                # TODO: Implement proper review fetching
                self.send_json_response(create_success_response(
                    data={'reviews': []}
                ))
                return
            
            # 404 Not Found
            self.send_json_response(
                create_error_response("Endpoint not found", "NOT_FOUND"),
                404
            )
            
        except Exception as e:
            logger.error(f"Error handling GET request: {e}\n{traceback.format_exc()}")
            self.send_json_response(
                create_error_response(f"Internal server error: {str(e)}", "INTERNAL_ERROR"),
                500
            )
    
    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        headers = self.get_headers_dict()
        
        # Extract current user from token if present
        token = get_auth_token(headers)
        current_user = None
        if token:
            current_user = verify_firebase_token(token)
        
        try:
            # Read request body if present
            content_length = int(self.headers.get('Content-Length', 0))
            body = None
            if content_length > 0:
                body_data = self.rfile.read(content_length)
                try:
                    body = json.loads(body_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self.send_json_response(
                        create_error_response("Invalid JSON in request body", "INVALID_JSON"),
                        400
                    )
                    return
            
            # Create product (admin only)
            if path == "/products":
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                # Check if user is admin
                if current_user.get('role') != 'admin':
                    self.send_json_response(
                        create_error_response("Admin access required", "FORBIDDEN"),
                        403
                    )
                    return
                
                if not body:
                    self.send_json_response(
                        create_error_response("Request body is required", "INVALID_REQUEST"),
                        400
                    )
                    return
                
                try:
                    created_product = create_product(body, current_user['id'])
                    if created_product:
                        self.send_json_response(create_success_response(
                            data=created_product,
                            message="Product created successfully"
                        ), 201)
                    else:
                        self.send_json_response(
                            create_error_response("Failed to create product", "CREATE_FAILED"),
                            500
                        )
                except ValueError as e:
                    self.send_json_response(
                        create_error_response(str(e), "VALIDATION_ERROR"),
                        400
                    )
                return
            
            # Increment view count
            elif path.endswith("/view") and "/products/" in path:
                product_id = path.split("/")[2]
                result = increment_product_view(product_id)
                
                if result:
                    self.send_json_response(create_success_response(
                        data=result,
                        message="Product view count incremented"
                    ))
                else:
                    self.send_json_response(
                        create_error_response("Product not found", "NOT_FOUND"),
                        404
                    )
                return
            
            # Authentication endpoints
            elif path == "/auth/login" or path == "/auth/register":
                # Firebase handles authentication directly from the frontend
                # This endpoint can be used for additional backend processing
                self.send_json_response(create_success_response(
                    message="Authentication should be handled through Firebase SDK"
                ))
                return
            
            # Cart operations (require authentication)
            elif path.startswith("/cart"):
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                # TODO: Implement cart operations
                self.send_json_response(create_success_response(
                    message="Cart operation completed"
                ))
                return
            
            # Order operations (require authentication)
            elif path.startswith("/orders"):
                if not current_user:
                    self.send_json_response(
                        create_error_response("Authentication required", "UNAUTHORIZED"),
                        401
                    )
                    return
                
                # TODO: Implement order operations
                self.send_json_response(create_success_response(
                    message="Order operation completed"
                ))
                return
            
            # Default POST response
            self.send_json_response(create_success_response(
                message="POST request received"
            ))
            
        except Exception as e:
            logger.error(f"Error handling POST request: {e}\n{traceback.format_exc()}")
            self.send_json_response(
                create_error_response(f"Internal server error: {str(e)}", "INTERNAL_ERROR"),
                500
            )
    
    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        headers = self.get_headers_dict()
        
        # Extract current user from token if present
        token = get_auth_token(headers)
        current_user = None
        if token:
            current_user = verify_firebase_token(token)
        
        if not current_user:
            self.send_json_response(
                create_error_response("Authentication required", "UNAUTHORIZED"),
                401
            )
            return
        
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = None
            if content_length > 0:
                body_data = self.rfile.read(content_length)
                try:
                    body = json.loads(body_data.decode('utf-8'))
                except json.JSONDecodeError:
                    self.send_json_response(
                        create_error_response("Invalid JSON in request body", "INVALID_JSON"),
                        400
                    )
                    return
            
            # TODO: Implement PUT operations for updating resources
            self.send_json_response(create_success_response(
                message="PUT request received"
            ))
            
        except Exception as e:
            logger.error(f"Error handling PUT request: {e}\n{traceback.format_exc()}")
            self.send_json_response(
                create_error_response(f"Internal server error: {str(e)}", "INTERNAL_ERROR"),
                500
            )
    
    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        headers = self.get_headers_dict()
        
        # Extract current user from token if present
        token = get_auth_token(headers)
        current_user = None
        if token:
            current_user = verify_firebase_token(token)
        
        if not current_user:
            self.send_json_response(
                create_error_response("Authentication required", "UNAUTHORIZED"),
                401
            )
            return
        
        try:
            # TODO: Implement DELETE operations for removing resources
            self.send_json_response(create_success_response(
                message="DELETE request received"
            ))
            
        except Exception as e:
            logger.error(f"Error handling DELETE request: {e}\n{traceback.format_exc()}")
            self.send_json_response(
                create_error_response(f"Internal server error: {str(e)}", "INTERNAL_ERROR"),
                500
            )
    
    def log_message(self, format, *args):
        """Custom log format - suppress SSL/TLS errors"""
        message = format % args
        # Only log valid HTTP requests, ignore SSL/TLS handshake attempts
        if "Bad request" not in message and "code 400" not in message:
            logger.info(f"{self.address_string()} - {message}")

def run_server(port=8000):
    """Run the HTTP server"""
    logger.info("=" * 60)
    logger.info("🚀 KYNORA E-COMMERCE BACKEND SERVER")
    logger.info("=" * 60)
    logger.info(f"📡 Server URL: http://localhost:{port}")
    logger.info(f"🔥 Firebase: {'✅ Connected' if firebase_initialized else '⚠️ Not connected (using mock data)'}")
    logger.info(f"🗄️ Database: {'✅ Connected' if db else '⚠️ Not connected (using sample data)'}")
    logger.info(f"🔑 Authentication: {'✅ Firebase Auth enabled' if firebase_initialized else '⚠️ Mock authentication'}")
    logger.info("=" * 60)
    logger.info("📋 Available endpoints:")
    logger.info("  Public endpoints (no auth required):")
    logger.info("    GET  /products          - List all products")
    logger.info("    GET  /products/featured - Get featured products")
    logger.info("    GET  /products/popular  - Get popular products")
    logger.info("    GET  /products/search   - Search products")
    logger.info("    GET  /products/{id}     - Get single product")
    logger.info("    POST /products/{id}/view - Increment view count")
    logger.info("    GET  /categories        - List categories")
    logger.info("  Protected endpoints (auth required):")
    logger.info("    POST /products          - Create product (admin only)")
    logger.info("    GET  /auth/me           - Get current user")
    logger.info("    GET  /users/me          - Get user profile")
    logger.info("    GET  /cart              - Get cart items")
    logger.info("    GET  /orders/my-orders  - Get user orders")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop the server")
    logger.info("")
    
    server_address = ('', port)
    httpd = HTTPServer(server_address, APIHandler)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        httpd.shutdown()

if __name__ == "__main__":
    run_server(8000)
