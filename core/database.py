"""
Database initialization and connection management
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
import logging
from .config import (
    FIREBASE_CREDENTIALS_PATH,
    FIREBASE_PROJECT_ID,
    FIREBASE_SERVICE_ACCOUNT,
    DEFAULT_FIREBASE_CREDENTIALS_PATH,
)
import os
import json
import tempfile

logger = logging.getLogger(__name__)

# Global Firestore client instance
db = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global db
    
    try:
        # Check if already initialized
        app = firebase_admin.get_app()
        logger.info("Firebase already initialized")
        db = firestore.client()
        return db
    except ValueError:
        try:
            # If a single JSON is provided via env var (useful for Railway), write it to a temp file
            cred_path = FIREBASE_CREDENTIALS_PATH
            if FIREBASE_SERVICE_ACCOUNT:
                try:
                    # FIREBASE_SERVICE_ACCOUNT may contain escaped newlines; unescape them
                    sa_content = FIREBASE_SERVICE_ACCOUNT
                    # If it's a JSON string, ensure it's valid JSON
                    if isinstance(sa_content, str):
                        # Replace escaped newlines if present
                        sa_content = sa_content.replace('\\n', '\n')

                    # Write to a temp file under /tmp or system temp dir
                    fd, temp_path = tempfile.mkstemp(prefix="firebase_sa_", suffix=".json")
                    with os.fdopen(fd, 'w', encoding='utf-8') as f:
                        if isinstance(sa_content, (dict, list)):
                            json.dump(sa_content, f)
                        else:
                            f.write(sa_content)
                    cred_path = temp_path
                    logger.info("Wrote FIREBASE_SERVICE_ACCOUNT to temporary credentials file")
                except Exception as e:
                    logger.warning(f"Failed to write FIREBASE_SERVICE_ACCOUNT to disk: {e}")

            # Try to initialize with service account if file exists
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': FIREBASE_PROJECT_ID
                })
                logger.info(f"Firebase initialized with service account for project: {FIREBASE_PROJECT_ID}")
            else:
                # Use default credentials (for Cloud Run, App Engine, etc.)
                firebase_admin.initialize_app()
                logger.info("Firebase initialized with default credentials")
            
            db = firestore.client()
            return db
        except Exception as e:
            logger.warning(f"Could not initialize Firebase: {e}")
            logger.warning("Running in development mode without database")
            return None

def get_db():
    """Get Firestore database instance"""
    global db
    if db is None:
        db = initialize_firebase()
    return db

# Alias for compatibility
get_firestore_client = get_db

def get_auth():
    """Get Firebase Auth instance"""
    return auth
