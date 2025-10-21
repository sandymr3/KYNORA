#!/usr/bin/env python
"""Test imports for new routers"""

import sys
import traceback

try:
    print("Testing imports...")
    
    print("Importing reviews...")
    from routers import reviews
    print("✓ reviews imported successfully")
    
    print("Importing users...")
    from routers import users
    print("✓ users imported successfully")
    
    print("\nAll imports successful!")
    
except Exception as e:
    print(f"\n✗ Import error: {e}")
    traceback.print_exc()
    sys.exit(1)
