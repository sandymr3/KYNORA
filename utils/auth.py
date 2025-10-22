"""Authentication utilities for JWT token handling"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from config.settings import settings
from config.firebase import firebase_config
from models.user import TokenData, User

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token security
security = HTTPBearer()


class AuthUtils:
    """Authentication utility functions"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token
        
        Args:
            data: Data to encode in token
            expires_delta: Token expiration time
            
        Returns:
            str: Encoded JWT token
        """
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token
        
        Args:
            data: Data to encode in token
            
        Returns:
            str: Encoded refresh token
        """
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.jwt_secret_key, 
            algorithm=settings.jwt_algorithm
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> TokenData:
        """
        Verify and decode a JWT token
        
        Args:
            token: JWT token to verify
            
        Returns:
            TokenData: Decoded token data
            
        Raises:
            HTTPException: If token is invalid
        """
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = jwt.decode(
                token, 
                settings.jwt_secret_key, 
                algorithms=[settings.jwt_algorithm]
            )
            
            user_id: str = payload.get("sub")
            email: str = payload.get("email")
            role: str = payload.get("role")
            
            if user_id is None or email is None:
                raise credentials_exception
                
            token_data = TokenData(
                user_id=user_id,
                email=email,
                role=role,
                exp=payload.get("exp")
            )
            return token_data
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {str(e)}")
            raise credentials_exception
    
    @staticmethod
    def verify_firebase_token(id_token: str) -> Dict[str, Any]:
        """
        Verify a Firebase ID token
        
        Args:
            id_token: Firebase ID token
            
        Returns:
            dict: Decoded token claims
            
        Raises:
            HTTPException: If token is invalid
        """
        try:
            decoded_token = firebase_config.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Firebase token verification failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Firebase token"
            )
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password
        
        Args:
            password: Plain text password
            
        Returns:
            str: Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password
            
        Returns:
            bool: True if password matches
        """
        return pwd_context.verify(plain_password, hashed_password)


# Dependency functions for FastAPI
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """
    Get current user from JWT token
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        TokenData: Current user data
        
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = AuthUtils.verify_token(token)
    return token_data


async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Get current active user
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenData: Active user data
        
    Raises:
        HTTPException: If user is inactive
    """
    # Here you could check if user is active in database
    # For now, we'll just return the user
    return current_user


async def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Require admin role
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenData: Admin user data
        
    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role not in ['admin', 'manager']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[TokenData]:
    """
    Get current user from JWT token if provided (optional authentication)
    
    Args:
        credentials: Bearer token credentials (optional)
        
    Returns:
        Optional[TokenData]: Current user data or None
    """
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        token_data = AuthUtils.verify_token(token)
        return token_data
    except:
        return None


async def require_seller(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """
    Require seller role
    
    Args:
        current_user: Current user from token
        
    Returns:
        TokenData: Seller user data
        
    Raises:
        HTTPException: If user is not seller
    """
    if current_user.role not in ['seller', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seller access required"
        )
    return current_user


# Export commonly used functions
create_access_token = AuthUtils.create_access_token
create_refresh_token = AuthUtils.create_refresh_token
verify_token = AuthUtils.verify_token
hash_password = AuthUtils.hash_password
verify_password = AuthUtils.verify_password
verify_firebase_token = AuthUtils.verify_firebase_token
