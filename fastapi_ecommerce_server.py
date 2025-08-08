"""
FastAPI E-commerce Server
Converts FirestoreEcommerceDB class methods into RESTful API endpoints

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
import os
import dotenv
dotenv.load_dotenv()  # Load environment variables from .env file
# Import your existing Firestore class
from firestore_ecommerce_db import FirestoreEcommerceDB
import firebase_admin
from firebase_admin import credentials, auth, firestore
FIRESTORE_PROJECT_ID=os.getenv("FIRESTORE_PROJECT_ID")  # Ensure this is set in your environment
GOOGLE_APPLICATION_CREDENTIALS=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # Ensure this is set in your environment

# Initialize Firebase Admin SDK
try:
    # Check if Firebase is already initialized
    firebase_admin.get_app()
except ValueError:
    # Initialize Firebase if not already done
    cred = credentials.Certificate(GOOGLE_APPLICATION_CREDENTIALS)
    firebase_admin.initialize_app(cred, {
        'projectId': FIRESTORE_PROJECT_ID
    })

# Get Firestore client
firestore_client = firestore.client()



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce API",
    description="RESTful API for Firestore-based e-commerce platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database instance
def get_db() -> FirestoreEcommerceDB:
    """Dependency to create/reuse Firestore database instance"""
    project_id = os.getenv("FIRESTORE_PROJECT_ID")  # Set this in your environment
    return FirestoreEcommerceDB(project_id=project_id)

# TODO: Add authentication dependency

async def get_current_user(authorization: str = Header(None)):
    """
    Firebase Authentication dependency
    Verifies Firebase ID token and retrieves user data from Firestore
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401, 
            detail="Invalid authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.split(" ")[1]
    
    try:
        # Verify the Firebase ID token
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        
        # Get user data from Firestore
        user_doc = firestore_client.collection('users').document(uid).get()
        
        if not user_doc.exists:
            # If user doesn't exist in Firestore, create a basic profile
            user_data = {
                'uid': uid,
                'email': decoded_token.get('email', ''),
                'displayName': decoded_token.get('name', ''),
                'photoURL': decoded_token.get('picture', ''),
                'role': 'buyer',  # Default role
                'phone': decoded_token.get('phone_number', ''),
                'address': {},
                'preferences': {
                    'currency': 'INR',
                    'language': 'en',
                    'notifications': {
                        'email': True,
                        'sms': True,
                        'push': True
                    }
                },
                'createdAt': datetime.now(),
                'updatedAt': datetime.now(),
                'isActive': True,
                'lastLoginAt': datetime.now()
            }
            
            # Create user document in Firestore
            firestore_client.collection('users').document(uid).set(user_data)
            logger.info(f"Created new user profile for UID: {uid}")
        else:
            user_data = user_doc.to_dict()
            
            # Update last login time
            firestore_client.collection('users').document(uid).update({
                'lastLoginAt': datetime.now()
            })
        
        # Check if user is active
        if not user_data.get('isActive', True):
            raise HTTPException(
                status_code=403, 
                detail="User account is deactivated"
            )
        
        # Return user info in the format expected by the API
        return {
            "user_id": uid,
            "email": user_data.get('email', ''),
            "name": user_data.get('displayName', ''),
            "role": user_data.get('role', 'buyer'),
            "phone": user_data.get('phone', ''),
            "address": user_data.get('address', {}),
            "preferences": user_data.get('preferences', {}),
            "photo_url": user_data.get('photoURL', ''),
            "is_active": user_data.get('isActive', True),
            "created_at": user_data.get('createdAt'),
            "last_login_at": user_data.get('lastLoginAt')
        }
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=401, 
            detail="Invalid Firebase ID token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=401, 
            detail="Firebase ID token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during authentication"
        )

def require_admin():
    """Dependency to require admin role"""
    user = get_current_user()
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# ==================== PYDANTIC MODELS ====================

class UserCreate(BaseModel):
    email: str
    name: str
    role: str = "customer"
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, Any]] = None
    preferences: Optional[Dict[str, Any]] = None

class ProductCreate(BaseModel):
    title: str
    description: str
    price: float
    category_id: str
    subcategory_id: Optional[str] = None
    seller_id: str
    images: List[str] = []
    specifications: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    inventory_quantity: int = 0
    sku: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    is_featured: bool = False

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    subcategory_id: Optional[str] = None
    images: Optional[List[str]] = None
    specifications: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    inventory_quantity: Optional[int] = None
    sku: Optional[str] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    is_featured: Optional[bool] = None
    status: Optional[str] = None

class OrderCreate(BaseModel):
    customer_id: str
    seller_id: str
    items: List[Dict[str, Any]]
    total_amount: float
    currency: str = "USD"
    shipping_address: Dict[str, Any]
    billing_address: Optional[Dict[str, Any]] = None
    payment_method: Optional[str] = None
    shipping_method: Optional[str] = None
    notes: Optional[str] = None

class OrderStatusUpdate(BaseModel):
    status: str
    fulfillment_details: Optional[Dict[str, Any]] = None

class OrderCancel(BaseModel):
    reason: str
    refund_amount: Optional[float] = None

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: int = 0
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[str] = None
    image_url: Optional[str] = None
    sort_order: Optional[int] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None

class InventoryCreate(BaseModel):
    product_id: str
    warehouse_id: str
    available_stock: int
    reserved_stock: int = 0
    low_stock_threshold: int = 10
    cost_per_unit: Optional[float] = None

class InventoryUpdate(BaseModel):
    quantity_change: int
    movement_type: str  # 'stock_in', 'stock_out', 'adjustment', 'transfer'
    notes: Optional[str] = None

class WarehouseCreate(BaseModel):
    name: str
    address: Dict[str, Any]
    contact_info: Dict[str, Any]
    capacity: Optional[int] = None
    manager_id: Optional[str] = None

class CartItemAdd(BaseModel):
    product_id: str
    variant_id: Optional[str] = None
    quantity: int = 1
    price: float
    attributes: Optional[Dict[str, Any]] = None

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = None
    variant_id: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class ReviewCreate(BaseModel):
    product_id: str
    user_id: str
    order_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = None
    content: str
    images: List[str] = []
    verified_purchase: bool = False

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5)
    title: Optional[str] = None
    content: Optional[str] = None
    images: Optional[List[str]] = None

class ReviewModerate(BaseModel):
    action: str  # 'approved' or 'rejected'
    notes: Optional[str] = None

class NotificationCreate(BaseModel):
    user_id: str
    type: str  # 'order_update', 'product_alert', 'promotion', etc.
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    channel: str = "app"  # 'app', 'email', 'sms'

class SupplierCreate(BaseModel):
    name: str
    contact_info: Dict[str, Any]
    address: Dict[str, Any]
    payment_terms: Optional[str] = None
    lead_time_days: Optional[int] = None
    minimum_order_quantity: Optional[int] = None

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.get("/auth/me", response_model=Dict[str, Any], summary="Get current user profile")
async def get_current_user_profile(
    current_user = Depends(get_current_user)
):
    """Get the current authenticated user's profile"""
    return {
        "success": True,
        "data": current_user,
        "message": "User profile retrieved successfully"
    }

@app.post("/auth/test", response_model=Dict[str, Any], summary="Test authentication")
async def test_authentication(
    current_user = Depends(get_current_user)
):
    """Test endpoint to verify authentication is working"""
    return {
        "success": True,
        "message": "Authentication successful",
        "user": {
            "user_id": current_user["user_id"],
            "email": current_user["email"],
            "role": current_user["role"]
        }
    }

# ==================== USER ENDPOINTS ====================

@app.post("/users", response_model=Dict[str, Any], summary="Create user profile")
async def create_user(
    user_data: UserCreate,
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Create a new user profile"""
    # TODO: Add authentication check - users should only create their own profile
    result = db.create_user_profile(user_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}", response_model=Dict[str, Any], summary="Get user profile")
async def get_user(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get user profile by ID"""
    # TODO: Add authorization - users can only access their own profile unless admin
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_profile(user_id)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.put("/users/{user_id}", response_model=Dict[str, Any], summary="Update user profile")
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update user profile"""
    # TODO: Add authorization - users can only update their own profile
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.update_user_profile(user_id, user_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users", response_model=Dict[str, Any], summary="Get users by role")
async def get_users_by_role(
    role: str = Query(..., description="User role to filter by"),
    limit: int = Query(50, description="Number of users to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Get users by role (admin only)"""
    result = db.get_users_by_role(role, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/users/{user_id}/deactivate", response_model=Dict[str, Any], summary="Deactivate user")
async def deactivate_user(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Deactivate a user (admin only)"""
    result = db.deactivate_user(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== PRODUCT ENDPOINTS ====================

@app.post("/products", response_model=Dict[str, Any], summary="Add new product")
async def add_product(
    product_data: ProductCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a new product"""
    # TODO: Add authorization - only sellers and admins can add products
    if current_user['role'] not in ['seller', 'admin']:
        raise HTTPException(status_code=403, detail="Seller or admin access required")
    
    result = db.add_product(product_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/{product_id}", response_model=Dict[str, Any], summary="Get product by ID")
async def get_product(
    product_id: str = Path(..., description="Product ID"),
    increment_view: bool = Query(True, description="Whether to increment view count"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get product details by ID"""
    result = db.get_product(product_id, increment_view)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.put("/products/{product_id}", response_model=Dict[str, Any], summary="Update product")
async def update_product(
    product_id: str = Path(..., description="Product ID"),
    product_data: ProductUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update product details"""
    # TODO: Add authorization - only product owner or admin
    result = db.update_product(product_id, product_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products", response_model=Dict[str, Any], summary="Get products with filters")
async def get_products(
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    subcategory_id: Optional[str] = Query(None, description="Filter by subcategory ID"),
    seller_id: Optional[str] = Query(None, description="Filter by seller ID"),
    min_price: Optional[float] = Query(None, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, description="Maximum price filter"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    limit: int = Query(20, description="Number of products to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get products with optional filters"""
    filters = {}
    if category_id:
        filters['category_id'] = category_id
    if subcategory_id:
        filters['subcategory_id'] = subcategory_id
    if seller_id:
        filters['seller_id'] = seller_id
    if min_price is not None:
        filters['min_price'] = min_price
    if max_price is not None:
        filters['max_price'] = max_price
    if tags:
        filters['tags'] = [tag.strip() for tag in tags.split(',')]
    
    result = db.get_products_with_filters(filters, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/active", response_model=Dict[str, Any], summary="Get active products")
async def get_active_products(
    limit: int = Query(20, description="Number of products to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get all active products"""
    result = db.get_active_products(limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/featured", response_model=Dict[str, Any], summary="Get featured products")
async def get_featured_products(
    limit: int = Query(10, description="Number of featured products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get featured products"""
    result = db.get_featured_products(limit)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/search", response_model=Dict[str, Any], summary="Search products")
async def search_products(
    q: str = Query(..., description="Search keywords"),
    limit: int = Query(20, description="Number of products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Search products by keywords"""
    result = db.search_products(q, limit)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/popular", response_model=Dict[str, Any], summary="Get popular products")
async def get_popular_products(
    metric: str = Query("sales", description="Metric to sort by (sales, views)"),
    limit: int = Query(10, description="Number of products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get popular products by sales or views"""
    result = db.get_popular_products(limit, metric)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/products/{product_id}/archive", response_model=Dict[str, Any], summary="Archive product")
async def archive_product(
    product_id: str = Path(..., description="Product ID"),
    status: str = Query("archived", description="New status for the product"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Archive or deactivate a product"""
    # TODO: Add authorization - only product owner or admin
    result = db.archive_product(product_id, status)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/products/batch", response_model=Dict[str, Any], summary="Batch update products")
async def batch_update_products(
    updates: List[Dict[str, Any]] = Body(..., description="List of product updates"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Batch update products (admin or seller only)"""
    # TODO: Add authorization check
    result = db.batch_update_products(updates)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== ORDER ENDPOINTS ====================

@app.post("/orders", response_model=Dict[str, Any], summary="Create new order")
async def create_order(
    order_data: OrderCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new order"""
    # TODO: Add authorization - authenticated users only
    result = db.create_order(order_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/orders/{order_id}", response_model=Dict[str, Any], summary="Get order by ID")
async def get_order(
    order_id: str = Path(..., description="Order ID"),
    include_items: bool = Query(True, description="Include order items"),
    include_timeline: bool = Query(False, description="Include order timeline"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get order details by ID"""
    # TODO: Add authorization - customer can access own orders, seller can access their orders
    result = db.get_order(order_id, include_items, include_timeline)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.get("/users/{user_id}/orders", response_model=Dict[str, Any], summary="Get user orders")
async def get_user_orders(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, description="Number of orders to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all orders for a user"""
    # TODO: Add authorization - users can only access their own orders
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_orders(user_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/sellers/{seller_id}/orders", response_model=Dict[str, Any], summary="Get seller orders")
async def get_seller_orders(
    seller_id: str = Path(..., description="Seller ID"),
    limit: int = Query(20, description="Number of orders to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all orders for a seller"""
    # TODO: Add authorization - sellers can only access their own orders
    result = db.get_seller_orders(seller_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/orders/{order_id}/status", response_model=Dict[str, Any], summary="Update order status")
async def update_order_status(
    order_id: str = Path(..., description="Order ID"),
    status_data: OrderStatusUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update order status"""
    # TODO: Add authorization - seller or admin only
    result = db.update_order_status(
        order_id, 
        status_data.status, 
        status_data.fulfillment_details
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/orders/{order_id}/cancel", response_model=Dict[str, Any], summary="Cancel order")
async def cancel_order(
    order_id: str = Path(..., description="Order ID"),
    cancel_data: OrderCancel = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancel an order"""
    # TODO: Add authorization - customer can cancel pending orders, admin can cancel any
    result = db.cancel_order(order_id, cancel_data.reason, cancel_data.refund_amount)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.post("/orders/{order_id}/timeline", response_model=Dict[str, Any], summary="Add timeline event")
async def add_order_timeline_event(
    order_id: str = Path(..., description="Order ID"),
    event: str = Body(..., description="Event name"),
    details: str = Body(..., description="Event details"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add a timeline event to an order"""
    # TODO: Add authorization - seller or admin only
    result = db.add_order_timeline_event(order_id, event, details, current_user['user_id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== CATEGORY ENDPOINTS ====================

@app.get("/categories", response_model=Dict[str, Any], summary="List categories")
async def list_categories(
    parent_id: Optional[str] = Query(None, description="Parent category ID for subcategories"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """List all categories or subcategories"""
    result = db.list_categories(parent_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.post("/categories", response_model=Dict[str, Any], summary="Add category")
async def add_category(
    category_data: CategoryCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Add a new category (admin only)"""
    result = db.add_category(category_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/categories/{category_id}", response_model=Dict[str, Any], summary="Update category")
async def update_category(
    category_id: str = Path(..., description="Category ID"),
    category_data: CategoryUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Update a category (admin only)"""
    result = db.update_category(category_id, category_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/categories/{category_id}/archive", response_model=Dict[str, Any], summary="Archive category")
async def archive_category(
    category_id: str = Path(..., description="Category ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Archive a category (admin only)"""
    result = db.archive_category(category_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== INVENTORY ENDPOINTS ====================

@app.post("/inventory", response_model=Dict[str, Any], summary="Add inventory record")
async def add_inventory_record(
    inventory_data: InventoryCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add new inventory record"""
    # TODO: Add authorization - seller or admin only
    result = db.add_inventory_record(inventory_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/inventory/{product_id}/{warehouse_id}", response_model=Dict[str, Any], summary="Update inventory")
async def update_inventory_quantities(
    product_id: str = Path(..., description="Product ID"),
    warehouse_id: str = Path(..., description="Warehouse ID"),
    inventory_update: InventoryUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update inventory quantities"""
    # TODO: Add authorization - seller or admin only
    result = db.update_inventory_quantities(
        product_id,
        warehouse_id,
        inventory_update.quantity_change,
        inventory_update.movement_type,
        inventory_update.notes
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/{product_id}/inventory", response_model=Dict[str, Any], summary="Get product inventory")
async def get_product_inventory(
    product_id: str = Path(..., description="Product ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get inventory for a product across all warehouses"""
    # TODO: Add authorization - seller can view own products, admin can view all
    result = db.get_product_inventory(product_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/inventory/low-stock", response_model=Dict[str, Any], summary="Get low stock items")
async def get_low_stock_items(
    limit: int = Query(50, description="Number of items to return"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get low stock items"""
    # TODO: Add authorization - seller can view own products, admin can view all
    result = db.get_low_stock_items(limit)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/warehouses/{warehouse_id}/inventory", response_model=Dict[str, Any], summary="Get warehouse inventory")
async def get_warehouse_inventory(
    warehouse_id: str = Path(..., description="Warehouse ID"),
    limit: int = Query(50, description="Number of items to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get inventory for a specific warehouse"""
    # TODO: Add authorization - warehouse staff or admin only
    result = db.get_warehouse_inventory(warehouse_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== WAREHOUSE ENDPOINTS ====================

@app.post("/warehouses", response_model=Dict[str, Any], summary="Create warehouse")
async def create_warehouse(
    warehouse_data: WarehouseCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Create a new warehouse (admin only)"""
    result = db.create_warehouse(warehouse_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/warehouses", response_model=Dict[str, Any], summary="List warehouses")
async def list_warehouses(
    active_only: bool = Query(True, description="Return only active warehouses"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all warehouses"""
    # TODO: Add authorization - admin or warehouse staff
    result = db.list_warehouses(active_only)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/warehouses/{warehouse_id}", response_model=Dict[str, Any], summary="Get warehouse details")
async def get_warehouse_details(
    warehouse_id: str = Path(..., description="Warehouse ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get warehouse details by ID"""
    # TODO: Add authorization - admin or warehouse staff
    result = db.get_warehouse_details(warehouse_id)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.put("/warehouses/{warehouse_id}", response_model=Dict[str, Any], summary="Update warehouse")
async def update_warehouse_details(
    warehouse_id: str = Path(..., description="Warehouse ID"),
    warehouse_data: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Update warehouse details (admin only)"""
    result = db.update_warehouse_details(warehouse_id, warehouse_data)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== CART ENDPOINTS ====================

@app.post("/users/{user_id}/cart/initialize", response_model=Dict[str, Any], summary="Initialize cart")
async def initialize_cart(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Initialize a cart for a user"""
    # TODO: Add authorization - users can only initialize their own cart
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.initialize_cart(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.post("/users/{user_id}/cart/items", response_model=Dict[str, Any], summary="Add item to cart")
async def add_item_to_cart(
    user_id: str = Path(..., description="User ID"),
    item_data: CartItemAdd = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add an item to cart"""
    # TODO: Add authorization - users can only modify their own cart
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.add_item_to_cart(user_id, item_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.delete("/users/{user_id}/cart/items/{product_id}", response_model=Dict[str, Any], summary="Remove item from cart")
async def remove_item_from_cart(
    user_id: str = Path(..., description="User ID"),
    product_id: str = Path(..., description="Product ID"),
    variant_id: Optional[str] = Query(None, description="Variant ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove an item from cart"""
    # TODO: Add authorization - users can only modify their own cart
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.remove_item_from_cart(user_id, product_id, variant_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/users/{user_id}/cart/items/{product_id}", response_model=Dict[str, Any], summary="Update cart item")
async def update_cart_item(
    user_id: str = Path(..., description="User ID"),
    product_id: str = Path(..., description="Product ID"),
    update_data: CartItemUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update quantity or variant of a cart item"""
    # TODO: Add authorization - users can only modify their own cart
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.update_cart_item(user_id, product_id, update_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/cart", response_model=Dict[str, Any], summary="Get user cart")
async def get_user_cart(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get cart for a user"""
    # TODO: Add authorization - users can only access their own cart
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_cart(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.delete("/users/{user_id}/cart", response_model=Dict[str, Any], summary="Clear cart")
async def clear_cart(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Clear/empty cart"""
    # TODO: Add authorization - users can only clear their own cart
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.clear_cart(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== REVIEW ENDPOINTS ====================

@app.post("/reviews", response_model=Dict[str, Any], summary="Submit review")
async def submit_review(
    review_data: ReviewCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Submit a review for a product"""
    # TODO: Add authorization - authenticated users only, must have purchased the product
    result = db.submit_review(review_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/{product_id}/reviews", response_model=Dict[str, Any], summary="Get product reviews")
async def get_product_reviews(
    product_id: str = Path(..., description="Product ID"),
    status: str = Query("approved", description="Review status filter"),
    limit: int = Query(20, description="Number of reviews to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get reviews for a product"""
    result = db.get_product_reviews(product_id, status, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/reviews", response_model=Dict[str, Any], summary="Get user reviews")
async def get_user_reviews(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, description="Number of reviews to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get reviews by user"""
    # TODO: Add authorization - users can only access their own reviews
    if current_user['user_id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_reviews(user_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/reviews/{review_id}", response_model=Dict[str, Any], summary="Update review")
async def update_review(
    review_id: str = Path(..., description="Review ID"),
    review_data: ReviewUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a review"""
    # TODO: Add authorization - users can only update their own reviews within time limit
    result = db.update_review(review_id, review_data.dict(exclude_unset=True), current_user['user_id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/reviews/{review_id}/moderate", response_model=Dict[str, Any], summary="Moderate review")
async def moderate_review(
    review_id: str = Path(..., description="Review ID"),
    moderation_data: ReviewModerate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Moderate (approve/reject) a review (admin only)"""
    result = db.moderate_review(
        review_id, 
        moderation_data.action, 
        admin_user['user_id'], 
        moderation_data.notes
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== NOTIFICATION ENDPOINTS ====================

@app.post("/notifications", response_model=Dict[str, Any], summary="Create notification")
async def create_notification(
    notification_data: NotificationCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create/send a notification to a user"""
    # TODO: Add authorization - system or admin only
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = db.create_notification(notification_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/notifications", response_model=Dict[str, Any], summary="Get user notifications")
async def get_user_notifications(
    user_id: str = Path(..., description="User ID"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(20, description="Number of notifications to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get notifications for a user"""
    # TODO: Add authorization - users can only access their own notifications
    if current_user['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_notifications(user_id, unread_only, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/notifications/{notification_id}/read", response_model=Dict[str, Any], summary="Mark notification as read")
async def mark_notification_read(
    notification_id: str = Path(..., description="Notification ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Mark notification as read"""
    # TODO: Add authorization - users can only mark their own notifications as read
    result = db.mark_notification_read(notification_id, current_user['user_id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== SUPPLIER ENDPOINTS ====================

@app.post("/suppliers", response_model=Dict[str, Any], summary="Add supplier")
async def add_supplier(
    supplier_data: SupplierCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Add a new supplier (admin only)"""
    result = db.add_supplier(supplier_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/suppliers/{supplier_id}", response_model=Dict[str, Any], summary="Update supplier")
async def update_supplier_info(
    supplier_id: str = Path(..., description="Supplier ID"),
    supplier_data: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Update supplier info (admin only)"""
    result = db.update_supplier_info(supplier_id, supplier_data)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/suppliers", response_model=Dict[str, Any], summary="List suppliers")
async def list_suppliers(
    active_only: bool = Query(True, description="Return only active suppliers"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List all suppliers"""
    # TODO: Add authorization - admin or authorized personnel only
    if current_user['role'] not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Admin or manager access required")
    
    result = db.list_suppliers(active_only)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/suppliers/{supplier_id}", response_model=Dict[str, Any], summary="Get supplier by ID")
async def get_supplier_by_id(
    supplier_id: str = Path(..., description="Supplier ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get supplier by ID"""
    # TODO: Add authorization - admin or authorized personnel only
    if current_user['role'] not in ['admin', 'manager']:
        raise HTTPException(status_code=403, detail="Admin or manager access required")
    
    result = db.get_supplier_by_id(supplier_id)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

# ==================== DASHBOARD & ANALYTICS ENDPOINTS ====================

@app.get("/dashboard/stats", response_model=Dict[str, Any], summary="Get dashboard stats")
async def get_dashboard_stats(
    seller_id: Optional[str] = Query(None, description="Seller ID for seller-specific stats"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get dashboard statistics"""
    # TODO: Add authorization - admin can see all stats, sellers can see only their stats
    if seller_id and current_user['role'] not in ['admin'] and current_user['user_id'] != seller_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_dashboard_stats(seller_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/sellers/{seller_id}/sales-stats", response_model=Dict[str, Any], summary="Get sales stats")
async def get_sales_stats(
    seller_id: str = Path(..., description="Seller ID"),
    start_date: datetime = Query(..., description="Start date for stats"),
    end_date: datetime = Query(..., description="End date for stats"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get sales statistics for a seller"""
    # TODO: Add authorization - sellers can only see their own stats, admin can see any seller's stats
    if current_user['role'] != 'admin' and current_user['user_id'] != seller_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_sales_stats(seller_id, start_date, end_date)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/analytics/low-stock-alerts", response_model=Dict[str, Any], summary="Get low stock alerts")
async def get_low_stock_alerts(
    limit: int = Query(20, description="Number of alerts to return"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get real-time low stock alerts"""
    # TODO: Add authorization - admin or warehouse staff only
    if current_user['role'] not in ['admin', 'warehouse_staff']:
        raise HTTPException(status_code=403, detail="Admin or warehouse staff access required")
    
    result = db.get_low_stock_alerts(limit)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== UTILITY ENDPOINTS ====================

@app.post("/batch-operations", response_model=Dict[str, Any], summary="Batch operations")
async def batch_operation(
    operations: List[Dict[str, Any]] = Body(..., description="List of operations to perform"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Perform multiple operations in a single batch (admin only)"""
    result = db.batch_operation(operations)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/health", response_model=Dict[str, Any], summary="Health check")
async def health_check(db: FirestoreEcommerceDB = Depends(get_db)):
    """Database health check"""
    result = db.health_check()
    if not result['success']:
        raise HTTPException(status_code=503, detail=result['error'])
    return result

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("FastAPI E-commerce server starting up...")
    
    # Test database connection
    try:
        db = get_db()
        health_result = db.health_check()
        if health_result['success']:
            logger.info("Database connection successful")
        else:
            logger.error(f"Database connection failed: {health_result['error']}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

"""
==================== RUNNING THE SERVER ====================

1. Install dependencies:
   pip install fastapi uvicorn python-multipart

2. Set environment variables:
   export FIRESTORE_PROJECT_ID=your-project-id
   export GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

3. Run the server:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

4. Access the API:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc
   - Health check: http://localhost:8000/health

==================== EXAMPLE API CALLS ====================

# Get all products
GET /products?limit=20&category_id=electronics

# Create a new user
POST /users
{
    "email": "user@example.com",
    "name": "John Doe",
    "role": "customer"
}

# Add item to cart
POST /users/user123/cart/items
{
    "product_id": "prod123",
    "quantity": 2,
    "price": 29.99
}

# Create an order
POST /orders
{
    "customer_id": "user123",
    "seller_id": "seller456",
    "items": [
        {
            "product_id": "prod123",
            "quantity": 2,
            "price": 29.99
        }
    ],
    "total_amount": 59.98,
    "shipping_address": {
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zip": "12345"
    }
}

# Search products
GET /products/search?q=laptop&limit=10

# Get user orders
GET /users/user123/orders?limit=20

# Update order status
PATCH /orders/order123/status
{
    "status": "shipped",
    "fulfillment_details": {
        "tracking_number": "1234567890",
        "carrier": "UPS"
    }
}

==================== AUTHENTICATION SETUP ====================

To implement real authentication, replace the mock `get_current_user()` function with:

1. Firebase Auth:
   - Install: pip install firebase-admin
   - Verify Firebase ID tokens
   - Extract user info from token

2. JWT Tokens:
   - Install: pip install python-jose[cryptography] passlib[bcrypt]
   - Create login endpoint
   - Verify JWT tokens in dependency

3. OAuth2:
   - Install: pip install python-multipart
   - Use FastAPI's OAuth2PasswordBearer
   - Implement token verification

Example Firebase Auth implementation:
```python
import firebase_admin
from firebase_admin import auth, credentials

# Initialize Firebase
cred = credentials.Certificate("path/to/service-account.json")
firebase_admin.initialize_app(cred)

async def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(token)
        return {
            "user_id": decoded_token["uid"],
            "email": decoded_token["email"],
            "role": decoded_token.get("role", "customer")
        }
    except Exception as e:
        raise HTTPException(401, "Invalid token")
```

==================== NEXT.JS INTEGRATION ====================

In your Next.js app, you can call these APIs using:

```javascript
// api/client.js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const apiClient = {
  // Products
  getProducts: (params) => 
    fetch(`${API_BASE_URL}/products?${new URLSearchParams(params)}`),
  
  getProduct: (productId) => 
    fetch(`${API_BASE_URL}/products/${productId}`),
  
  // Cart
  addToCart: (userId, item) =>
    fetch(`${API_BASE_URL}/users/${userId}/cart/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item)
    }),
  
  // Orders
  createOrder: (orderData) =>
    fetch(`${API_BASE_URL}/orders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(orderData)
    }),
  
  getUserOrders: (userId) =>
    fetch(`${API_BASE_URL}/users/${userId}/orders`)
};
```
"""
    