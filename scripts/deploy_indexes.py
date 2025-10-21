#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Firestore Index Deployment Script
Deploys composite indexes defined in firestore.indexes.json to Firebase
"""

import sys
import os
import json
import subprocess
from pathlib import Path
import logging

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


class FirestoreIndexDeployer:
    """Deploy Firestore indexes from configuration file"""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        else:
            project_root = Path(project_root)
            
        self.project_root = project_root
        self.indexes_file = project_root / "firestore.indexes.json"
        self.service_account_file = project_root / "serviceAccountKey.json"
        
    def validate_files(self) -> bool:
        """Validate required files exist"""
        if not self.indexes_file.exists():
            logger.error(f"❌ Indexes file not found: {self.indexes_file}")
            return False
            
        if not self.service_account_file.exists():
            logger.error(f"❌ Service account key not found: {self.service_account_file}")
            return False
            
        return True
    
    def load_indexes(self) -> dict:
        """Load indexes from JSON file"""
        try:
            with open(self.indexes_file, 'r') as f:
                data = json.load(f)
            
            logger.info(f"✅ Loaded {len(data.get('indexes', []))} indexes from configuration")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in indexes file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to load indexes: {e}")
            raise
    
    def get_project_id(self) -> str:
        """Extract project ID from service account key"""
        try:
            with open(self.service_account_file, 'r') as f:
                service_account = json.load(f)
            
            project_id = service_account.get('project_id')
            if not project_id:
                raise ValueError("project_id not found in service account key")
                
            logger.info(f"📋 Project ID: {project_id}")
            return project_id
        except Exception as e:
            logger.error(f"❌ Failed to get project ID: {e}")
            raise
    
    def check_firebase_cli(self) -> bool:
        """Check if Firebase CLI is installed"""
        try:
            result = subprocess.run(
                ['firebase', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.strip()
                logger.info(f"✅ Firebase CLI installed: {version}")
                return True
            else:
                logger.error("❌ Firebase CLI not responding correctly")
                return False
                
        except FileNotFoundError:
            logger.error("❌ Firebase CLI not found")
            logger.info("📦 Install it with: npm install -g firebase-tools")
            return False
        except Exception as e:
            logger.error(f"❌ Error checking Firebase CLI: {e}")
            return False
    
    def deploy_indexes(self, project_id: str) -> bool:
        """Deploy indexes using Firebase CLI"""
        try:
            logger.info("🚀 Deploying Firestore indexes...")
            
            # Set environment variable for service account
            env = os.environ.copy()
            env['GOOGLE_APPLICATION_CREDENTIALS'] = str(self.service_account_file)
            
            # Run firebase deploy command
            result = subprocess.run(
                [
                    'firebase', 'deploy',
                    '--only', 'firestore:indexes',
                    '--project', project_id
                ],
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                env=env,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info("✅ Indexes deployed successfully!")
                logger.info(result.stdout)
                return True
            else:
                logger.error("❌ Index deployment failed!")
                logger.error(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Deployment timed out after 120 seconds")
            return False
        except Exception as e:
            logger.error(f"❌ Deployment error: {e}")
            return False
    
    def display_indexes_summary(self, indexes_data: dict):
        """Display summary of indexes to be deployed"""
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
    
    def run(self, dry_run: bool = False):
        """Main execution method"""
        try:
            logger.info("🔧 Starting Firestore index deployment...")
            
            # Validate files
            if not self.validate_files():
                return False
            
            # Load indexes
            indexes_data = self.load_indexes()
            
            # Display summary
            self.display_indexes_summary(indexes_data)
            
            # Get project ID
            project_id = self.get_project_id()
            
            if dry_run:
                logger.info("🔍 Dry run mode - skipping actual deployment")
                return True
            
            # Check Firebase CLI
            if not self.check_firebase_cli():
                logger.error("❌ Cannot proceed without Firebase CLI")
                return False
            
            # Deploy indexes
            success = self.deploy_indexes(project_id)
            
            if success:
                print("\n" + "="*60)
                print("✅ DEPLOYMENT SUCCESSFUL")
                print("="*60)
                print("Your Firestore indexes are being created.")
                print("This may take several minutes to complete.")
                print(f"\nCheck status at:")
                print(f"https://console.firebase.google.com/project/{project_id}/firestore/indexes")
                print("="*60 + "\n")
            else:
                print("\n" + "="*60)
                print("❌ DEPLOYMENT FAILED")
                print("="*60)
                print("Please check the error messages above.")
                print("="*60 + "\n")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Deploy Firestore indexes from firestore.indexes.json'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deployed without actually deploying'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        help='Path to project root directory (default: parent of script directory)'
    )
    
    args = parser.parse_args()
    
    try:
        deployer = FirestoreIndexDeployer(args.project_root)
        success = deployer.run(dry_run=args.dry_run)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
