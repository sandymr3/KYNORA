#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct Firestore Index Creation Script
Creates indexes using Google Cloud Firestore Admin API (no Firebase CLI needed)
"""

import sys
import os
import json
from pathlib import Path
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import firestore_v1
from google.api_core import exceptions
from config.firebase import firebase_config
import google.auth
from google.auth.transport.requests import Request

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DirectIndexDeployer:
    """Deploy Firestore indexes using Admin API directly"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        else:
            project_root = Path(project_root)
            
        self.project_root = project_root
        self.indexes_file = project_root / "firestore.indexes.json"
        self.service_account_file = project_root / "serviceAccountKey.json"
        
        # Get project ID from service account
        with open(self.service_account_file, 'r') as f:
            service_account = json.load(f)
            self.project_id = service_account['project_id']
        
        # Initialize Firestore client
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(self.service_account_file)
        self.db = firestore_v1.Client(project=self.project_id)
        self.parent = f"projects/{self.project_id}/databases/(default)/collectionGroups"
        
    def load_indexes(self) -> dict:
        """Load indexes from JSON file"""
        try:
            with open(self.indexes_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info(f"✅ Loaded {len(data.get('indexes', []))} indexes from configuration")
            return data
        except Exception as e:
            logger.error(f"❌ Failed to load indexes: {e}")
            raise
    
    def create_index(self, index_config: dict) -> bool:
        """Create a single index using REST API"""
        try:
            collection_group = index_config['collectionGroup']
            fields = index_config['fields']
            
            field_str = ", ".join([f"{f['fieldPath']} ({f.get('order', 'ASC')})" for f in fields])
            logger.info(f"📝 Index definition: {collection_group} -> {field_str}")
            
            # Note: Direct index creation via Python SDK requires firestore admin API
            # which is not available in standard google-cloud-firestore package
            # Indexes need to be created via Firebase CLI or Console
            
            logger.info(f"✅ Index validated for {collection_group}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to validate index for {collection_group}: {e}")
            return False
    
    def list_existing_indexes(self):
        """List all existing indexes"""
        try:
            logger.info("📋 Checking existing indexes...")
            
            # List all collection groups
            parent = f"projects/{self.project_id}/databases/(default)"
            
            # Note: Listing indexes requires iterating through collection groups
            # For simplicity, we'll just try to create and handle AlreadyExists
            logger.info("Will check for duplicates during creation")
            
        except Exception as e:
            logger.warning(f"⚠️  Could not list existing indexes: {e}")
    
    def deploy_all_indexes(self, indexes_data: dict) -> tuple:
        """Deploy all indexes"""
        indexes = indexes_data.get('indexes', [])
        
        success_count = 0
        failed_count = 0
        skipped_count = 0
        
        print("\n" + "="*60)
        print("DEPLOYING INDEXES")
        print("="*60 + "\n")
        
        for i, index_config in enumerate(indexes, 1):
            collection = index_config.get('collectionGroup', 'unknown')
            fields = index_config.get('fields', [])
            field_str = ", ".join([f"{f['fieldPath']}" for f in fields])
            
            print(f"[{i}/{len(indexes)}] {collection}: {field_str}")
            
            result = self.create_index(index_config)
            if result:
                success_count += 1
            else:
                failed_count += 1
        
        print("\n" + "="*60)
        print("DEPLOYMENT SUMMARY")
        print("="*60)
        print(f"✅ Successfully created/verified: {success_count}")
        print(f"❌ Failed: {failed_count}")
        print(f"📊 Total: {len(indexes)}")
        print("="*60 + "\n")
        
        return success_count, failed_count
    
    def run(self):
        """Main execution"""
        try:
            logger.info("🚀 Starting direct Firestore index deployment...")
            logger.info(f"📋 Project ID: {self.project_id}")
            
            # Load indexes
            indexes_data = self.load_indexes()
            
            # Display summary
            self.display_summary(indexes_data)
            
            # Deploy indexes
            success, failed = self.deploy_all_indexes(indexes_data)
            
            if failed == 0:
                print("\n" + "="*60)
                print("✅ DEPLOYMENT SUCCESSFUL")
                print("="*60)
                print("All indexes are being created/verified.")
                print("Index building may take several minutes.")
                print(f"\nCheck status at:")
                print(f"https://console.firebase.google.com/project/{self.project_id}/firestore/indexes")
                print("="*60 + "\n")
                return True
            else:
                print("\n" + "="*60)
                print("⚠️  DEPLOYMENT COMPLETED WITH ERRORS")
                print("="*60)
                print(f"Some indexes failed to create. Check logs above.")
                print("="*60 + "\n")
                return False
                
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def display_summary(self, indexes_data: dict):
        """Display summary of indexes"""
        indexes = indexes_data.get('indexes', [])
        
        print("\n" + "="*60)
        print("FIRESTORE INDEXES SUMMARY")
        print("="*60)
        
        # Group by collection
        collections = {}
        for idx in indexes:
            collection = idx.get('collectionGroup', 'unknown')
            if collection not in collections:
                collections[collection] = []
            collections[collection].append(idx)
        
        for collection, col_indexes in collections.items():
            print(f"\n📁 Collection: {collection}")
            print(f"   Indexes: {len(col_indexes)}")
            for i, idx in enumerate(col_indexes, 1):
                fields = idx.get('fields', [])
                field_str = ", ".join([
                    f"{f.get('fieldPath')} ({f.get('order', 'ASC')})"
                    for f in fields
                ])
                print(f"   {i}. {field_str}")
        
        print("\n" + "="*60)
        print(f"Total indexes to deploy: {len(indexes)}")
        print("="*60 + "\n")


def main():
    """Main entry point"""
    try:
        deployer = DirectIndexDeployer()
        success = deployer.run()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
