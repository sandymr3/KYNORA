#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Testing Pydantic model imports...")

try:
    from models.base import BaseDocument, BaseResponse
    print("✅ BaseDocument and BaseResponse imported successfully")
except Exception as e:
    print(f"❌ ERROR importing base models: {e}")
    sys.exit(1)

try:
    from models.user import User, UserCreate
    print("✅ User models imported successfully")
except Exception as e:
    print(f"❌ ERROR importing user models: {e}")
    sys.exit(1)

try:
    from models.category import Category
    print("✅ Category models imported successfully")
except Exception as e:
    print(f"❌ ERROR importing category models: {e}")
    sys.exit(1)

print("🎉 All models imported successfully! Pydantic issues resolved.")
