"""Product API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List
import logging
from datetime import datetime

from config.firebase import db
from models.product import (
    Product, ProductCreate, ProductUpdate, 
    ProductResponse, ProductListResponse, ProductFilter
)
from models.base import PaginationParams
from utils.auth import get_current_user, require_seller
from utils.helpers import Helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_featured: Optional[bool] = None,
    search: Optional[str] = None
):
    """List all active products with filters"""
    try:
        # Build query
        query = db.collection('products').where('status', '==', 'active')
        
        if category_id:
            query = query.where('category_id', '==', category_id)
        if is_featured is not None:
            query = query.where('is_featured', '==', is_featured)
        if min_price is not None:
            query = query.where('price', '>=', min_price)
        if max_price is not None:
            query = query.where('price', '<=', max_price)
        
        # Get total count
        all_docs = list(query.stream())
        total = len(all_docs)
        
        # Filter by search if provided
        if search:
            search_lower = search.lower()
            all_docs = [
                doc for doc in all_docs
                if search_lower in doc.to_dict().get('title', '').lower()
                or search_lower in doc.to_dict().get('description', '').lower()
            ]
            total = len(all_docs)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to Product objects
        products = []
        for doc in paginated_docs:
            product_data = doc.to_dict()
            product_data['product_id'] = doc.id
            products.append(Product(**product_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        return ProductListResponse(
            success=True,
            message="Products retrieved successfully",
            products=products,
            **pagination
        )
        
    except Exception as e:
        logger.error(f"Error listing products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve products"
        )


@router.get("/featured", response_model=ProductListResponse)
async def get_featured_products(limit: int = Query(10, ge=1, le=50)):
    """Get featured products"""
    try:
        query = db.collection('products')\
            .where('status', '==', 'active')\
            .where('is_featured', '==', True)\
            .limit(limit)
        
        products = []
        for doc in query.stream():
            product_data = doc.to_dict()
            product_data['product_id'] = doc.id
            products.append(Product(**product_data))
        
        return ProductListResponse(
            success=True,
            message="Featured products retrieved",
            products=products,
            page=1,
            limit=limit,
            total=len(products),
            pages=1,
            has_next=False,
            has_prev=False
        )
        
    except Exception as e:
        logger.error(f"Error getting featured products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve featured products"
        )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product details"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check if product is active
        if product_data.get('status') != 'active':
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not available"
            )
        
        product_data['product_id'] = product_doc.id
        product = Product(**product_data)
        
        # Increment view count
        db.collection('products').document(product_id).update({
            'view_count': product.view_count + 1
        })
        
        return ProductResponse(
            success=True,
            message="Product retrieved successfully",
            product=product
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve product"
        )


@router.post("", response_model=ProductResponse)
async def create_product(
    product_data: ProductCreate,
    current_user = Depends(require_seller)
):
    """Create new product (seller/admin only)"""
    try:
        # Generate product ID
        product_id = Helpers.generate_id("prod")
        
        # Create product
        product = Product(
            product_id=product_id,
            seller_id=current_user.user_id,
            **product_data.dict()
        )
        
        # Generate slug if not provided
        if not product.slug:
            product.slug = Helpers.generate_slug(product.title)
        
        # Save to Firestore
        db.collection('products').document(product_id).set(
            product.to_firestore()
        )
        
        # Update category product count
        if product.category_id:
            category_ref = db.collection('categories').document(product.category_id)
            category_doc = category_ref.get()
            if category_doc.exists:
                current_count = category_doc.to_dict().get('product_count', 0)
                category_ref.update({'product_count': current_count + 1})
        
        return ProductResponse(
            success=True,
            message="Product created successfully",
            product=product
        )
        
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product"
        )


@router.put("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user = Depends(require_seller)
):
    """Update product (seller/admin only)"""
    try:
        # Get existing product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership (unless admin)
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own products"
            )
        
        # Update fields
        update_data = product_update.dict(exclude_unset=True)
        update_data['updated_at'] = Helpers.filter_none_values(update_data)
        
        # Update in Firestore
        db.collection('products').document(product_id).update(update_data)
        
        # Get updated product
        updated_doc = db.collection('products').document(product_id).get()
        updated_data = updated_doc.to_dict()
        updated_data['product_id'] = product_id
        updated_product = Product(**updated_data)
        
        return ProductResponse(
            success=True,
            message="Product updated successfully",
            product=updated_product
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update product"
        )


@router.patch("/{product_id}/archive")
async def archive_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Archive product (soft delete)"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only archive your own products"
            )
        
        # Archive product
        db.collection('products').document(product_id).update({
            'status': 'archived',
            'deleted_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        # Update category product count
        if product_data.get('category_id'):
            category_ref = db.collection('categories').document(product_data['category_id'])
            category_doc = category_ref.get()
            if category_doc.exists:
                current_count = category_doc.to_dict().get('product_count', 0)
                category_ref.update({'product_count': max(0, current_count - 1)})
        
        return {
            "success": True,
            "message": "Product archived successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive product"
        )


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Delete product permanently"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own products"
            )
        
        # Delete product
        db.collection('products').document(product_id).delete()
        
        # Update category product count
        if product_data.get('category_id'):
            category_ref = db.collection('categories').document(product_data['category_id'])
            category_doc = category_ref.get()
            if category_doc.exists:
                current_count = category_doc.to_dict().get('product_count', 0)
                category_ref.update({'product_count': max(0, current_count - 1)})
        
        return {
            "success": True,
            "message": "Product deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product"
        )


@router.patch("/{product_id}/unarchive")
async def unarchive_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Restore archived product"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only restore your own products"
            )
        
        # Restore product
        db.collection('products').document(product_id).update({
            'status': 'active',
            'deleted_at': None,
            'updated_at': datetime.utcnow()
        })
        
        # Update category product count
        if product_data.get('category_id'):
            category_ref = db.collection('categories').document(product_data['category_id'])
            category_doc = category_ref.get()
            if category_doc.exists:
                current_count = category_doc.to_dict().get('product_count', 0)
                category_ref.update({'product_count': current_count + 1})
        
        return {
            "success": True,
            "message": "Product restored successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to restore product"
        )


@router.patch("/{product_id}/activate")
async def activate_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Activate product"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only activate your own products"
            )
        
        # Activate product
        db.collection('products').document(product_id).update({
            'status': 'active',
            'is_active': True,
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Product activated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate product"
        )


@router.patch("/{product_id}/deactivate")
async def deactivate_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Deactivate product"""
    try:
        # Get product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only deactivate your own products"
            )
        
        # Deactivate product
        db.collection('products').document(product_id).update({
            'status': 'inactive',
            'is_active': False,
            'updated_at': datetime.utcnow()
        })
        
        return {
            "success": True,
            "message": "Product deactivated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate product"
        )


@router.post("/{product_id}/duplicate")
async def duplicate_product(
    product_id: str,
    current_user = Depends(require_seller)
):
    """Duplicate a product"""
    try:
        # Get original product
        product_doc = db.collection('products').document(product_id).get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        product_data = product_doc.to_dict()
        
        # Check ownership
        if current_user.role != 'admin' and product_data.get('seller_id') != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only duplicate your own products"
            )
        
        # Create new product with updated details
        new_product_id = Helpers.generate_id("prod")
        new_product_data = product_data.copy()
        
        # Update fields for the duplicate
        new_product_data['product_id'] = new_product_id
        new_product_data['title'] = f"{product_data['title']} (Copy)"
        new_product_data['slug'] = Helpers.generate_slug(new_product_data['title'])
        new_product_data['sku'] = f"{product_data.get('sku', '')}_copy" if product_data.get('sku') else None
        new_product_data['status'] = 'draft'
        new_product_data['view_count'] = 0
        new_product_data['sales_count'] = 0
        new_product_data['created_at'] = datetime.utcnow()
        new_product_data['updated_at'] = datetime.utcnow()
        
        # Save duplicated product
        db.collection('products').document(new_product_id).set(new_product_data)
        
        return {
            "success": True,
            "message": "Product duplicated successfully",
            "product_id": new_product_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating product: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to duplicate product"
        )


@router.post("/{product_id}/view")
async def increment_view_count(product_id: str):
    """Increment product view count"""
    try:
        product_ref = db.collection('products').document(product_id)
        product_doc = product_ref.get()
        
        if not product_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        current_views = product_doc.to_dict().get('view_count', 0)
        new_views = current_views + 1
        product_ref.update({'view_count': new_views})
        
        return {
            "success": True,
            "message": "View count updated",
            "data": {
                "product_id": product_id,
                "view_count": new_views
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating view count: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update view count"
        )


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: str = Query("relevance", regex="^(relevance|price_asc|price_desc|newest|rating)$")
):
    """Search products by title, description, or tags"""
    try:
        # Build base query for active products
        query = db.collection('products').where('status', '==', 'active')
        
        # Apply filters
        if category_id:
            query = query.where('category_id', '==', category_id)
        if min_price is not None:
            query = query.where('price', '>=', min_price)
        if max_price is not None:
            query = query.where('price', '<=', max_price)
        
        # Get all matching documents
        all_docs = list(query.stream())
        
        # Search filter
        search_lower = q.lower()
        matching_docs = []
        
        for doc in all_docs:
            product_data = doc.to_dict()
            
            # Search in title, description, and tags
            title_match = search_lower in product_data.get('title', '').lower()
            desc_match = search_lower in product_data.get('description', '').lower()
            tag_match = any(search_lower in tag.lower() for tag in product_data.get('tags', []))
            
            if title_match or desc_match or tag_match:
                # Add relevance score for sorting
                relevance = 0
                if title_match:
                    relevance += 3  # Title matches are most relevant
                if tag_match:
                    relevance += 2  # Tag matches are second
                if desc_match:
                    relevance += 1  # Description matches are least relevant
                
                matching_docs.append((doc, relevance))
        
        # Sort results
        if sort_by == "relevance":
            matching_docs.sort(key=lambda x: x[1], reverse=True)
        elif sort_by == "price_asc":
            matching_docs.sort(key=lambda x: x[0].to_dict().get('price', 0))
        elif sort_by == "price_desc":
            matching_docs.sort(key=lambda x: x[0].to_dict().get('price', 0), reverse=True)
        elif sort_by == "newest":
            matching_docs.sort(key=lambda x: x[0].to_dict().get('created_at'), reverse=True)
        elif sort_by == "rating":
            matching_docs.sort(key=lambda x: x[0].to_dict().get('average_rating', 0), reverse=True)
        
        # Extract just the documents
        sorted_docs = [doc for doc, _ in matching_docs]
        
        total = len(sorted_docs)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = sorted_docs[start_idx:end_idx]
        
        # Convert to Product objects
        products = []
        for doc in paginated_docs:
            product_data = doc.to_dict()
            product_data['product_id'] = doc.id
            products.append(Product(**product_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        return ProductListResponse(
            success=True,
            message=f"Found {total} products matching '{q}'",
            products=products,
            **pagination
        )
        
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search products"
        )


@router.get("/active", response_model=ProductListResponse)
async def get_active_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
):
    """Get all active products"""
    try:
        # Build query for active products only
        query = db.collection('products').where('status', '==', 'active')
        
        if category_id:
            query = query.where('category_id', '==', category_id)
        if min_price is not None:
            query = query.where('price', '>=', min_price)
        if max_price is not None:
            query = query.where('price', '<=', max_price)
        
        # Get all documents
        all_docs = list(query.stream())
        total = len(all_docs)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to Product objects
        products = []
        for doc in paginated_docs:
            product_data = doc.to_dict()
            product_data['product_id'] = doc.id
            products.append(Product(**product_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        return ProductListResponse(
            success=True,
            message="Active products retrieved successfully",
            products=products,
            **pagination
        )
        
    except Exception as e:
        logger.error(f"Error getting active products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active products"
        )


@router.get("/popular", response_model=ProductListResponse)
async def get_popular_products(
    limit: int = Query(10, ge=1, le=50),
    days: int = Query(30, ge=1, le=365, description="Number of days to consider for popularity")
):
    """Get popular products based on views and sales"""
    try:
        # Get active products
        query = db.collection('products').where('status', '==', 'active')
        
        all_docs = list(query.stream())
        
        # Calculate popularity score
        products_with_score = []
        for doc in all_docs:
            product_data = doc.to_dict()
            
            # Simple popularity score based on views, sales, and rating
            view_count = product_data.get('view_count', 0)
            sales_count = product_data.get('sales_count', 0)
            rating = product_data.get('average_rating', 0)
            review_count = product_data.get('review_count', 0)
            
            # Calculate weighted score
            popularity_score = (
                view_count * 0.2 +  # Views have lowest weight
                sales_count * 5 +   # Sales have highest weight
                rating * review_count * 2  # Good reviews boost popularity
            )
            
            products_with_score.append((doc, popularity_score))
        
        # Sort by popularity score
        products_with_score.sort(key=lambda x: x[1], reverse=True)
        
        # Take top N products
        top_products = products_with_score[:limit]
        
        # Convert to Product objects
        products = []
        for doc, score in top_products:
            product_data = doc.to_dict()
            product_data['product_id'] = doc.id
            products.append(Product(**product_data))
        
        return ProductListResponse(
            success=True,
            message="Popular products retrieved",
            products=products,
            page=1,
            limit=limit,
            total=len(products),
            pages=1,
            has_next=False,
            has_prev=False
        )
        
    except Exception as e:
        logger.error(f"Error getting popular products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular products"
        )


@router.get("/{product_id}/reviews")
async def get_product_reviews(
    product_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    """Get reviews for a specific product"""
    try:
        # Get reviews from Firestore
        query = db.collection('reviews').where('product_id', '==', product_id)
        
        all_docs = list(query.stream())
        total = len(all_docs)
        
        # Apply pagination
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_docs = all_docs[start_idx:end_idx]
        
        # Convert to review objects
        reviews = []
        for doc in paginated_docs:
            review_data = doc.to_dict()
            review_data['id'] = doc.id
            
            # Get user info
            user_id = review_data.get('user_id')
            if user_id:
                user_doc = db.collection('users').document(user_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    review_data['user_name'] = user_data.get('displayName', 'Anonymous')
                    review_data['user_avatar'] = user_data.get('avatar')
            
            reviews.append(review_data)
        
        return {
            "success": True,
            "message": "Reviews retrieved successfully",
            "data": reviews,
            "page": page,
            "limit": limit,
            "total": total,
            "has_next": end_idx < total
        }
        
    except Exception as e:
        logger.error(f"Error getting product reviews: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reviews"
        )
