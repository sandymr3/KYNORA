#!/usr/bin/env python
"""Test the backend API"""
import urllib.request
import json

def test_endpoint(url):
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            return data
    except Exception as e:
        return {"error": str(e)}

# Test endpoints
endpoints = [
    "http://localhost:8001/",
    "http://localhost:8001/products/featured",
    "http://localhost:8001/products",
    "http://localhost:8001/categories"
]

print("Testing Kynora Backend API at http://localhost:8001")
print("-" * 50)

for endpoint in endpoints:
    print(f"\nTesting: {endpoint}")
    result = test_endpoint(endpoint)
    if "error" in result:
        print(f"  ❌ Error: {result['error']}")
    else:
        print(f"  ✅ Success: {result.get('message', 'OK')}")
        if "products" in result:
            print(f"  📦 Products found: {len(result['products'])}")
        if "categories" in result:
            print(f"  📁 Categories found: {len(result['categories'])}")
