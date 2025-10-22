"""
Quick script to check Firestore database status
"""
import os
os.environ.pop('FIRESTORE_EMULATOR_HOST', None)  # Ensure we check production

from core.database import initialize_firebase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database():
    """Check what data exists in Firestore"""
    try:
        db = initialize_firebase()
        if not db:
            logger.error("❌ Failed to initialize Firebase")
            return
        
        logger.info("✅ Connected to Firestore")
        logger.info("\n" + "="*60)
        logger.info("CHECKING DATABASE COLLECTIONS")
        logger.info("="*60 + "\n")
        
        collections = [
            'users',
            'products', 
            'categories',
            'orders',
            'carts',
            'reviews',
            'wishlists'
        ]
        
        for collection_name in collections:
            try:
                docs = db.collection(collection_name).limit(5).get()
                count = len(docs)
                
                if count > 0:
                    logger.info(f"✅ {collection_name}: {count} document(s) found")
                    # Show first doc structure (without sensitive data)
                    first_doc = docs[0].to_dict()
                    logger.info(f"   Sample fields: {', '.join(first_doc.keys())}")
                else:
                    logger.warning(f"⚠️  {collection_name}: Empty (0 documents)")
            except Exception as e:
                logger.error(f"❌ {collection_name}: Error - {e}")
        
        logger.info("\n" + "="*60)
        logger.info("DATABASE CHECK COMPLETE")
        logger.info("="*60)
        
        # Recommendations
        logger.info("\n📋 RECOMMENDATIONS:")
        logger.info("   • If collections are empty, run:")
        logger.info("     python scripts/setup_firestore.py --seed=true")
        logger.info("")
        logger.info("   • To view in Firebase Console:")
        logger.info("     https://console.firebase.google.com")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        logger.info("\n💡 Make sure:")
        logger.info("   1. serviceAccountKey.json exists")
        logger.info("   2. Firebase project ID is correct in .env")
        logger.info("   3. Firestore is enabled in Firebase Console")

if __name__ == "__main__":
    check_database()
