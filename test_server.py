import requests
import json

def test_server():
    base_url = "http://localhost:8000"
    
    print("Testing FastAPI server...")
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except Exception as e:
        print(f"Health check failed: {e}")
    
    # Test docs endpoint
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"Docs endpoint: {response.status_code}")
        print(f"Content type: {response.headers.get('content-type')}")
    except Exception as e:
        print(f"Docs endpoint failed: {e}")
    
    # Test products endpoint
    try:
        response = requests.get(f"{base_url}/products")
        print(f"Products endpoint: {response.status_code}")
        if response.status_code == 200:
            print("Products endpoint working!")
        else:
            print(f"Products response: {response.text}")
    except Exception as e:
        print(f"Products endpoint failed: {e}")

if __name__ == "__main__":
    test_server()