import os
import dotenv
dotenv.load_dotenv()

from firestore_ecommerce_db import FirestoreEcommerceDB

def debug_featured_products():
    try:
        db = FirestoreEcommerceDB()
        
        print("=== DEBUGGING FEATURED PRODUCTS ===")
        
        # Check featured products
        featured_result = db.get_featured_products(limit=10)
        print(f"Featured products result: {featured_result}")
        
        # Check raw Firestore data
        from firebase_admin import firestore
        firestore_client = firestore.client()
        
        products_ref = firestore_client.collection('products')
        all_docs = products_ref.stream()
        
        featured_count = 0
        total_count = 0
        
        for doc in all_docs:
            total_count += 1
            data = doc.to_dict()
            is_featured = data.get('is_featured', False)
            status = data.get('status', 'unknown')
            title = data.get('title', 'No title')
            
            print(f"Product: {title[:30]}, Status: {status}, Featured: {is_featured}")
            
            if is_featured and status == 'active':
                featured_count += 1
        
        print(f"\nTotal products: {total_count}")
        print(f"Featured active products: {featured_count}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_featured_products()