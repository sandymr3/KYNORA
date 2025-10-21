"""
Category management endpoints for KYNORA backend
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body, status
from typing import Optional, List
from datetime import datetime
from firebase_admin import firestore
import logging

from core.database import get_db
from core.dependencies import require_authenticated_user, require_admin
from core.utils import create_success_response, create_error_response, generate_id, generate_slug
from core.models import CategoryCreate, CategoryUpdate

router = APIRouter()
logger = logging.getLogger(__name__)

# Sample categories for development
SAMPLE_CATEGORIES = [
    {
        "id": "electronics",
        "name": "Electronics",
        "slug": "electronics",
        "description": "Electronic devices and gadgets",
        "parent_id": None,
        "image": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=300",
        "status": "active",
        "product_count": 3
    },
    {
        "id": "accessories",
        "name": "Accessories",
        "slug": "accessories",
        "description": "Computer and phone accessories",
        "parent_id": None,
        "image": "https://images.unsplash.com/photo-1484704849700-f032a568e944?w=300",
        "status": "active",
        "product_count": 2
    },
    {
        "id": "clothing",
        "name": "Clothing",
        "slug": "clothing",
        "description": "Men's and Women's clothing",
        "parent_id": None,
        "image": "https://images.unsplash.com/photo-1489987707025-afc232f7ea0f?w=300",
        "status": "active",
        "product_count": 0
    }
]

@router.get("")
async def get_categories(
    parent_id: Optional[str] = Query(None, description="Filter by parent category ID"),
    status: Optional[str] = Query("active", description="Filter by status"),
    include_count: bool = Query(True, description="Include product count")
):
    """Get all categories"""
    try:
        db = get_db()
        
        if not db:
            # Return sample categories in development mode
            categories = SAMPLE_CATEGORIES.copy()
            
            if parent_id is not None:
                categories = [c for c in categories if c.get('parent_id') == parent_id]
            
            if status:
                categories = [c for c in categories if c.get('status') == status]
            
            return create_success_response(
                data={'categories': categories},
                message=f"Retrieved {len(categories)} categories"
            )
        
        # Query Firestore
        query = db.collection('categories')
        
        if parent_id is not None:
            query = query.where('parent_id', '==', parent_id)
        
        if status:
            query = query.where('status', '==', status)
        
        query = query.order_by('name')
        
        categories = []
        for doc in query.stream():
            category = doc.to_dict()
            category['id'] = doc.id
            category['category_id'] = doc.id
            
            # Include product count if requested
            if include_count:
                product_count = db.collection('products') \
                    .where('category_id', '==', doc.id) \
                    .where('status', '==', 'active') \
                    .count().get()[0][0].value
                category['product_count'] = product_count
            
            categories.append(category)
        
        return create_success_response(
            data={'categories': categories},
            message=f"Retrieved {len(categories)} categories"
        )
        
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )

@router.get("/tree")
async def get_category_tree():
    """Get categories organized in tree structure"""
    try:
        db = get_db()
        
        if not db:
            # Build tree from sample categories
            categories = SAMPLE_CATEGORIES.copy()
            
            # Build tree structure
            tree = []
            category_map = {cat['id']: cat for cat in categories}
            
            for category in categories:
                category['children'] = []
                if category['parent_id'] is None:
                    tree.append(category)
                elif category['parent_id'] in category_map:
                    parent = category_map[category['parent_id']]
                    if 'children' not in parent:
                        parent['children'] = []
                    parent['children'].append(category)
            
            return create_success_response(
                data={'tree': tree}
            )
        
        # Get all categories from Firestore
        categories = []
        for doc in db.collection('categories').where('status', '==', 'active').stream():
            category = doc.to_dict()
            category['id'] = doc.id
            category['children'] = []
            categories.append(category)
        
        # Build tree structure
        tree = []
        category_map = {cat['id']: cat for cat in categories}
        
        for category in categories:
            if category['parent_id'] is None:
                tree.append(category)
            elif category['parent_id'] in category_map:
                parent = category_map[category['parent_id']]
                parent['children'].append(category)
        
        return create_success_response(
            data={'tree': tree}
        )
        
    except Exception as e:
        logger.error(f"Error getting category tree: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category tree"
        )

@router.get("/{category_id}")
async def get_category(
    category_id: str = Path(..., description="Category ID"),
    include_subcategories: bool = Query(False, description="Include subcategories"),
    include_products: bool = Query(False, description="Include products in this category")
):
    """Get category by ID"""
    try:
        db = get_db()
        
        if not db:
            # Find in sample categories
            category = next((c for c in SAMPLE_CATEGORIES if c['id'] == category_id), None)
            
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Category not found"
                )
            
            result = category.copy()
            
            if include_subcategories:
                result['subcategories'] = [
                    c for c in SAMPLE_CATEGORIES 
                    if c.get('parent_id') == category_id
                ]
            
            return create_success_response(data=result)
        
        # Get from Firestore
        doc = db.collection('categories').document(category_id).get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        category = doc.to_dict()
        category['id'] = doc.id
        category['category_id'] = doc.id
        
        # Include subcategories if requested
        if include_subcategories:
            subcategories = []
            sub_query = db.collection('categories').where('parent_id', '==', category_id)
            
            for sub_doc in sub_query.stream():
                subcategory = sub_doc.to_dict()
                subcategory['id'] = sub_doc.id
                subcategories.append(subcategory)
            
            category['subcategories'] = subcategories
        
        # Include products if requested
        if include_products:
            products = []
            prod_query = db.collection('products') \
                .where('category_id', '==', category_id) \
                .where('status', '==', 'active') \
                .limit(20)
            
            for prod_doc in prod_query.stream():
                product = prod_doc.to_dict()
                product['id'] = prod_doc.id
                products.append(product)
            
            category['products'] = products
        
        return create_success_response(data=category)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category"
        )

@router.post("")
async def create_category(
    category_data: CategoryCreate,
    current_user: dict = Depends(require_admin)
):
    """Create new category (admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            data={'category_id': 'test_cat_123'},
            message="Category created (development mode)"
        )
    
    try:
        # Generate category ID
        category_id = generate_id("cat_")
        
        # Create slug if not provided
        slug = category_data.slug or generate_slug(category_data.name)
        
        # Check if slug already exists
        existing_query = db.collection('categories').where('slug', '==', slug).limit(1)
        if list(existing_query.stream()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with slug '{slug}' already exists"
            )
        
        # Validate parent category if provided
        if category_data.parent_id:
            parent_doc = db.collection('categories').document(category_data.parent_id).get()
            if not parent_doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent category not found"
                )
        
        # Create category document
        category_doc = {
            'name': category_data.name,
            'slug': slug,
            'description': category_data.description,
            'parent_id': category_data.parent_id,
            'image': category_data.image,
            'metadata': category_data.metadata or {},
            'status': 'active',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_by': current_user['id']
        }
        
        db.collection('categories').document(category_id).set(category_doc)
        
        logger.info(f"Category created: {category_id} by user: {current_user['id']}")
        
        return create_success_response(
            data={'category_id': category_id, 'slug': slug},
            message="Category created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{category_id}")
async def update_category(
    category_id: str = Path(..., description="Category ID"),
    category_data: CategoryUpdate = None,
    current_user: dict = Depends(require_admin)
):
    """Update category (admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Category updated (development mode)"
        )
    
    try:
        doc_ref = db.collection('categories').document(category_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        update_data = category_data.dict(exclude_unset=True)
        
        # Check slug uniqueness if being updated
        if 'slug' in update_data:
            existing_query = db.collection('categories') \
                .where('slug', '==', update_data['slug']) \
                .where('__name__', '!=', category_id) \
                .limit(1)
            
            if list(existing_query.stream()):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with slug '{update_data['slug']}' already exists"
                )
        
        # Validate parent category if being updated
        if 'parent_id' in update_data and update_data['parent_id']:
            # Prevent self-reference
            if update_data['parent_id'] == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category cannot be its own parent"
                )
            
            parent_doc = db.collection('categories').document(update_data['parent_id']).get()
            if not parent_doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent category not found"
                )
        
        update_data['updated_at'] = datetime.utcnow()
        update_data['updated_by'] = current_user['id']
        
        doc_ref.update(update_data)
        
        logger.info(f"Category updated: {category_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Category updated successfully",
            data={'category_id': category_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{category_id}")
async def delete_category(
    category_id: str = Path(..., description="Category ID"),
    force: bool = Query(False, description="Force delete even if category has products"),
    current_user: dict = Depends(require_admin)
):
    """Delete category (admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Category deleted (development mode)"
        )
    
    try:
        doc_ref = db.collection('categories').document(category_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if category has subcategories
        subcategories = list(
            db.collection('categories')
            .where('parent_id', '==', category_id)
            .limit(1)
            .stream()
        )
        
        if subcategories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category with subcategories"
            )
        
        # Check if category has products
        if not force:
            products = list(
                db.collection('products')
                .where('category_id', '==', category_id)
                .where('status', '==', 'active')
                .limit(1)
                .stream()
            )
            
            if products:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot delete category with active products. Use force=true to override."
                )
        
        # Soft delete - just update status
        doc_ref.update({
            'status': 'deleted',
            'deleted_at': datetime.utcnow(),
            'deleted_by': current_user['id']
        })
        
        logger.info(f"Category deleted: {category_id} by user: {current_user['id']}")
        
        return create_success_response(
            message="Category deleted successfully",
            data={'category_id': category_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.patch("/{category_id}/reorder")
async def reorder_category(
    category_id: str = Path(..., description="Category ID"),
    new_position: int = Body(..., description="New position in the list"),
    current_user: dict = Depends(require_admin)
):
    """Reorder category position (admin only)"""
    db = get_db()
    
    if not db:
        return create_success_response(
            message="Category reordered (development mode)"
        )
    
    try:
        doc_ref = db.collection('categories').document(category_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Update the display order
        doc_ref.update({
            'display_order': new_position,
            'updated_at': datetime.utcnow(),
            'updated_by': current_user['id']
        })
        
        logger.info(f"Category reordered: {category_id} to position {new_position} by user: {current_user['id']}")
        
        return create_success_response(
            message="Category reordered successfully",
            data={'category_id': category_id, 'new_position': new_position}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reordering category: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
