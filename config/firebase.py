"""Firebase Configuration and Initialization"""

import firebase_admin
from firebase_admin import credentials, firestore, auth
from typing import Optional
import os
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class FirebaseConfig:
    """Firebase configuration and initialization class"""
    
    _instance: Optional['FirebaseConfig'] = None
    _initialized: bool = False
    _db: Optional[firestore.Client] = None
    _auth: Optional[auth.Client] = None
    
    def __new__(cls):
        """Singleton pattern for Firebase configuration"""
        if cls._instance is None:
            cls._instance = super(FirebaseConfig, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Firebase configuration"""
        if not self._initialized:
            self._initialize_firebase()
            self._initialized = True
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if we should use emulator
            if settings.firestore_emulator_host and settings.is_development():
                os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host
                logger.info(f"Using Firestore Emulator at {settings.firestore_emulator_host}")
            
            # Check if already initialized
            if not firebase_admin._apps:
                # Try to load from service account file first
                service_account_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'serviceAccountKey.json'
                )
                
                if os.path.exists(service_account_path):
                    # Use service account file
                    cred = credentials.Certificate(service_account_path)
                    logger.info("Using serviceAccountKey.json for Firebase authentication")
                else:
                    # Use environment variables
                    firebase_creds = settings.get_firebase_credentials()
                    cred = credentials.Certificate(firebase_creds)
                    logger.info("Using environment variables for Firebase authentication")
                
                # Initialize Firebase app
                firebase_admin.initialize_app(cred, {
                    'projectId': settings.firebase_project_id,
                })
                
                logger.info(f"Firebase initialized successfully for project: {settings.firebase_project_id}")
            else:
                logger.info("Firebase already initialized")
            
            # Initialize Firestore client
            self._db = firestore.client()
            
            # Initialize Auth client
            self._auth = auth
            
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {str(e)}")
            raise Exception(f"Firebase initialization failed: {str(e)}")
    
    @property
    def db(self) -> firestore.Client:
        """Get Firestore database client"""
        if self._db is None:
            raise Exception("Firebase not initialized. Call FirebaseConfig() first.")
        return self._db
    
    @property
    def auth_client(self) -> auth:
        """Get Firebase Auth client"""
        if self._auth is None:
            raise Exception("Firebase not initialized. Call FirebaseConfig() first.")
        return self._auth
    
    def verify_id_token(self, id_token: str) -> dict:
        """
        Verify a Firebase ID token
        
        Args:
            id_token: The Firebase ID token to verify
            
        Returns:
            dict: Decoded token claims
            
        Raises:
            Exception: If token is invalid
        """
        try:
            decoded_token = self._auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Failed to verify ID token: {str(e)}")
            raise Exception(f"Invalid token: {str(e)}")
    
    def create_custom_token(self, uid: str, additional_claims: dict = None) -> bytes:
        """
        Create a custom Firebase token
        
        Args:
            uid: User ID
            additional_claims: Additional claims to include in token
            
        Returns:
            bytes: Custom token
        """
        try:
            return self._auth.create_custom_token(uid, additional_claims)
        except Exception as e:
            logger.error(f"Failed to create custom token: {str(e)}")
            raise Exception(f"Failed to create custom token: {str(e)}")
    
    def get_user(self, uid: str) -> auth.UserRecord:
        """
        Get Firebase user by UID
        
        Args:
            uid: User ID
            
        Returns:
            UserRecord: Firebase user record
        """
        try:
            return self._auth.get_user(uid)
        except Exception as e:
            logger.error(f"Failed to get user: {str(e)}")
            raise Exception(f"User not found: {str(e)}")
    
    def create_user(self, email: str, password: str, **kwargs) -> auth.UserRecord:
        """
        Create a new Firebase user
        
        Args:
            email: User email
            password: User password
            **kwargs: Additional user properties
            
        Returns:
            UserRecord: Created user record
        """
        try:
            return self._auth.create_user(
                email=email,
                password=password,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Failed to create user: {str(e)}")
            raise Exception(f"Failed to create user: {str(e)}")
    
    def update_user(self, uid: str, **kwargs) -> auth.UserRecord:
        """
        Update Firebase user
        
        Args:
            uid: User ID
            **kwargs: Properties to update
            
        Returns:
            UserRecord: Updated user record
        """
        try:
            return self._auth.update_user(uid, **kwargs)
        except Exception as e:
            logger.error(f"Failed to update user: {str(e)}")
            raise Exception(f"Failed to update user: {str(e)}")
    
    def delete_user(self, uid: str):
        """
        Delete Firebase user
        
        Args:
            uid: User ID
        """
        try:
            self._auth.delete_user(uid)
        except Exception as e:
            logger.error(f"Failed to delete user: {str(e)}")
            raise Exception(f"Failed to delete user: {str(e)}")
    
    def set_custom_user_claims(self, uid: str, custom_claims: dict):
        """
        Set custom claims for a user
        
        Args:
            uid: User ID
            custom_claims: Custom claims dictionary
        """
        try:
            self._auth.set_custom_user_claims(uid, custom_claims)
        except Exception as e:
            logger.error(f"Failed to set custom claims: {str(e)}")
            raise Exception(f"Failed to set custom claims: {str(e)}")


# Global Firebase instance
firebase_config = FirebaseConfig()

# Export commonly used objects
db = firebase_config.db
auth_client = firebase_config.auth_client
