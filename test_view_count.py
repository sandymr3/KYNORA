#!/usr/bin/env python
"""Test the product view count increment endpoint"""
import requests
import json

# Test incrementing view count for a product
product_id = "prod_001"
url = f"http://localhost:8000/products/{product_id}/view"

print(f"Testing view count increment for product: {product_id}")
print("-" * 50)

try:
    # Make POST request to increment view count
    response = requests.post(url)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data.get('message', '')}")
        if 'data' in data:
            view_count = data['data'].get('view_count', 'unknown')
            print(f"   New view count: {view_count}")
    else:
        print(f"❌ Failed:")
        print(json.dumps(response.json(), indent=2))
        
except Exception as e:
    print(f"❌ Error: {e}")
