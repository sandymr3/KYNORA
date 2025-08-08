"""
Test script for Firebase Authentication with FastAPI
"""
import requests
import json

def test_auth_endpoints():
    """Test authentication endpoints"""
    base_url = "http://localhost:8000"
    
    print("🔐 Testing Firebase Authentication Integration")
    print("=" * 50)
    
    # Test without authentication (should fail)
    print("\n1. Testing endpoint without authentication...")
    try:
        response = requests.get(f"{base_url}/auth/me")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with invalid token (should fail)
    print("\n2. Testing with invalid token...")
    try:
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = requests.get(f"{base_url}/auth/me", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Instructions for testing with real token
    print("\n3. To test with real Firebase token:")
    print("   - Get a Firebase ID token from your frontend")
    print("   - Use it in the Authorization header: 'Bearer <your_token>'")
    print("   - Example:")
    print("     curl -H 'Authorization: Bearer <your_firebase_token>' http://localhost:8000/auth/me")
    
    # Test public endpoints (should work)
    print("\n4. Testing public endpoints...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check status: {response.status_code}")
        
        response = requests.get(f"{base_url}/products")
        print(f"Products endpoint status: {response.status_code}")
        
        response = requests.get(f"{base_url}/categories")
        print(f"Categories endpoint status: {response.status_code}")
    except Exception as e:
        print(f"Error testing public endpoints: {e}")

if __name__ == "__main__":
    test_auth_endpoints()