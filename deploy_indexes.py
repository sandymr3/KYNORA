#!/usr/bin/env python3
"""
Deploy Firestore indexes from firestore.indexes.json
"""
import json
import subprocess
import sys

def deploy_indexes():
    """Deploy Firestore indexes using Firebase CLI"""
    try:
        # Check if Firebase CLI is installed
        result = subprocess.run(['firebase', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"Firebase CLI version: {result.stdout.strip()}")
        
        # Deploy indexes
        print("Deploying Firestore indexes...")
        result = subprocess.run(['firebase', 'deploy', '--only', 'firestore:indexes'], 
                              capture_output=True, text=True, check=True)
        
        print("✅ Indexes deployed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error deploying indexes: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Firebase CLI not found. Please install it first:")
        print("npm install -g firebase-tools")
        sys.exit(1)

if __name__ == "__main__":
    deploy_indexes()