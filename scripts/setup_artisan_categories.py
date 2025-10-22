"""
Script to set up categories for artisan/handmade products
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import initialize_firebase
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Categories for artisan/handmade products
ARTISAN_CATEGORIES = [
    {
        "id": "pottery",
        "name": "Pottery & Ceramics",
        "slug": "pottery-ceramics",
        "description": "Handcrafted pottery, ceramics, and clay artworks",
        "image_url": "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "bowls", "name": "Bowls & Plates"},
            {"id": "vases", "name": "Vases & Decorative"},
            {"id": "mugs", "name": "Mugs & Cups"},
            {"id": "planters", "name": "Planters & Pots"}
        ]
    },
    {
        "id": "handmade-toys",
        "name": "Handmade Toys",
        "slug": "handmade-toys",
        "description": "Handcrafted wooden, fabric, and traditional toys",
        "image_url": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "wooden-toys", "name": "Wooden Toys"},
            {"id": "soft-toys", "name": "Soft Toys & Dolls"},
            {"id": "educational", "name": "Educational Toys"},
            {"id": "traditional", "name": "Traditional Games"}
        ]
    },
    {
        "id": "textiles",
        "name": "Handwoven Textiles",
        "slug": "handwoven-textiles",
        "description": "Handwoven fabrics, rugs, and textile art",
        "image_url": "https://images.unsplash.com/photo-1528459801416-a9e53bbf4e17?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "rugs", "name": "Rugs & Carpets"},
            {"id": "blankets", "name": "Blankets & Throws"},
            {"id": "scarves", "name": "Scarves & Shawls"},
            {"id": "bags", "name": "Bags & Pouches"}
        ]
    },
    {
        "id": "jewelry",
        "name": "Handmade Jewelry",
        "slug": "handmade-jewelry",
        "description": "Handcrafted jewelry and accessories",
        "image_url": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "necklaces", "name": "Necklaces & Pendants"},
            {"id": "bracelets", "name": "Bracelets & Bangles"},
            {"id": "earrings", "name": "Earrings"},
            {"id": "rings", "name": "Rings"}
        ]
    },
    {
        "id": "woodcraft",
        "name": "Wood Crafts",
        "slug": "wood-crafts",
        "description": "Hand-carved and crafted wooden items",
        "image_url": "https://images.unsplash.com/photo-1513519107127-1bed33748e4c?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "furniture", "name": "Small Furniture"},
            {"id": "decor", "name": "Home Decor"},
            {"id": "kitchenware", "name": "Kitchen Items"},
            {"id": "sculptures", "name": "Sculptures & Art"}
        ]
    },
    {
        "id": "artwork",
        "name": "Art & Paintings",
        "slug": "art-paintings",
        "description": "Original paintings, drawings, and artworks",
        "image_url": "https://images.unsplash.com/photo-1460661419201-fd4cecdf8a8b?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "paintings", "name": "Paintings"},
            {"id": "drawings", "name": "Drawings & Sketches"},
            {"id": "prints", "name": "Prints & Posters"},
            {"id": "mixed-media", "name": "Mixed Media"}
        ]
    },
    {
        "id": "candles-soaps",
        "name": "Candles & Soaps",
        "slug": "candles-soaps",
        "description": "Handmade candles, soaps, and bath products",
        "image_url": "https://images.unsplash.com/photo-1602028915047-65269d1b975f?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "candles", "name": "Scented Candles"},
            {"id": "soaps", "name": "Natural Soaps"},
            {"id": "bath-bombs", "name": "Bath Bombs"},
            {"id": "aromatherapy", "name": "Aromatherapy"}
        ]
    },
    {
        "id": "metalwork",
        "name": "Metal Crafts",
        "slug": "metal-crafts",
        "description": "Handcrafted metal items and decorative pieces",
        "image_url": "https://images.unsplash.com/photo-1589939705384-d09cae2b4583?w=500",
        "is_active": True,
        "product_count": 0,
        "subcategories": [
            {"id": "lamps", "name": "Lamps & Lighting"},
            {"id": "wall-art", "name": "Wall Art"},
            {"id": "utensils", "name": "Utensils & Tools"},
            {"id": "decorative", "name": "Decorative Items"}
        ]
    }
]

def setup_categories():
    """Set up artisan product categories in Firestore"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("Failed to initialize Firebase")
            return False
        
        logger.info("Setting up artisan product categories...")
        
        for category in ARTISAN_CATEGORIES:
            category_id = category["id"]
            
            # Prepare category data
            category_data = {
                "name": category["name"],
                "slug": category["slug"],
                "description": category["description"],
                "image_url": category["image_url"],
                "is_active": category["is_active"],
                "product_count": category["product_count"],
                "parent_id": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Create main category
            db.collection('categories').document(category_id).set(category_data)
            logger.info(f"✅ Created category: {category['name']}")
            
            # Create subcategories
            for subcategory in category.get("subcategories", []):
                sub_id = f"{category_id}_{subcategory['id']}"
                sub_data = {
                    "name": subcategory["name"],
                    "slug": f"{category['slug']}-{subcategory['id']}",
                    "description": f"{subcategory['name']} in {category['name']}",
                    "parent_id": category_id,
                    "is_active": True,
                    "product_count": 0,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                db.collection('categories').document(sub_id).set(sub_data)
                logger.info(f"   ✅ Created subcategory: {subcategory['name']}")
        
        logger.info("\n✅ All categories created successfully!")
        logger.info("\n📋 Categories Summary:")
        logger.info("   • Pottery & Ceramics")
        logger.info("   • Handmade Toys")
        logger.info("   • Handwoven Textiles")
        logger.info("   • Handmade Jewelry")
        logger.info("   • Wood Crafts")
        logger.info("   • Art & Paintings")
        logger.info("   • Candles & Soaps")
        logger.info("   • Metal Crafts")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up categories: {e}")
        return False

if __name__ == "__main__":
    setup_categories()
