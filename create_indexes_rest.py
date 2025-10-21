#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Auto-generated script to create Firestore indexes via REST API"""

import sys
import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configuration
PROJECT_ID = "kynora-ecommerce"
SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"

# Load credentials
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Refresh credentials
credentials.refresh(Request())
access_token = credentials.token

# Base URL
base_url = f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/collectionGroups"

# Headers
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Indexes to create
indexes = [
    {
        "collectionGroup": "products",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "category_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            }
        ]
    },
    {
        "collectionGroup": "products",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "is_featured",
                "order": "DESCENDING"
            },
            {
                "fieldPath": "created_at",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "products",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "seller_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            }
        ]
    },
    {
        "collectionGroup": "products",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "price",
                "order": "ASCENDING"
            }
        ]
    },
    {
        "collectionGroup": "orders",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "user_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "created_at",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "orders",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "created_at",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "reviews",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "product_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "created_at",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "reviews",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "product_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "verified_purchase",
                "order": "DESCENDING"
            },
            {
                "fieldPath": "rating",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "notifications",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "user_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "read",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "created_at",
                "order": "DESCENDING"
            }
        ]
    },
    {
        "collectionGroup": "categories",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "parent_id",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "display_order",
                "order": "ASCENDING"
            }
        ]
    },
    {
        "collectionGroup": "categories",
        "queryScope": "COLLECTION",
        "fields": [
            {
                "fieldPath": "status",
                "order": "ASCENDING"
            },
            {
                "fieldPath": "display_order",
                "order": "ASCENDING"
            }
        ]
    }
]

print("Creating Firestore indexes...")
print(f"Project: {PROJECT_ID}\n")

success_count = 0
failed_count = 0

for i, index_config in enumerate(indexes, 1):
    collection = index_config["collectionGroup"]
    fields = index_config["fields"]
    
    field_str = ", ".join([f"{f['fieldPath']} ({f.get('order', 'ASC')})" for f in fields])
    print(f"[{i}/{len(indexes)}] Creating: {collection} -> {field_str}")
    
    # Build index payload
    index_fields = []
    for field in fields:
        field_obj = {
            "fieldPath": field["fieldPath"]
        }
        
        if field.get("order") == "ASCENDING":
            field_obj["order"] = "ASCENDING"
        elif field.get("order") == "DESCENDING":
            field_obj["order"] = "DESCENDING"
        
        index_fields.append(field_obj)
    
    payload = {
        "queryScope": "COLLECTION",
        "fields": index_fields
    }
    
    # Create index
    url = f"{base_url}/{collection}/indexes"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"  ✅ Success")
            success_count += 1
        elif response.status_code == 409:
            print(f"  ⏭️  Already exists")
            success_count += 1
        else:
            print(f"  ❌ Failed: {response.status_code} - {response.text}")
            failed_count += 1
    except Exception as e:
        print(f"  ❌ Error: {e}")
        failed_count += 1

print(f"\n{'='*70}")
print(f"SUMMARY")
print(f"{'='*70}")
print(f"✅ Success: {success_count}")
print(f"❌ Failed: {failed_count}")
print(f"📊 Total: {len(indexes)}")
print(f"{'='*70}\n")

if failed_count == 0:
    print("All indexes created successfully!")
    print(f"Check status at: https://console.firebase.google.com/project/{PROJECT_ID}/firestore/indexes")
