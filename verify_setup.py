#!/usr/bin/env python3
"""
KYNORA Backend - Setup Verification Script
Checks if all requirements are met for running the application
"""

import sys
import os
from pathlib import Path
import importlib.util


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_python_version():
    """Check if Python version is 3.11+"""
    print("\n🐍 Checking Python Version...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"   ✅ Python {version.major}.{version.minor}.{version.micro} (OK)")
        return True
    else:
        print(f"   ❌ Python {version.major}.{version.minor}.{version.micro} (Need 3.11+)")
        return False


def check_package(package_name, import_name=None):
    """Check if a Python package is installed"""
    if import_name is None:
        import_name = package_name.replace("-", "_")
    
    spec = importlib.util.find_spec(import_name)
    if spec is not None:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, "__version__", "unknown")
            print(f"   ✅ {package_name:30} {version}")
            return True
        except Exception:
            print(f"   ⚠️  {package_name:30} (installed but can't load)")
            return False
    else:
        print(f"   ❌ {package_name:30} (not installed)")
        return False


def check_required_packages():
    """Check if all required packages are installed"""
    print("\n📦 Checking Required Packages...")
    
    required_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("firebase-admin", "firebase_admin"),
        ("google-cloud-firestore", "google.cloud.firestore"),
        ("google-auth", "google.auth"),
        ("pydantic", "pydantic"),
        ("python-dotenv", "dotenv"),
        ("python-jose", "jose"),
        ("passlib", "passlib"),
        ("cloudinary", "cloudinary"),
        ("httpx", "httpx"),
        ("aiohttp", "aiohttp"),
        ("requests", "requests"),
        ("loguru", "loguru"),
    ]
    
    results = []
    for package_name, import_name in required_packages:
        results.append(check_package(package_name, import_name))
    
    return all(results)


def check_file_exists(file_path, name):
    """Check if a required file exists"""
    if os.path.exists(file_path):
        print(f"   ✅ {name}")
        return True
    else:
        print(f"   ❌ {name} (not found)")
        return False


def check_required_files():
    """Check if required configuration files exist"""
    print("\n📄 Checking Required Files...")
    
    files = [
        ("serviceAccountKey.json", "Firebase Service Account Key"),
        (".env", "Environment Variables File"),
        ("requirements.txt", "Requirements File"),
        ("main.py", "Main Application File"),
        ("firestore.indexes.json", "Firestore Indexes Definition"),
    ]
    
    results = []
    for file_path, name in files:
        results.append(check_file_exists(file_path, name))
    
    return all(results)


def check_env_variables():
    """Check if required environment variables are set"""
    print("\n🔧 Checking Environment Variables...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        "FIREBASE_PROJECT_ID",
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
        "JWT_SECRET_KEY",
    ]
    
    results = []
    for var in required_vars:
        value = os.getenv(var)
        if value and value != f"your_{var.lower()}":
            print(f"   ✅ {var:30} (set)")
            results.append(True)
        else:
            print(f"   ❌ {var:30} (not set or using default)")
            results.append(False)
    
    return all(results)


def check_firebase_connection():
    """Check if Firebase connection can be established"""
    print("\n🔥 Checking Firebase Connection...")
    
    try:
        from core.database import initialize_firebase
        db = initialize_firebase()
        if db:
            print("   ✅ Firebase connection successful")
            return True
        else:
            print("   ❌ Firebase connection failed")
            return False
    except Exception as e:
        print(f"   ❌ Firebase connection error: {str(e)[:50]}...")
        return False


def check_port_available(port=8000):
    """Check if the default port is available"""
    print(f"\n🔌 Checking Port {port}...")
    
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"   ⚠️  Port {port} is already in use")
            print(f"      Use: uvicorn main:app --port {port + 1}")
            return False
        else:
            print(f"   ✅ Port {port} is available")
            return True
    except Exception as e:
        print(f"   ⚠️  Could not check port: {e}")
        return True


def print_summary(checks):
    """Print summary of all checks"""
    print_header("VERIFICATION SUMMARY")
    
    total = len(checks)
    passed = sum(checks.values())
    failed = total - passed
    
    print(f"\n   Total Checks: {total}")
    print(f"   ✅ Passed: {passed}")
    print(f"   ❌ Failed: {failed}")
    
    if failed == 0:
        print("\n   🎉 All checks passed! You're ready to run the application.")
        print("\n   Next steps:")
        print("   1. Run: uvicorn main:app --reload")
        print("   2. Open: http://localhost:8000/docs")
        return True
    else:
        print("\n   ⚠️  Some checks failed. Please fix the issues above.")
        print("\n   Recommended actions:")
        if not checks.get("packages"):
            print("   - Install packages: pip install -r requirements.txt")
        if not checks.get("files"):
            print("   - Check required files (serviceAccountKey.json, .env)")
        if not checks.get("env_vars"):
            print("   - Configure .env file with your credentials")
        if not checks.get("firebase"):
            print("   - Verify Firebase configuration")
        return False


def main():
    """Main verification function"""
    print_header("KYNORA Backend Setup Verification")
    print("This script checks if your environment is properly configured.\n")
    
    checks = {}
    
    # Run all checks
    checks["python"] = check_python_version()
    checks["packages"] = check_required_packages()
    checks["files"] = check_required_files()
    checks["env_vars"] = check_env_variables()
    checks["firebase"] = check_firebase_connection()
    checks["port"] = check_port_available()
    
    # Print summary
    success = print_summary(checks)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
