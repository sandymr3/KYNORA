"""
Product management endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, status
from typing import Optional, List
from datetime import datetime
from firebase_admin import firestore
import logging

from core.database import get_db
from core.dependencies import get_current_user, require_authenticated_user, require_admin
from core.utils import create_success_response, create_error_response, generate_id, generate_slug
from core.models import ProductCreate, ProductUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

# No mock data - using production Firestore only

@router.get("")
async def get_products(
    category_id: Optional[str] = Query(None),
    subcategory_id: Optional[str] = Query(None),
    seller_id: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    tags: Optional[List[str]] = Query(None),
    search: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="Search query"),
    sort_by: Optional[str] = Query("created_at", pattern="^(price|created_at|view_count|rating)$"),
    sort_order: Optional[str] = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    last_doc_id: Optional[str] = Query(None)
):
    """Get products with filters"""
    try:
        db = get_db()
        
        # Database is required - no fallback
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Query Firestore
        query = db.collection('products').where('status', '==', 'active').limit(limit)
        
        products = []
        for doc in query.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            
            # Apply additional filters that Firestore can't handle
            if min_price is not None and product.get('price', 0) < min_price:
                continue
            if max_price is not None and product.get('price', 0) > max_price:
                continue
            if tags and not any(tag in product.get('tags', []) for tag in tags):
                continue
            
            # Apply search filter
            search_query = q or search
            if search_query:
                search_lower = search_query.lower()
                if not (search_lower in product.get('title', '').lower() or
                        search_lower in product.get('description', '').lower()):
                    continue
            
            products.append(product)
        
        return create_success_response(
            data={
                'products': products,
                'total': len(products),
                'limit': limit,
                'offset': offset,
                'last_doc_id': products[-1]['id'] if products else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products"
        )

@router.get("/featured")
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50)
):
    """Get featured products"""
    try:
        db = get_db()
        
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Query Firestore for featured products
        query = db.collection('products').where('status', '==', 'active').limit(limit * 2)
        
        products = []
        for doc in query.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            
            # Filter for featured products
            if product.get('is_featured', False):
                products.append(product)
                if len(products) >= limit:
                    break
        
        return create_success_response(
            data={'products': products}
        )
        
    except Exception as e:
        logger.error(f"Error getting featured products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve featured products"
        )

@router.get("/popular")
async def get_popular_products(
    limit: int = Query(10, ge=1, le=50)
):
    """Get popular products sorted by view count"""
    try:
        db = get_db()
        
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Query Firestore for popular products
        query = db.collection('products').where('status', '==', 'active').limit(limit * 2)
        
        products = []
        for doc in query.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            products.append(product)
        
        # Sort by view count in Python
        products.sort(key=lambda x: x.get('view_count', 0), reverse=True)
        products = products[:limit]
        
        return create_success_response(
            data={'products': products}
        )
        
    except Exception as e:
        logger.error(f"Error getting popular products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular products"
        )

@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(20, ge=1, le=100)
):
    """Search products"""
    try:
        db = get_db()
        
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Note: For production, use a proper search service like Algolia or ElasticSearch
        # This is a simple implementation that searches all products
        
        products = []
        all_products = db.collection('products') \
                        .where('status', '==', 'active') \
                        .stream()
        
        search_lower = q.lower()
        for doc in all_products:
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            
            if (search_lower in product.get('title', '').lower() or
                search_lower in product.get('description', '').lower() or
                any(search_lower in tag.lower() for tag in product.get('tags', []))):
                products.append(product)
                
                if len(products) >= limit:
                    break
        
        return create_success_response(
            data={
                'products': products,
                'query': q,
                'count': len(products)
            },
            message=f"Found {len(products)} products"
        )
        
    except Exception as e:
        logger.error(f"Error searching products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )

@router.get("/active")
async def get_active_products(
    limit: int = Query(20, ge=1, le=100),
    last_doc_id: Optional[str] = Query(None)
):
    """Get active products"""
    try:
        db = get_db()
        
        if not db:
            active = [p for p in SAMPLE_PRODUCTS if p.get('status') == 'active'][:limit]
            return create_success_response(
                data={'products': active}
            )
        
        query = db.collection('products').where('status', '==', 'active')
        
        if last_doc_id:
            last_doc = db.collection('products').document(last_doc_id).get()
            if last_doc.exists:
                query = query.start_after(last_doc)
        
        query = query.limit(limit)
        
        products = []
        for doc in query.stream():
            product = doc.to_dict()
            product['id'] = doc.id
            product['product_id'] = doc.id
            products.append(product)
        
        return create_success_response(
            data={
                'products': products,
                'last_doc_id': products[-1]['id'] if products else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting active products: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active products"
        )

@router.get("/{product_id}")
async def get_product(product_id: str):
    """Get product by ID"""
    try:
        db = get_db()
        
        if not db:
            product = next((p for p in SAMPLE_PRODUCTS if p['id'] == product_id), None)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found"
                )
            return create_success_response(data=product)
        
        doc = db.collection('products').document(product_id).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product = doc.to_dict()
        product['id'] = doc.id
        product['product_id'] = doc.id
        
        return create_success_response(data=product)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product"
        )

@router.post("/{product_id}/view")
async def increment_product_view(product_id: str):
    """Increment product view count"""
    try:
        db = get_db()
        
        if not db:
            product = next((p for p in SAMPLE_PRODUCTS if p['id'] == product_id), None)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Product not found"
                )
            
            product['view_count'] = product.get('view_count', 0) + 1
            return create_success_response(
                data={
                    'product_id': product_id,
                    'view_count': product['view_count']
                },
                message="Product view count incremented"
            )
        
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Increment view count atomically
        doc_ref.update({
            'view_count': firestore.Increment(1),
            'last_viewed_at': datetime.utcnow()
        })
        
        # Get updated count
        updated_doc = doc_ref.get()
        new_count = updated_doc.to_dict().get('view_count', 0)
        
        logger.info(f"View count incremented for product: {product_id} -> {new_count}")
        
        return create_success_response(
            data={
                'product_id': product_id,
                'view_count': new_count
            },
            message="Product view count incremented"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error incrementing view count: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to increment view count"
        )

@router.post("")
async def create_product(
    product_data: ProductCreate,
    current_user: dict = Depends(require_admin)
):
    """Create new product (admin only)"""
    db = get_db()
    
    if not db:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not available"
        )
    
    try:
        product_id = generate_id("prod_")
        
        product_doc = product_data.dict()
        product_doc.update({
            'seller_id': product_data.seller_id or current_user['id'],
            'status': 'active',
            'view_count': 0,
            'average_rating': 0,
            'review_count': 0,
            'slug': generate_slug(product_data.title),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': current_user['id']
        })
        
        # Save to Firestore
        db.collection('products').document(product_id).set(product_doc)
        
        # Return the created product with ID
        created_product = product_doc.copy()
        created_product['id'] = product_id
        created_product['product_id'] = product_id
        
        logger.info(f"Product created: {product_id} by user: {current_user['id']}")
        
        return create_success_response(
            data=created_product,
            message="Product created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{product_id}")
async def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: dict = Depends(require_admin)
):
    """Update product (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        update_data = product_data.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()
        update_data['updated_by'] = current_user['id']
        
        doc_ref.update(update_data)
        
        logger.info(f"Product updated: {product_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Product updated successfully",
            data={'product_id': product_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: dict = Depends(require_admin)
):
    """Delete product (admin only)"""
    db = get_db()
    
    if not db:
        return create_error_response("Database not available", "DB_ERROR")
    
    try:
        doc_ref = db.collection('products').document(product_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Soft delete - just update status
        doc_ref.update({
            'status': 'deleted',
            'deleted_at': datetime.utcnow(),
            'deleted_by': current_user['id']
        })
        
        logger.info(f"Product deleted: {product_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Product deleted successfully",
            data={'product_id': product_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
