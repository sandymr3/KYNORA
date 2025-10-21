"""Category Management API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging

from config.firebase import db
from models.category import (
    Category, CategoryCreate, CategoryUpdate,
    CategoryResponse, CategoryListResponse, CategoryTree, CategoryTreeResponse
)
from utils.auth import require_admin
from utils.helpers import Helpers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=CategoryListResponse)
async def list_categories():
    """List all categories"""
    try:
        # Get all active categories
        query = db.collection('categories').where('status', '==', 'active')
        
        categories = []
        for doc in query.stream():
            category_data = doc.to_dict()
            category_data['category_id'] = doc.id
            categories.append(Category(**category_data))
        
        # Sort by display order
        categories.sort(key=lambda x: x.display_order)
        
        return CategoryListResponse(
            success=True,
            message="Categories retrieved successfully",
            categories=categories,
            total=len(categories)
        )
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@router.get("/tree", response_model=CategoryTreeResponse)
async def get_category_tree():
    """Get hierarchical category tree"""
    try:
        # Get all active categories
        query = db.collection('categories').where('status', '==', 'active')
        
        categories = []
        for doc in query.stream():
            category_data = doc.to_dict()
            category_data['category_id'] = doc.id
            categories.append(Category(**category_data))
        
        # Build tree structure
        tree = []
        category_map = {cat.category_id: cat for cat in categories}
        
        # First, add root categories
        for category in categories:
            if category.parent_id is None:
                tree_node = CategoryTree(
                    category=category,
                    children=[]
                )
                tree.append(tree_node)
        
        # Then, add subcategories
        for category in categories:
            if category.parent_id:
                # Find parent in tree
                for root in tree:
                    if root.category.category_id == category.parent_id:
                        child_node = CategoryTree(
                            category=category,
                            children=[]
                        )
                        root.children.append(child_node)
                        break
        
        # Sort by display order
        tree.sort(key=lambda x: x.category.display_order)
        for node in tree:
            node.children.sort(key=lambda x: x.category.display_order)
        
        return CategoryTreeResponse(
            success=True,
            message="Category tree retrieved successfully",
            tree=tree
        )
        
    except Exception as e:
        logger.error(f"Error getting category tree: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category tree"
        )


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    """Get category details"""
    try:
        # Get category
        category_doc = db.collection('categories').document(category_id).get()
        
        if not category_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        category_data = category_doc.to_dict()
        category_data['category_id'] = category_doc.id
        category = Category(**category_data)
        
        return CategoryResponse(
            success=True,
            message="Category retrieved successfully",
            category=category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category"
        )


@router.get("/{category_id}/products")
async def get_category_products(
    category_id: str,
    page: int = 1,
    limit: int = 20
):
    """Get products in category"""
    try:
        # Verify category exists
        category_doc = db.collection('categories').document(category_id).get()
        if not category_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Get products
        query = db.collection('products')\
            .where('category_id', '==', category_id)\
            .where('status', '==', 'active')
        
        # Get total
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
            from models.product import Product
            products.append(Product(**product_data))
        
        # Calculate pagination
        pagination = Helpers.calculate_pagination(total, page, limit)
        
        from models.product import ProductListResponse
        return ProductListResponse(
            success=True,
            message="Category products retrieved",
            products=products,
            **pagination
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting category products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve category products"
        )


@router.post("", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    current_user = Depends(require_admin)
):
    """Create new category (admin only)"""
    try:
        # Generate category ID from slug
        category_id = category_data.slug
        
        # Check if category exists
        existing = db.collection('categories').document(category_id).get()
        if existing.exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category with this slug already exists"
            )
        
        # Determine level and path
        level = 0
        path = category_id
        
        if category_data.parent_id:
            # Get parent category
            parent_doc = db.collection('categories').document(category_data.parent_id).get()
            if not parent_doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent category not found"
                )
            parent = parent_doc.to_dict()
            level = parent.get('level', 0) + 1
            path = f"{parent.get('path')}/{category_id}"
        
        # Create category
        from datetime import datetime
        category = Category(
            category_id=category_id,
            level=level,
            path=path,
            product_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            **category_data.dict()
        )
        
        # Save to Firestore
        db.collection('categories').document(category_id).set(
            category.to_firestore()
        )
        
        return CategoryResponse(
            success=True,
            message="Category created successfully",
            category=category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create category"
        )


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category_update: CategoryUpdate,
    current_user = Depends(require_admin)
):
    """Update category (admin only)"""
    try:
        # Get existing category
        category_doc = db.collection('categories').document(category_id).get()
        
        if not category_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Update fields
        from datetime import datetime
        update_data = category_update.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.utcnow()
        update_data = Helpers.filter_none_values(update_data)
        
        # Update in Firestore
        db.collection('categories').document(category_id).update(update_data)
        
        # Get updated category
        updated_doc = db.collection('categories').document(category_id).get()
        updated_data = updated_doc.to_dict()
        updated_data['category_id'] = category_id
        updated_category = Category(**updated_data)
        
        return CategoryResponse(
            success=True,
            message="Category updated successfully",
            category=updated_category
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update category"
        )


@router.delete("/{category_id}")
async def delete_category(
    category_id: str,
    current_user = Depends(require_admin)
):
    """Delete category (admin only)"""
    try:
        # Get category
        category_doc = db.collection('categories').document(category_id).get()
        
        if not category_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        category_data = category_doc.to_dict()
        
        # Check if category has products
        if category_data.get('product_count', 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category with products"
            )
        
        # Check if category has subcategories
        subcategories = db.collection('categories')\
            .where('parent_id', '==', category_id)\
            .limit(1)\
            .stream()
        
        if list(subcategories):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete category with subcategories"
            )
        
        # Delete category
        db.collection('categories').document(category_id).delete()
        
        return {
            "success": True,
            "message": "Category deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category"
        )
