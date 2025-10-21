#!/usr/bin/env python
"""Test script to verify backend endpoints are working"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_endpoint(method, path, headers=None, data=None, params=None):
    """Test an endpoint and return the response"""
    url = BASE_URL + path
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            return None
            
        return {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text
        }
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Make sure the backend is running on port 8000"}
    except Exception as e:
        return {"error": str(e)}

def main():
    print("=" * 60)
    print("TESTING KYNORA BACKEND ENDPOINTS")
    print("=" * 60)
    
    # Test health endpoint
    print("\n1. Testing Health Check...")
    result = test_endpoint("GET", "/health")
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['body'].get('firebase'):
            print(f"   Firebase: {result['body'].get('firebase')}")
            print(f"   Database: {result['body'].get('database')}")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test featured products (public endpoint)
    print("\n2. Testing Featured Products (Public)...")
    result = test_endpoint("GET", "/products/featured", params={"limit": 5})
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            products = result['body'].get('data', {}).get('products', [])
            print(f"   Found {len(products)} featured products")
            for p in products[:3]:
                print(f"     - {p.get('title', 'Unknown')} (${p.get('price', 0)})")
        else:
            print(f"   Response: {json.dumps(result['body'], indent=2)}")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test all products
    print("\n3. Testing All Products (Public)...")
    result = test_endpoint("GET", "/products", params={"limit": 5})
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            products = result['body'].get('data', {}).get('products', [])
            print(f"   Found {len(products)} products")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test popular products
    print("\n4. Testing Popular Products (Public)...")
    result = test_endpoint("GET", "/products/popular", params={"limit": 5})
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            products = result['body'].get('data', {}).get('products', [])
            print(f"   Found {len(products)} popular products")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test search
    print("\n5. Testing Product Search (Public)...")
    result = test_endpoint("GET", "/products/search", params={"q": "wireless", "limit": 5})
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            products = result['body'].get('data', {}).get('products', [])
            print(f"   Found {len(products)} products matching 'wireless'")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test single product
    print("\n6. Testing Single Product (Public)...")
    result = test_endpoint("GET", "/products/prod_001")
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            product = result['body'].get('data', {})
            print(f"   Product: {product.get('title', 'Unknown')}")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test categories
    print("\n7. Testing Categories (Public)...")
    result = test_endpoint("GET", "/categories")
    if result and not result.get("error"):
        print(f"   ✅ Status: {result['status_code']}")
        if result['status_code'] == 200:
            categories = result['body'].get('data', {}).get('categories', [])
            print(f"   Found {len(categories)} categories")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test protected endpoint without auth
    print("\n8. Testing Protected Endpoint without Auth...")
    result = test_endpoint("GET", "/auth/me")
    if result and not result.get("error"):
        print(f"   Status: {result['status_code']}")
        if result['status_code'] == 401:
            print(f"   ✅ Correctly rejected: {result['body'].get('error', 'Unauthorized')}")
        else:
            print(f"   ❌ Should have returned 401 Unauthorized")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    # Test with mock authentication (if Firebase is not connected)
    print("\n9. Testing with Mock Authentication...")
    headers = {"Authorization": "Bearer mock_token_12345"}
    result = test_endpoint("GET", "/auth/me", headers=headers)
    if result and not result.get("error"):
        print(f"   Status: {result['status_code']}")
        if result['status_code'] == 200:
            user = result['body'].get('data', {})
            print(f"   ✅ Authenticated as: {user.get('email', 'Unknown')}")
        else:
            print(f"   Auth not working: {result['body'].get('error', 'Unknown error')}")
    else:
        print(f"   ❌ Error: {result.get('error')}")
    
    print("\n" + "=" * 60)
    print("Testing Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
