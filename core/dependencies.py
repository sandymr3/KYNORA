"""
Shared dependencies for FastAPI endpoints
"""
from fastapi import HTTPException, Header, Depends, status, Request
from typing import Optional, Dict
from firebase_admin import auth
from .database import get_db, get_auth
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger('auth')

async def get_current_user(request: Request) -> Optional[Dict]:
    """
    Firebase Authentication dependency for centralized authentication.
    
    This function provides:
    - Firebase ID token verification using firebase-admin SDK
    - Automatic user profile creation for new users
    - Role-based access control with custom claims support
    - Proper error handling with meaningful messages
    
    Usage:
    - Protected endpoints use: Depends(require_authenticated_user)
    - Frontend sends: Authorization: Bearer <firebase_id_token>
    - Token is verified against Firebase Auth service
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        return None
    
    if not authorization.startswith("Bearer "):
        logger.warning(f"Invalid authorization format: {authorization[:20]}...")
        return None
    
    token = authorization.split(" ", 1)[1]  # Use split with maxsplit=1 to handle tokens with spaces
    
    if not token or len(token) < 10:
        logger.warning("Invalid or too short authentication token")
        return None
    
    try:
        # Verify the Firebase ID token with enhanced validation
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Log successful token verification
        auth_logger.debug(f"Firebase token verified successfully for UID: {uid}")
        
        # Get user data from Firestore by UID
        db = get_db()
        if not db:
            # Return basic user info if database not available
            return {
                'id': uid,
                'uid': uid,
                'email': email,
                'name': decoded_token.get('name', ''),
                'role': decoded_token.get('role', 'customer'),
                'email_verified': decoded_token.get('email_verified', False),
                'phone': decoded_token.get('phone_number', ''),
                'photo_url': decoded_token.get('picture', '')
            }
        
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            # Check if user exists by email first (for migration scenarios)
            if email:
                existing_user_query = db.collection('users').where('email', '==', email).limit(1).get()
                
                if existing_user_query:
                    # User exists with this email, migrate to new UID
                    existing_user_doc = existing_user_query[0]
                    user_data = existing_user_doc.to_dict()
                    
                    # Update the existing user document with the new UID
                    user_data['uid'] = uid
                    user_data['updatedAt'] = datetime.now()
                    user_data['lastLoginAt'] = datetime.now()
                    
                    db.collection('users').document(uid).set(user_data)
                    
                    # Delete the old document if it has a different ID
                    if existing_user_doc.id != uid:
                        db.collection('users').document(existing_user_doc.id).delete()
                    
                    logger.info(f"Migrated existing user {email} to UID: {uid}")
                else:
                    # Create new user with default customer role
                    user_data = {
                        'uid': uid,
                        'email': email,
                        'displayName': decoded_token.get('name', decoded_token.get('firebase', {}).get('identities', {}).get('email', [''])[0].split('@')[0] if decoded_token.get('firebase', {}).get('identities', {}).get('email') else ''),
                        'photoURL': decoded_token.get('picture', ''),
                        'role': decoded_token.get('role', 'customer'),  # Support custom claims for role
                        'phone': decoded_token.get('phone_number', ''),
                        'address': {},
                        'preferences': {
                            'currency': 'USD',
                            'language': 'en',
                            'notifications': {
                                'email': True,
                                'sms': False,
                                'push': True
                            }
                        },
                        'createdAt': datetime.now(),
                        'updatedAt': datetime.now(),
                        'isActive': True,
                        'lastLoginAt': datetime.now(),
                        'emailVerified': decoded_token.get('email_verified', False)
                    }
                    
                    # Create user document in Firestore
                    db.collection('users').document(uid).set(user_data)
                    logger.info(f"Created new user profile for UID: {uid}, Email: {email}")
            else:
                logger.warning(f"User profile not found and email not available for auto-creation: {uid}")
                return None
        else:
            user_data = user_doc.to_dict()
            
            # Update last login time asynchronously (don't wait for it)
            try:
                db.collection('users').document(uid).update({
                    'lastLoginAt': datetime.now()
                })
            except Exception as update_error:
                # Log but don't fail authentication for login time update errors
                logger.warning(f"Failed to update last login time for {uid}: {update_error}")
        
        # Check if user account is active
        if not user_data.get('isActive', True):
            logger.warning(f"Deactivated user access attempt: {uid} ({email})")
            return None
        
        # Support custom claims for enhanced role management
        user_role = user_data.get('role', 'customer')
        if 'role' in decoded_token:  # Custom claim takes precedence
            user_role = decoded_token['role']
            # Update user role in Firestore if it changed
            if user_data.get('role') != user_role:
                db.collection('users').document(uid).update({'role': user_role})
        
        # Return user info in the format expected by the application
        user_info = {
            "id": uid,
            "uid": uid,
            "email": user_data.get('email', email),
            "name": user_data.get('displayName', ''),
            "displayName": user_data.get('displayName', ''),
            "role": user_role,
            "email_verified": user_data.get('emailVerified', False),
            "phone": user_data.get('phone', ''),
            "photo_url": user_data.get('photoURL', ''),
            "address": user_data.get('address', {}),
            "preferences": user_data.get('preferences', {}),
            "status": user_data.get('status', 'active'),
            "created_at": user_data.get('createdAt'),
            "updated_at": user_data.get('updatedAt')
        }
        
        # Log successful authentication
        auth_logger.info(f"User authenticated successfully: {uid} ({email}) with role: {user_role}")
        
        return user_info
        
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Invalid Firebase token: {str(e)}")
        return None
    except auth.ExpiredIdTokenError as e:
        logger.warning(f"Expired Firebase token: {str(e)}")
        return None
    except auth.RevokedIdTokenError as e:
        logger.warning(f"Revoked Firebase token: {str(e)}")
        return None
    except auth.CertificateFetchError as e:
        logger.error(f"Firebase certificate fetch error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in Firebase authentication: {str(e)}", exc_info=True)
        return None

async def require_authenticated_user(current_user: Optional[Dict] = Depends(get_current_user)) -> Dict:
    """Require authenticated user for protected endpoints"""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return current_user

async def require_admin(current_user: Dict = Depends(require_authenticated_user)) -> Dict:
    """Require admin role for admin endpoints"""
    if current_user.get('role') != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def require_seller(current_user: Dict = Depends(require_authenticated_user)) -> Dict:
    """Require seller role for seller endpoints"""
    if current_user.get('role') not in ['seller', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller access required"
        )
    return current_user
