"""Product Comparison API endpoints"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional, Dict, Any
import logging

from core.database import get_firestore_client
from models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products/compare", tags=["Product Comparison"])


@router.get("")
async def compare_products(
    ids: str = Query(..., description="Comma-separated product IDs to compare")
):
    """Compare multiple products side by side"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Parse product IDs
        product_ids = [id.strip() for id in ids.split(',') if id.strip()]
        
        if len(product_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least 2 products are required for comparison"
            )
        
        if len(product_ids) > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 4 products can be compared at once"
            )
        
        # Fetch products
        products = []
        for product_id in product_ids:
            product_ref = db.collection('products').document(product_id)
            product_doc = product_ref.get()
            
            if product_doc.exists:
                product_data = product_doc.to_dict()
                product_data['product_id'] = product_doc.id
                products.append(product_data)
        
        if len(products) < 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not enough valid products found for comparison"
            )
        
        # Extract comparison fields
        comparison_data = {
            "products": products,
            "comparison_fields": extract_comparison_fields(products),
            "total_products": len(products)
        }
        
        return {
            "success": True,
            "message": f"Comparing {len(products)} products",
            "data": comparison_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compare products"
        )


def extract_comparison_fields(products: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Extract and organize fields for easy comparison"""
    
    # Define fields to compare
    comparison_fields = {
        "basic_info": {
            "title": "Product Name",
            "price": "Price",
            "artisan_name": "Artisan",
            "rating": "Rating",
            "reviews_count": "Reviews"
        },
        "specifications": {
            "material": "Material",
            "crafting_method": "Crafting Method",
            "origin_location": "Origin",
            "processing_time": "Processing Time",
            "weight": "Weight",
            "dimensions": "Dimensions"
        },
        "features": {
            "is_handmade": "Handmade",
            "is_eco_friendly": "Eco-Friendly",
            "customizable": "Customizable",
            "made_to_order": "Made to Order",
            "in_stock": "In Stock"
        },
        "shipping": {
            "ships_from": "Ships From",
            "shipping_time": "Shipping Time",
            "free_shipping": "Free Shipping"
        }
    }
    
    result = {}
    
    for category, fields in comparison_fields.items():
        result[category] = {}
        for field_key, field_label in fields.items():
            result[category][field_key] = {
                "label": field_label,
                "values": []
            }
            
            for product in products:
                value = product.get(field_key, "—")
                
                # Format boolean values
                if isinstance(value, bool):
                    value = "✓" if value else "✗"
                
                # Format None values
                if value is None or value == "":
                    value = "—"
                
                result[category][field_key]["values"].append(value)
    
    return result


@router.get("/suggestions")
async def get_comparison_suggestions(
    product_id: str,
    limit: int = Query(3, ge=1, le=5)
):
    """Get suggested products to compare with a given product"""
    try:
        db = get_firestore_client()
        if not db:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection not available"
            )
        
        # Get the source product
        source_doc = db.collection('products').document(product_id).get()
        if not source_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        source_product = source_doc.to_dict()
        
        # Find similar products in the same category
        suggestions = []
        
        # Query by category
        if 'category' in source_product:
            similar_query = (
                db.collection('products')
                .where('category', '==', source_product['category'])
                .where('product_id', '!=', product_id)
                .limit(limit * 2)  # Get more to filter
            )
            
            similar_docs = similar_query.stream()
            
            for doc in similar_docs:
                if len(suggestions) >= limit:
                    break
                    
                product_data = doc.to_dict()
                product_data['product_id'] = doc.id
                
                # Calculate similarity score
                similarity = calculate_similarity(source_product, product_data)
                
                suggestions.append({
                    "product": product_data,
                    "similarity_score": similarity,
                    "reason": get_comparison_reason(source_product, product_data)
                })
            
            # Sort by similarity score
            suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)
            suggestions = suggestions[:limit]
        
        return {
            "success": True,
            "message": f"Found {len(suggestions)} products to compare",
            "suggestions": suggestions
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting comparison suggestions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get comparison suggestions"
        )


def calculate_similarity(product1: Dict, product2: Dict) -> float:
    """Calculate similarity score between two products"""
    score = 0.0
    
    # Same category: +30
    if product1.get('category') == product2.get('category'):
        score += 30
    
    # Similar price range: +20
    price1 = product1.get('price', 0)
    price2 = product2.get('price', 0)
    if price1 and price2:
        price_diff_pct = abs(price1 - price2) / max(price1, price2)
        if price_diff_pct < 0.2:  # Within 20% price range
            score += 20
        elif price_diff_pct < 0.5:  # Within 50% price range
            score += 10
    
    # Same material: +15
    if product1.get('material') == product2.get('material'):
        score += 15
    
    # Same crafting method: +10
    if product1.get('crafting_method') == product2.get('crafting_method'):
        score += 10
    
    # Both eco-friendly: +10
    if product1.get('is_eco_friendly') and product2.get('is_eco_friendly'):
        score += 10
    
    # Both handmade: +10
    if product1.get('is_handmade') and product2.get('is_handmade'):
        score += 10
    
    # Same artisan: +5
    if product1.get('seller_id') == product2.get('seller_id'):
        score += 5
    
    return min(score, 100)  # Cap at 100


def get_comparison_reason(product1: Dict, product2: Dict) -> str:
    """Generate a reason why these products are good for comparison"""
    reasons = []
    
    if product1.get('category') == product2.get('category'):
        reasons.append("same category")
    
    price1 = product1.get('price', 0)
    price2 = product2.get('price', 0)
    if price1 and price2:
        price_diff_pct = abs(price1 - price2) / max(price1, price2)
        if price_diff_pct < 0.2:
            reasons.append("similar price")
    
    if product1.get('material') == product2.get('material'):
        reasons.append("same material")
    
    if product1.get('artisan_name') == product2.get('artisan_name'):
        reasons.append("same artisan")
    
    if reasons:
        return f"Good comparison: {', '.join(reasons[:2])}"
    else:
        return "Alternative option in this category"
