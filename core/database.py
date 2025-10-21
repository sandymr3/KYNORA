"""
Database initialization and connection management
"""
import firebase_admin
from firebase_admin import credentials, firestore, auth
import logging
from .config import FIREBASE_CREDENTIALS_PATH, FIREBASE_PROJECT_ID
import os

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
            # Try to initialize with service account
            if os.path.exists(FIREBASE_CREDENTIALS_PATH):
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_PATH)
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

def get_auth():
    """Get Firebase Auth instance"""
    return auth
