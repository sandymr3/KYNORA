#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Firebase Index Creation Commands
Creates manual commands or REST API calls to create indexes
"""

import sys
import os
import json
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def load_indexes():
    """Load indexes from JSON file"""
    script_dir = Path(__file__).parent.parent
    indexes_file = script_dir / "firestore.indexes.json"
    
    with open(indexes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data


def generate_console_instructions(indexes_data):
    """Generate instructions for Firebase Console"""
    indexes = indexes_data.get('indexes', [])
    
    print("\n" + "="*70)
    print("FIREBASE CONSOLE - MANUAL INDEX CREATION INSTRUCTIONS")
    print("="*70)
    print("\n1. Go to: https://console.firebase.google.com")
    print("2. Select your project: kynora-ecommerce")
    print("3. Navigate to: Firestore Database → Indexes tab")
    print("4. Click 'Add Index' button for each index below:\n")
    
    for i, idx in enumerate(indexes, 1):
        collection = idx.get('collectionGroup', 'unknown')
        fields = idx.get('fields', [])
        
        print(f"\n{'─'*70}")
        print(f"INDEX #{i}: {collection}")
        print(f"{'─'*70}")
        print(f"Collection ID: {collection}")
        print(f"Query scope: Collection")
        print(f"Fields to index:")
        
        for j, field in enumerate(fields, 1):
            field_path = field.get('fieldPath')
            order = field.get('order', 'ASCENDING')
            print(f"  {j}. Field path: {field_path}")
            print(f"     Order: {order}")
        
        print(f"\nThen click 'Create'")
    
    print(f"\n{'='*70}")
    print(f"Total indexes to create: {len(indexes)}")
    print(f"{'='*70}\n")


def generate_rest_api_script(indexes_data):
    """Generate Python script using REST API"""
    script_dir = Path(__file__).parent.parent
    service_account_file = script_dir / "serviceAccountKey.json"
    
    with open(service_account_file, 'r') as f:
        service_account = json.load(f)
        project_id = service_account['project_id']
    
    indexes = indexes_data.get('indexes', [])
    
    print("\n" + "="*70)
    print("PYTHON REST API SCRIPT")
    print("="*70)
    print("\nSave this as 'create_indexes_rest.py' and run it:\n")
    
    script_content = f'''#!/usr/bin/env python3
"""Auto-generated script to create Firestore indexes via REST API"""

import requests
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request

# Configuration
PROJECT_ID = "{project_id}"
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
base_url = f"https://firestore.googleapis.com/v1/projects/{{PROJECT_ID}}/databases/(default)/collectionGroups"

# Headers
headers = {{
    "Authorization": f"Bearer {{access_token}}",
    "Content-Type": "application/json"
}}

# Indexes to create
indexes = {json.dumps(indexes, indent=4)}

print("Creating Firestore indexes...")
print(f"Project: {{PROJECT_ID}}\\n")

success_count = 0
failed_count = 0

for i, index_config in enumerate(indexes, 1):
    collection = index_config["collectionGroup"]
    fields = index_config["fields"]
    
    field_str = ", ".join([f"{{f['fieldPath']}} ({{f.get('order', 'ASC')}})" for f in fields])
    print(f"[{{i}}/{{len(indexes)}}] Creating: {{collection}} -> {{field_str}}")
    
    # Build index payload
    index_fields = []
    for field in fields:
        field_obj = {{
            "fieldPath": field["fieldPath"]
        }}
        
        if field.get("order") == "ASCENDING":
            field_obj["order"] = "ASCENDING"
        elif field.get("order") == "DESCENDING":
            field_obj["order"] = "DESCENDING"
        
        index_fields.append(field_obj)
    
    payload = {{
        "queryScope": "COLLECTION",
        "fields": index_fields
    }}
    
    # Create index
    url = f"{{base_url}}/{{collection}}/indexes"
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code in [200, 201]:
            print(f"  ✅ Success")
            success_count += 1
        elif response.status_code == 409:
            print(f"  ⏭️  Already exists")
            success_count += 1
        else:
            print(f"  ❌ Failed: {{response.status_code}} - {{response.text}}")
            failed_count += 1
    except Exception as e:
        print(f"  ❌ Error: {{e}}")
        failed_count += 1

print(f"\\n{{'='*70}}")
print(f"SUMMARY")
print(f"{{'='*70}}")
print(f"✅ Success: {{success_count}}")
print(f"❌ Failed: {{failed_count}}")
print(f"📊 Total: {{len(indexes)}}")
print(f"{{'='*70}}\\n")

if failed_count == 0:
    print("All indexes created successfully!")
    print(f"Check status at: https://console.firebase.google.com/project/{{PROJECT_ID}}/firestore/indexes")
'''
    
    print(script_content)
    
    # Save to file
    output_file = script_dir / "create_indexes_rest.py"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"\n{'='*70}")
    print(f"✅ Script saved to: {output_file}")
    print(f"{'='*70}")
    print(f"\nTo run: python create_indexes_rest.py")
    print(f"{'='*70}\n")


def main():
    """Main entry point"""
    try:
        print("\n🔧 Firestore Index Creation Helper")
        print("="*70)
        
        # Load indexes
        indexes_data = load_indexes()
        print(f"\n✅ Loaded {len(indexes_data.get('indexes', []))} indexes")
        
        # Generate REST API script
        generate_rest_api_script(indexes_data)
        
        # Generate console instructions
        generate_console_instructions(indexes_data)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
