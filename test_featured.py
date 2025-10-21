#!/usr/bin/env python
"""Test the featured products endpoint"""
import urllib.request
import requests
import json

url = "http://localhost:8000/products/featured?limit=10"
print(f"Testing: {url}")
print("-" * 50)

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Content Type: {response.headers.get('content-type', 'unknown')}")
    print(f"Response Body:")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
    except:
        print(response.text[:1000])
            
except Exception as e:
    print(f"❌ Error: {e}")
