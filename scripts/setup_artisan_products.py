"""
Script to set up sample artisan/handmade products
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import initialize_firebase
from datetime import datetime
import logging
from utils.helpers import Helpers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample artisan products
ARTISAN_PRODUCTS = [
    {
        "title": "Hand-Thrown Ceramic Bowl Set",
        "description": "Beautiful set of 4 ceramic bowls, each uniquely hand-thrown on a potter's wheel. Perfect for serving salads, soups, or as decorative pieces. Each bowl features a unique glaze pattern in earth tones.",
        "short_description": "Set of 4 handmade ceramic bowls with unique glazes",
        "price": 85.00,
        "category_id": "pottery",
        "subcategory_id": "pottery_bowls",
        "artisan_name": "Sarah Chen",
        "material": "Stoneware clay",
        "crafting_method": "Hand-thrown on potter's wheel",
        "customizable": True,
        "made_to_order": False,
        "processing_time": 0,
        "care_instructions": "Dishwasher and microwave safe. Hand washing recommended for longevity.",
        "origin_location": "Portland, Oregon",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Each piece is unique with slight variations in glaze and shape",
        "images": [
            "https://images.unsplash.com/photo-1565193566173-7a0ee3dbe261?w=800",
            "https://images.unsplash.com/photo-1610701596007-11502861dcfa?w=800"
        ],
        "inventory_quantity": 12,
        "tags": ["ceramic", "bowls", "kitchen", "handmade", "eco-friendly"],
        "is_featured": True
    },
    {
        "title": "Wooden Train Set - Handcrafted",
        "description": "Classic wooden train set handcrafted from sustainable pine wood. Includes engine, 3 carriages, and 20 pieces of track. Painted with non-toxic, child-safe paints. Perfect educational toy for children aged 3+.",
        "short_description": "Handcrafted wooden train set with tracks",
        "price": 120.00,
        "category_id": "handmade-toys",
        "subcategory_id": "handmade-toys_wooden-toys",
        "artisan_name": "Robert Johnson",
        "material": "Sustainable pine wood",
        "crafting_method": "Hand-carved and sanded",
        "customizable": True,
        "made_to_order": True,
        "processing_time": 7,
        "care_instructions": "Wipe clean with damp cloth. Do not submerge in water.",
        "origin_location": "Vermont, USA",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Can be personalized with child's name",
        "images": [
            "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=800",
            "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800"
        ],
        "inventory_quantity": 5,
        "tags": ["wooden", "toys", "educational", "children", "sustainable"],
        "is_featured": True
    },
    {
        "title": "Handwoven Wool Rug - Traditional Pattern",
        "description": "Stunning handwoven wool rug featuring traditional geometric patterns. Made using centuries-old weaving techniques passed down through generations. Natural dyes create rich, lasting colors.",
        "short_description": "Traditional handwoven wool rug with geometric patterns",
        "price": 350.00,
        "category_id": "textiles",
        "subcategory_id": "textiles_rugs",
        "artisan_name": "Maria Rodriguez",
        "material": "100% wool with natural dyes",
        "crafting_method": "Hand-loomed using traditional techniques",
        "customizable": True,
        "made_to_order": True,
        "processing_time": 21,
        "care_instructions": "Vacuum regularly. Professional cleaning recommended for stains.",
        "origin_location": "New Mexico, USA",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Custom sizes and color combinations available",
        "images": [
            "https://images.unsplash.com/photo-1527786356703-4b100091cd2c?w=800",
            "https://images.unsplash.com/photo-1600166898405-da9535204843?w=800"
        ],
        "inventory_quantity": 3,
        "tags": ["rug", "wool", "handwoven", "traditional", "home-decor"],
        "is_featured": False
    },
    {
        "title": "Sterling Silver Leaf Pendant Necklace",
        "description": "Delicate sterling silver pendant inspired by nature. Each leaf is hand-formed and textured to capture realistic details. Comes on an 18-inch sterling silver chain.",
        "short_description": "Hand-formed sterling silver leaf pendant",
        "price": 95.00,
        "category_id": "jewelry",
        "subcategory_id": "jewelry_necklaces",
        "artisan_name": "Emma Thompson",
        "material": "Sterling silver",
        "crafting_method": "Hand-formed and textured",
        "customizable": False,
        "made_to_order": False,
        "processing_time": 0,
        "care_instructions": "Polish with silver cloth. Store in provided pouch when not wearing.",
        "origin_location": "Austin, Texas",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Each pendant has unique texture and patina",
        "images": [
            "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800",
            "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?w=800"
        ],
        "inventory_quantity": 8,
        "tags": ["jewelry", "silver", "necklace", "nature-inspired", "handmade"],
        "is_featured": True
    },
    {
        "title": "Hand-Carved Wooden Serving Board",
        "description": "Beautiful live-edge walnut serving board, perfect for cheese, charcuterie, or as a decorative piece. Each board showcases the natural wood grain and is finished with food-safe mineral oil.",
        "short_description": "Live-edge walnut serving board",
        "price": 75.00,
        "category_id": "woodcraft",
        "subcategory_id": "woodcraft_kitchenware",
        "artisan_name": "David Kim",
        "material": "Black walnut",
        "crafting_method": "Hand-carved and sanded",
        "customizable": True,
        "made_to_order": False,
        "processing_time": 0,
        "care_instructions": "Hand wash only. Oil periodically with mineral oil.",
        "origin_location": "North Carolina, USA",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Natural wood grain makes each piece one-of-a-kind",
        "images": [
            "https://images.unsplash.com/photo-1550411294-098af68c8c2e?w=800",
            "https://images.unsplash.com/photo-1615887023516-9b6bcd559e87?w=800"
        ],
        "inventory_quantity": 10,
        "tags": ["wood", "kitchen", "serving", "walnut", "sustainable"],
        "is_featured": False
    },
    {
        "title": "Abstract Watercolor Painting - Original",
        "description": "Original abstract watercolor painting on 300gsm cold-pressed paper. Vibrant blues and greens create a calming, oceanic feel. Unframed, ships in protective tube.",
        "short_description": "Original abstract watercolor artwork",
        "price": 250.00,
        "category_id": "artwork",
        "subcategory_id": "artwork_paintings",
        "artisan_name": "Lisa Chang",
        "material": "Professional watercolors on archival paper",
        "crafting_method": "Wet-on-wet watercolor technique",
        "customizable": False,
        "made_to_order": False,
        "processing_time": 0,
        "care_instructions": "Frame behind UV-protective glass. Avoid direct sunlight.",
        "origin_location": "San Francisco, California",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "One-of-a-kind original artwork",
        "images": [
            "https://images.unsplash.com/photo-1549887534-1541e9326642?w=800",
            "https://images.unsplash.com/photo-1579783902614-a3fb3927b6a5?w=800"
        ],
        "inventory_quantity": 1,
        "tags": ["art", "watercolor", "original", "abstract", "painting"],
        "is_featured": True
    },
    {
        "title": "Lavender Soy Candle Set",
        "description": "Set of 3 hand-poured soy candles infused with pure lavender essential oil. Clean burning, long-lasting (40+ hours each). Packaged in reusable glass jars.",
        "short_description": "Hand-poured lavender soy candles",
        "price": 45.00,
        "category_id": "candles-soaps",
        "subcategory_id": "candles-soaps_candles",
        "artisan_name": "Jessica Brown",
        "material": "100% soy wax, cotton wicks",
        "crafting_method": "Hand-poured in small batches",
        "customizable": True,
        "made_to_order": False,
        "processing_time": 0,
        "care_instructions": "Trim wick to 1/4 inch before each use. Burn for max 4 hours at a time.",
        "origin_location": "Asheville, North Carolina",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Custom scent blends available",
        "images": [
            "https://images.unsplash.com/photo-1602028915047-65269d1b975f?w=800",
            "https://images.unsplash.com/photo-1603006905003-be475563bc59?w=800"
        ],
        "inventory_quantity": 20,
        "tags": ["candles", "lavender", "soy", "aromatherapy", "eco-friendly"],
        "is_featured": False
    },
    {
        "title": "Copper Wind Chimes - Garden Art",
        "description": "Handcrafted copper wind chimes that create beautiful, melodic tones. Weather-resistant finish develops a natural patina over time. Perfect for gardens, patios, or meditation spaces.",
        "short_description": "Handcrafted copper wind chimes",
        "price": 135.00,
        "category_id": "metalwork",
        "subcategory_id": "metalwork_decorative",
        "artisan_name": "Michael Torres",
        "material": "Copper with brass accents",
        "crafting_method": "Hand-forged and tuned",
        "customizable": False,
        "made_to_order": True,
        "processing_time": 5,
        "care_instructions": "No maintenance required. Will develop natural patina outdoors.",
        "origin_location": "Colorado Springs, Colorado",
        "is_eco_friendly": True,
        "is_handmade": True,
        "uniqueness_note": "Each chime is tuned to a unique harmonic scale",
        "images": [
            "https://images.unsplash.com/photo-1589939705384-d09cae2b4583?w=800",
            "https://images.unsplash.com/photo-1522444690501-0c7c94c357b7?w=800"
        ],
        "inventory_quantity": 4,
        "tags": ["copper", "wind-chimes", "garden", "outdoor", "metal-art"],
        "is_featured": False
    }
]

def setup_products():
    """Set up sample artisan products in Firestore"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("Failed to initialize Firebase")
            return False
        
        logger.info("Setting up artisan products...")
        
        for product_data in ARTISAN_PRODUCTS:
            # Generate product ID
            product_id = Helpers.generate_id("prod")
            
            # Prepare product data
            product = {
                **product_data,
                "product_id": product_id,
                "seller_id": "artisan_" + product_data["artisan_name"].lower().replace(" ", "_"),
                "slug": Helpers.generate_slug(product_data["title"]),
                "sku": f"ART-{product_id[-6:]}",
                "status": "active",
                "is_on_sale": False,
                "view_count": 0,
                "sales_count": 0,
                "rating_average": 0.0,
                "rating_count": 0,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Set thumbnail
            if product.get("images"):
                product["thumbnail"] = product["images"][0]
            
            # Create product
            db.collection('products').document(product_id).set(product)
            logger.info(f"✅ Created product: {product_data['title']}")
        
        logger.info("\n✅ All products created successfully!")
        logger.info(f"\n📋 Created {len(ARTISAN_PRODUCTS)} artisan products")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up products: {e}")
        return False

if __name__ == "__main__":
    setup_products()
