"""
Simple FastAPI backend for testing
"""
import sys
import os

# Workaround for Python 3.14 compatibility issues
sys.modules['collections.abc'] = sys.modules.get('collections.abc', sys.modules['collections'])

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

# Basic configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
    
    # Initialize FastAPI app
    app = FastAPI(
        title="Kynora E-commerce API",
        description="Simple backend for e-commerce",
        version="1.0.0"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Sample data
    SAMPLE_PRODUCTS = [
        {
            "id": "prod_001",
            "product_id": "prod_001",
            "title": "Wireless Headphones",
            "description": "High-quality wireless headphones with noise cancellation",
            "price": 199.99,
            "category_id": "cat_electronics",
            "seller_id": "seller_001",
            "images": ["https://via.placeholder.com/300"],
            "inventory_quantity": 50,
            "tags": ["electronics", "audio", "wireless"],
            "is_featured": True,
            "status": "active",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "view_count": 120,
            "average_rating": 4.5,
            "review_count": 23
        },
        {
            "id": "prod_002",
            "product_id": "prod_002",
            "title": "Smart Watch",
            "description": "Feature-rich smartwatch with health tracking",
            "price": 299.99,
            "category_id": "cat_electronics",
            "seller_id": "seller_001",
            "images": ["https://via.placeholder.com/300"],
            "inventory_quantity": 30,
            "tags": ["electronics", "wearable", "fitness"],
            "is_featured": True,
            "status": "active",
            "created_at": "2024-01-02T00:00:00",
            "updated_at": "2024-01-02T00:00:00",
            "view_count": 85,
            "average_rating": 4.3,
            "review_count": 15
        },
        {
            "id": "prod_003",
            "product_id": "prod_003",
            "title": "Laptop Backpack",
            "description": "Durable laptop backpack with multiple compartments",
            "price": 79.99,
            "category_id": "cat_accessories",
            "seller_id": "seller_002",
            "images": ["https://via.placeholder.com/300"],
            "inventory_quantity": 100,
            "tags": ["accessories", "bags", "laptop"],
            "is_featured": False,
            "status": "active",
            "created_at": "2024-01-03T00:00:00",
            "updated_at": "2024-01-03T00:00:00",
            "view_count": 45,
            "average_rating": 4.7,
            "review_count": 8
        }
    ]
    
    SAMPLE_CATEGORIES = [
        {
            "id": "cat_electronics",
            "name": "Electronics",
            "description": "Electronic devices and gadgets",
            "parent_id": None,
            "is_active": True
        },
        {
            "id": "cat_accessories",
            "name": "Accessories",
            "description": "Various accessories",
            "parent_id": None,
            "is_active": True
        }
    ]
    
    # Health check
    @app.get("/")
    async def root():
        return {
            "success": True,
            "message": "Kynora E-commerce API",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Products endpoints
    @app.get("/products")
    async def list_products(
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100),
        category_id: Optional[str] = None
    ):
        products = SAMPLE_PRODUCTS
        if category_id:
            products = [p for p in products if p.get("category_id") == category_id]
        
        return {
            "success": True,
            "products": products,
            "page": page,
            "limit": limit,
            "total": len(products)
        }
    
    @app.get("/products/featured")
    async def get_featured_products(limit: int = Query(10, ge=1, le=50)):
        featured = [p for p in SAMPLE_PRODUCTS if p.get("is_featured")][:limit]
        return {
            "success": True,
            "products": featured
        }
    
    @app.get("/products/popular")
    async def get_popular_products(limit: int = Query(10, ge=1, le=50)):
        popular = sorted(SAMPLE_PRODUCTS, key=lambda x: x.get("view_count", 0), reverse=True)[:limit]
        return {
            "success": True,
            "products": popular
        }
    
    @app.get("/products/search")
    async def search_products(
        q: str = Query(..., min_length=1),
        page: int = Query(1, ge=1),
        limit: int = Query(20, ge=1, le=100)
    ):
        results = [
            p for p in SAMPLE_PRODUCTS 
            if q.lower() in p["title"].lower() or q.lower() in p["description"].lower()
        ]
        return {
            "success": True,
            "message": f"Found {len(results)} products",
            "products": results,
            "page": page,
            "limit": limit,
            "total": len(results)
        }
    
    @app.get("/products/{product_id}")
    async def get_product(product_id: str):
        product = next((p for p in SAMPLE_PRODUCTS if p["id"] == product_id), None)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return {
            "success": True,
            "data": product
        }
    
    @app.post("/products/{product_id}/view")
    async def increment_view_count(product_id: str):
        product = next((p for p in SAMPLE_PRODUCTS if p["id"] == product_id), None)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product["view_count"] = product.get("view_count", 0) + 1
        return {
            "success": True,
            "message": "View count updated",
            "data": {
                "product_id": product_id,
                "view_count": product["view_count"]
            }
        }
    
    @app.get("/products/{product_id}/reviews")
    async def get_product_reviews(product_id: str):
        # Sample reviews
        reviews = [
            {
                "id": "rev_001",
                "product_id": product_id,
                "user_id": "user_001",
                "user_name": "John Doe",
                "rating": 5,
                "title": "Excellent product",
                "content": "Really happy with this purchase. Great quality!",
                "created_at": "2024-01-10T00:00:00"
            }
        ]
        return {
            "success": True,
            "data": reviews
        }
    
    # Categories endpoints
    @app.get("/categories")
    async def list_categories():
        return {
            "success": True,
            "categories": SAMPLE_CATEGORIES
        }
    
    # Auth endpoints
    @app.get("/auth/me")
    async def get_current_user():
        return {
            "success": True,
            "data": {
                "id": "user_001",
                "email": "user@example.com",
                "name": "Test User",
                "role": "customer"
            }
        }
    
    # Cart endpoints
    @app.get("/cart")
    async def get_cart():
        return {
            "success": True,
            "cart": {
                "items": [],
                "total": 0
            }
        }
    
    @app.get("/cart/summary")
    async def get_cart_summary():
        return {
            "success": True,
            "data": {
                "items_count": 0,
                "subtotal": 0,
                "tax": 0,
                "total": 0
            }
        }
    
    # Orders endpoints
    @app.get("/orders/my-orders")
    async def get_my_orders():
        return {
            "success": True,
            "orders": []
        }
    
    # Users endpoints
    @app.get("/users/me")
    async def get_user_profile():
        return {
            "success": True,
            "user": {
                "user_id": "user_001",
                "displayName": "Test User",
                "email": "user@example.com",
                "role": "customer"
            }
        }
    
    # Reviews endpoints
    @app.get("/reviews/products/{product_id}")
    async def get_reviews_for_product(product_id: str):
        return {
            "success": True,
            "reviews": []
        }
    
    if __name__ == "__main__":
        logger.info("Starting Kynora Backend on http://localhost:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
except ImportError as e:
    print(f"Import error: {e}")
    print("Please install required packages:")
    print("pip install fastapi==0.95.2 uvicorn==0.24.0 pydantic==1.10.13")
    sys.exit(1)
