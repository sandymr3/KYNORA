#!/usr/bin/env python3
"""
Test script to verify KYNORA API is working
Run this after setting up the backend
"""

import requests
import json
import sys
from datetime import datetime


BASE_URL = "http://localhost:8000"


def print_response(response, title="Response"):
    """Pretty print API response"""
    print(f"\n{'='*50}")
    print(f"{title}")
    print(f"{'='*50}")
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)
    print(f"{'='*50}\n")


def test_health():
    """Test health check endpoint"""
    print("🔍 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response, "Health Check")
    return response.status_code == 200


def test_products():
    """Test products endpoints"""
    print("🔍 Testing Products...")
    
    # Get all products
    response = requests.get(f"{BASE_URL}/products")
    print_response(response, "Get Products")
    
    # Get featured products
    response = requests.get(f"{BASE_URL}/products/featured")
    print_response(response, "Get Featured Products")
    
    return response.status_code == 200


def test_categories():
    """Test categories endpoints"""
    print("🔍 Testing Categories...")
    
    # Get all categories
    response = requests.get(f"{BASE_URL}/categories")
    print_response(response, "Get Categories")
    
    # Get category tree
    response = requests.get(f"{BASE_URL}/categories/tree")
    print_response(response, "Get Category Tree")
    
    return response.status_code == 200


def test_auth():
    """Test authentication endpoints"""
    print("🔍 Testing Authentication...")
    
    # Test login
    login_data = {
        "email": "sandy@gmail.com",
        "password": "Sandy@1"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json=login_data
    )
    print_response(response, "Login")
    
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data:
            return data["access_token"]
    return None


def test_cart(token):
    """Test cart endpoints"""
    print("🔍 Testing Cart...")
    
    if not token:
        print("⚠️ No token available, skipping cart tests")
        return False
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Get cart
    response = requests.get(
        f"{BASE_URL}/cart",
        headers=headers
    )
    print_response(response, "Get Cart")
    
    # Get cart summary
    response = requests.get(
        f"{BASE_URL}/cart/summary",
        headers=headers
    )
    print_response(response, "Get Cart Summary")
    
    return response.status_code == 200


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 KYNORA API Test Suite")
    print("="*60)
    print(f"Testing API at: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    # Test health
    results["Health Check"] = test_health()
    
    # Test products
    results["Products"] = test_products()
    
    # Test categories
    results["Categories"] = test_categories()
    
    # Test auth and get token
    token = test_auth()
    results["Authentication"] = token is not None
    
    # Test cart (requires auth)
    results["Cart"] = test_cart(token)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    
    if all_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
