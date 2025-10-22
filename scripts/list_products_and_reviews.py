"""
List all products and their reviews for debugging
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import initialize_firebase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_products_and_reviews():
    """List all products and their associated reviews"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("Failed to initialize Firebase")
            return False
        
        print("\n" + "="*60)
        print("📦 PRODUCTS IN DATABASE:")
        print("="*60)
        
        # Get all products
        products = db.collection('products').limit(10).stream()
        
        product_count = 0
        for product_doc in products:
            product_data = product_doc.to_dict()
            product_id = product_doc.id
            product_count += 1
            
            print(f"\n{product_count}. Product ID: {product_id}")
            print(f"   Title: {product_data.get('title', 'Unknown')}")
            print(f"   Price: ${product_data.get('price', 0)}")
            print(f"   Category: {product_data.get('category_id', 'Unknown')}")
            print(f"   Rating: {product_data.get('average_rating', 0)}★ ({product_data.get('review_count', 0)} reviews)")
            
            # Get reviews for this product
            reviews = db.collection('reviews').where('product_id', '==', product_id).stream()
            review_list = list(reviews)
            
            if review_list:
                print(f"   📝 Reviews ({len(review_list)}):")
                for idx, review_doc in enumerate(review_list[:3]):  # Show first 3 reviews
                    review_data = review_doc.to_dict()
                    print(f"      - {review_data.get('rating', 0)}★ \"{review_data.get('title', review_data.get('comment', 'No comment'))[:50]}...\"")
                    print(f"        Status: {review_data.get('status', 'unknown')}, Verified: {review_data.get('verified_purchase', False)}")
            else:
                print("   📝 No reviews")
        
        if product_count == 0:
            print("\n❌ No products found in database!")
            print("   Run: python scripts/setup_artisan_products.py")
        else:
            print(f"\n✅ Found {product_count} products")
        
        # List all reviews
        print("\n" + "="*60)
        print("📝 ALL REVIEWS IN DATABASE:")
        print("="*60)
        
        all_reviews = db.collection('reviews').limit(20).stream()
        review_count = 0
        
        for review_doc in all_reviews:
            review_data = review_doc.to_dict()
            review_id = review_doc.id
            review_count += 1
            
            print(f"\n{review_count}. Review ID: {review_id}")
            print(f"   Product ID: {review_data.get('product_id', 'Unknown')}")
            print(f"   Rating: {review_data.get('rating', 0)}★")
            print(f"   Title: {review_data.get('title', 'No title')}")
            print(f"   Comment: {review_data.get('comment', review_data.get('content', 'No content'))[:100]}...")
            print(f"   Status: {review_data.get('status', 'unknown')}")
            print(f"   Created: {review_data.get('created_at', 'Unknown')}")
        
        if review_count == 0:
            print("\n❌ No reviews found in database!")
            print("   Run: python scripts/create_sample_reviews.py")
        else:
            print(f"\n✅ Found {review_count} reviews")
        
        print("\n" + "="*60)
        print("🔍 TEST COMMANDS:")
        print("="*60)
        print("\nTest with actual product IDs from above:")
        print("curl -X GET \"http://localhost:8000/reviews/products/[PRODUCT_ID]?limit=20&offset=0\"")
        
        return True
        
    except Exception as e:
        logger.error(f"Error listing products and reviews: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    list_products_and_reviews()
