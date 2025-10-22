"""
Script to create sample reviews for testing
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import initialize_firebase
from datetime import datetime, timedelta
import logging
import random
from utils.helpers import Helpers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample review data
SAMPLE_REVIEWS = [
    {
        "rating": 5,
        "title": "Amazing craftsmanship!",
        "comment": "The ceramic bowl set is absolutely beautiful. Each piece is unique and the glaze is stunning.",
        "verified_purchase": True,
        "helpful_count": 12
    },
    {
        "rating": 4,
        "title": "Great quality, minor imperfection",
        "comment": "Love the handmade feel. One bowl has a tiny chip but that adds to the character.",
        "verified_purchase": True,
        "helpful_count": 8
    },
    {
        "rating": 5,
        "title": "Perfect gift",
        "comment": "Bought this as a wedding gift and they loved it! The packaging was also very nice.",
        "verified_purchase": True,
        "helpful_count": 5
    },
    {
        "rating": 5,
        "title": "Better than expected",
        "comment": "The photos don't do justice to these bowls. The colors are rich and the texture is amazing.",
        "verified_purchase": False,
        "helpful_count": 3
    },
    {
        "rating": 4,
        "title": "Good value for handmade items",
        "comment": "Considering these are handmade, the price is very reasonable. Will buy again!",
        "verified_purchase": True,
        "helpful_count": 7
    }
]

def create_sample_reviews():
    """Create sample reviews for products"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("Failed to initialize Firebase")
            return False
        
        logger.info("Creating sample reviews...")
        
        # Get first few products to add reviews to
        products_ref = db.collection('products').limit(3)
        products = list(products_ref.stream())
        
        if not products:
            logger.warning("No products found. Run setup_artisan_products.py first!")
            return False
        
        review_count = 0
        for product_doc in products:
            product_data = product_doc.to_dict()
            product_id = product_doc.id
            product_title = product_data.get('title', 'Unknown')
            
            logger.info(f"Adding reviews for: {product_title}")
            
            # Add 2-3 random reviews per product
            num_reviews = random.randint(2, 3)
            selected_reviews = random.sample(SAMPLE_REVIEWS, min(num_reviews, len(SAMPLE_REVIEWS)))
            
            for idx, review_template in enumerate(selected_reviews):
                review_id = Helpers.generate_id("rev")
                
                # Create review with random dates in the past month
                days_ago = random.randint(1, 30)
                created_at = datetime.utcnow() - timedelta(days=days_ago)
                
                review_data = {
                    "review_id": review_id,
                    "product_id": product_id,
                    "user_id": f"user_sample_{idx + 1}",  # Fake user IDs for testing
                    "order_id": f"order_sample_{idx + 1}",  # Fake order IDs
                    "rating": review_template["rating"],
                    "title": review_template["title"],
                    "comment": review_template["comment"],
                    "verified_purchase": review_template["verified_purchase"],
                    "helpful_count": review_template["helpful_count"],
                    "status": "approved",  # All approved for visibility
                    "images": [],
                    "created_at": created_at,
                    "updated_at": created_at,
                    "user_info": {
                        "user_id": f"user_sample_{idx + 1}",
                        "displayName": f"Customer {idx + 1}",
                        "avatar": None
                    }
                }
                
                # Save review
                db.collection('reviews').document(review_id).set(review_data)
                review_count += 1
                logger.info(f"   ✅ Added review: {review_template['title'][:30]}...")
        
        logger.info(f"\n✅ Created {review_count} sample reviews successfully!")
        
        # Update product ratings
        for product_doc in products:
            product_id = product_doc.id
            
            # Get all reviews for this product
            reviews = db.collection('reviews').where('product_id', '==', product_id).stream()
            reviews_list = list(reviews)
            
            if reviews_list:
                total_rating = sum(r.to_dict().get('rating', 0) for r in reviews_list)
                count = len(reviews_list)
                average = round(total_rating / count, 2) if count > 0 else 0
                
                # Update product
                db.collection('products').document(product_id).update({
                    'average_rating': average,
                    'rating_average': average,
                    'review_count': count,
                    'rating_count': count
                })
                logger.info(f"Updated product {product_id}: {average}★ ({count} reviews)")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating sample reviews: {e}")
        return False

if __name__ == "__main__":
    create_sample_reviews()
