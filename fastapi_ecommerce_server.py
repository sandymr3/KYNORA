"""
FastAPI E-commerce Server with Optimized Authentication
Converts FirestoreEcommerceDB class methods into RESTful API endpoints

Features:
- Clean Swagger UI without redundant authorization parameters
- Centralized authentication through global "Authorize" button
- Firebase ID token verification with role-based access control
- Clear distinction between public (🌐) and protected (🔒) endpoints

Authentication:
- Public endpoints: No authentication required
- Protected endpoints: Use global "Authorize" button in Swagger UI
- Set token once: Bearer <your-firebase-token>
- Token automatically applied to all protected endpoints

Run with: python start_server.py (default port 8001)
API Documentation: http://localhost:8001/docs
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
import logging
import os
import dotenv
import asyncio
from functools import wraps
import hashlib
import json
dotenv.load_dotenv()  # Load environment variables from .env file
# Import your existing Firestore class
from firestore_ecommerce_db import FirestoreEcommerceDB
import firebase_admin
from firebase_admin import credentials, auth, firestore
import json

# Get Firebase configuration from environment variables
FIRESTORE_PROJECT_ID = os.getenv("FIRESTORE_PROJECT_ID")

# Initialize Firebase Admin SDK using environment variables
try:
    # Check if Firebase is already initialized
    firebase_admin.get_app()
except ValueError:
    # Create service account credentials from environment variables
    firebase_credentials = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("FIREBASE_PRIVATE_KEY") else None,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN")
    }
    
    # Initialize Firebase if not already done
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred, {
        'projectId': FIRESTORE_PROJECT_ID
    })

# Get Firestore client
firestore_client = firestore.client()



# ==================== ENHANCED LOGGING CONFIGURATION ====================

import sys
from logging.handlers import RotatingFileHandler
import traceback
import uuid

# Configure enhanced logging
def setup_logging():
    """Setup comprehensive logging configuration"""
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler for development
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for production logs
    try:
        file_handler = RotatingFileHandler(
            'logs/ecommerce_api.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    except (OSError, IOError):
        # If logs directory doesn't exist or can't write, continue without file logging
        pass
    
    # Error file handler for errors only
    try:
        error_handler = RotatingFileHandler(
            'logs/ecommerce_errors.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)
    except (OSError, IOError):
        # If logs directory doesn't exist or can't write, continue without error file logging
        pass
    
    return root_logger

# Setup logging
logger = setup_logging()

# Create specialized loggers
auth_logger = logging.getLogger('auth')
db_logger = logging.getLogger('database')
api_logger = logging.getLogger('api')
performance_logger = logging.getLogger('performance')

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce API",
    description="RESTful API for Firestore-based e-commerce platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend applications with authentication support
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "http://localhost:8001",  # React development
        "http://localhost:5173",  # Vite development
        "https://kynora.onrender.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "*",
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With"
    ],
    expose_headers=["X-Request-ID", "X-Process-Time"]
)

# ==================== ENHANCED REQUEST/RESPONSE LOGGING MIDDLEWARE ====================

@app.middleware("http")
async def enhanced_logging_middleware(request, call_next):
    """Enhanced request/response logging with detailed monitoring"""
    
    # Generate unique request ID for tracing
    request_id = str(uuid.uuid4())[:8]
    
    # Start timing
    start_time = datetime.utcnow()
    
    # Extract request details
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get('user-agent', 'Unknown')
    content_length = request.headers.get('content-length', '0')
    
    # Log incoming request
    api_logger.info(
        f"[{request_id}] {request.method} {request.url.path} - "
        f"IP: {client_ip} - UA: {user_agent[:50]}... - "
        f"Content-Length: {content_length}"
    )
    
    # Log query parameters if present
    if request.url.query:
        api_logger.debug(f"[{request_id}] Query params: {request.url.query}")
    
    # Log headers for debugging (excluding sensitive ones)
    sensitive_headers = {'authorization', 'cookie', 'x-api-key'}
    safe_headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in sensitive_headers
    }
    api_logger.debug(f"[{request_id}] Headers: {safe_headers}")
    
    # Add request ID to request state for use in endpoints
    request.state.request_id = request_id
    
    try:
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log response details
        response_size = response.headers.get('content-length', 'unknown')
        
        # Determine log level based on status code
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO
        
        api_logger.log(
            log_level,
            f"[{request_id}] Response: {response.status_code} - "
            f"Time: {process_time:.3f}s - Size: {response_size} bytes"
        )
        
        # Log slow requests
        if process_time > 2.0:  # Requests taking more than 2 seconds
            performance_logger.warning(
                f"[{request_id}] Slow request: {request.method} {request.url.path} "
                f"took {process_time:.3f}s"
            )
        
        # Add headers for monitoring
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # Calculate processing time for failed requests
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log the exception
        api_logger.error(
            f"[{request_id}] Request failed: {request.method} {request.url.path} - "
            f"Error: {str(e)} - Time: {process_time:.3f}s",
            exc_info=True
        )
        
        # Re-raise the exception to be handled by exception handlers
        raise

# Response compression middleware for large payloads
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=500)  # Compress responses > 500 bytes

# Connection pooling and resource management
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from functools import lru_cache

class ConnectionPool:
    """Connection pool for Firestore operations"""
    
    def __init__(self, max_connections: int = 10):
        self.max_connections = max_connections
        self.executor = ThreadPoolExecutor(max_workers=max_connections)
        self._connections = {}
        self._lock = threading.Lock()
    
    def get_connection(self, thread_id: int = None):
        """Get or create a Firestore connection for the current thread"""
        if thread_id is None:
            thread_id = threading.get_ident()
        
        with self._lock:
            if thread_id not in self._connections:
                # Create new connection for this thread
                from firebase_admin import firestore as admin_firestore
                self._connections[thread_id] = admin_firestore.client()
        
        return self._connections[thread_id]
    
    async def execute_async(self, func, *args, **kwargs):
        """Execute Firestore operation asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)
    
    def cleanup_connections(self):
        """Clean up unused connections"""
        with self._lock:
            active_threads = {t.ident for t in threading.enumerate()}
            inactive_connections = [
                tid for tid in self._connections.keys() 
                if tid not in active_threads
            ]
            for tid in inactive_connections:
                del self._connections[tid]

# Global connection pool
connection_pool = ConnectionPool(max_connections=15)

# Periodic cleanup task
async def cleanup_connections_periodically():
    """Clean up inactive connections every 5 minutes"""
    while True:
        await asyncio.sleep(300)  # 5 minutes
        connection_pool.cleanup_connections()

# Track startup time for performance monitoring
startup_time = datetime.utcnow()

# Start cleanup tasks
@app.on_event("startup")
async def startup_event():
    global startup_time
    startup_time = datetime.utcnow()
    asyncio.create_task(cleanup_connections_periodically())
    asyncio.create_task(cleanup_cache_periodically())
    logger.info("Performance optimization services started")
    logger.info(f"Server startup completed at {startup_time.isoformat()}")

# ==================== CACHING SYSTEM ====================

class EnhancedCache:
    """Enhanced in-memory cache with TTL management and statistics"""
    
    def __init__(self, max_size: int = 1000):
        self._cache = {}
        self._timestamps = {}
        self._access_count = {}
        self._hit_count = 0
        self._miss_count = 0
        self.max_size = max_size
        self._lock = threading.Lock()
    
    def _generate_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Generate cache key from endpoint and parameters"""
        # Sort parameters for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True, default=str)
        key_string = f"{endpoint}:{sorted_params}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _evict_lru(self) -> None:
        """Evict least recently used items when cache is full"""
        if len(self._cache) >= self.max_size:
            # Find least recently used key
            lru_key = min(self._access_count.keys(), key=lambda k: self._access_count[k])
            self._cache.pop(lru_key, None)
            self._timestamps.pop(lru_key, None)
            self._access_count.pop(lru_key, None)
    
    def get(self, endpoint: str, params: Dict[str, Any], ttl_seconds: int = 300) -> Optional[Any]:
        """Get cached response if not expired"""
        key = self._generate_key(endpoint, params)
        
        with self._lock:
            if key in self._cache:
                timestamp = self._timestamps.get(key, 0)
                if datetime.utcnow().timestamp() - timestamp < ttl_seconds:
                    # Update access count for LRU
                    self._access_count[key] = datetime.utcnow().timestamp()
                    self._hit_count += 1
                    logger.debug(f"Cache hit for {endpoint}")
                    return self._cache[key]
                else:
                    # Expired, remove from cache
                    self._cache.pop(key, None)
                    self._timestamps.pop(key, None)
                    self._access_count.pop(key, None)
            
            self._miss_count += 1
            return None
    
    def set(self, endpoint: str, params: Dict[str, Any], data: Any) -> None:
        """Cache response data with LRU eviction"""
        key = self._generate_key(endpoint, params)
        
        with self._lock:
            # Evict if cache is full
            self._evict_lru()
            
            # Store data
            self._cache[key] = data
            current_time = datetime.utcnow().timestamp()
            self._timestamps[key] = current_time
            self._access_count[key] = current_time
            logger.debug(f"Cached response for {endpoint}")
    
    def clear(self, pattern: str = None) -> None:
        """Clear cache entries matching pattern"""
        with self._lock:
            if pattern:
                keys_to_remove = [key for key in self._cache.keys() if pattern in key]
                for key in keys_to_remove:
                    self._cache.pop(key, None)
                    self._timestamps.pop(key, None)
                    self._access_count.pop(key, None)
            else:
                self._cache.clear()
                self._timestamps.clear()
                self._access_count.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_rate = (self._hit_count / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self._cache),
            "max_size": self.max_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def cleanup_expired(self, default_ttl: int = 300) -> int:
        """Clean up expired entries and return count of removed items"""
        current_time = datetime.utcnow().timestamp()
        expired_keys = []
        
        with self._lock:
            for key, timestamp in self._timestamps.items():
                if current_time - timestamp > default_ttl:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                self._access_count.pop(key, None)
        
        return len(expired_keys)

# Global cache instance
cache = EnhancedCache(max_size=2000)

def cached_response(ttl_seconds: int = 300, cache_key_params: List[str] = None, 
                  invalidate_on: List[str] = None, vary_by_user: bool = False):
    """
    Enhanced decorator for caching API responses with invalidation strategies
    
    Args:
        ttl_seconds: Time to live in seconds
        cache_key_params: List of parameter names to include in cache key
        invalidate_on: List of operations that should invalidate this cache
        vary_by_user: Whether to include user ID in cache key
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract endpoint name
            endpoint = func.__name__
            
            # Build cache key parameters
            cache_params = {}
            if cache_key_params:
                for param in cache_key_params:
                    if param in kwargs:
                        cache_params[param] = kwargs[param]
            
            # Add user ID to cache key if needed
            if vary_by_user:
                # Try to get current user from kwargs or dependencies
                current_user = kwargs.get('current_user')
                if current_user and isinstance(current_user, dict):
                    cache_params['user_id'] = current_user.get('id')
            
            # Try to get from cache
            cached_data = cache.get(endpoint, cache_params, ttl_seconds)
            if cached_data is not None:
                # Add cache hit header
                if isinstance(cached_data, dict):
                    cached_data['_cache_hit'] = True
                return cached_data
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Only cache successful responses
            if isinstance(result, dict) and result.get('success', False):
                # Remove any internal fields before caching
                cache_result = {k: v for k, v in result.items() if not k.startswith('_')}
                cache.set(endpoint, cache_params, cache_result)
            
            return result
        
        return wrapper
    return decorator

@app.post("/products/{product_id}/view", response_model=Dict[str, Any], summary="Increment product view count")
async def increment_product_view(
    request: Request,
    product_id: str = Path(..., description="Product ID")
):
    """Increment the product's view_count and return the new value.

    - Public endpoint (no auth) so product pages can record views.
    - Uses Firestore atomic increment when available; falls back to a transaction otherwise.
    """
    request_id = getattr(request.state, 'request_id', 'unknown')
    try:
        doc_ref = firestore_client.collection('products').document(product_id)
        snap = doc_ref.get()
        if not snap.exists:
            raise NotFoundError(f"Product with ID '{product_id}' not found", resource_type="product", resource_id=product_id)

        # Try atomic increment
        try:
            doc_ref.update({
                'view_count': firestore.Increment(1),
                'updatedAt': datetime.now()
            })
            snap2 = doc_ref.get()
            new_count = int(snap2.to_dict().get('view_count', 0))
        except Exception as inc_err:
            # Fallback to transactional update
            api_logger.warning(f"[{request_id}] Firestore Increment fallback for product {product_id}: {inc_err}")
            transaction = firestore_client.transaction()

            @firestore.transactional
            def txn_update(txn):
                current = doc_ref.get(transaction=txn)
                data = current.to_dict() if current.exists else {}
                view_count = int(data.get('view_count', 0)) + 1
                txn.update(doc_ref, {
                    'view_count': view_count,
                    'updatedAt': datetime.now()
                })
                return view_count

            new_count = txn_update(transaction)

        api_logger.info(f"[{request_id}] Incremented view_count for product {product_id} -> {new_count}")
        return create_success_response(
            data={
                'product_id': product_id,
                'view_count': new_count
            },
            message="Product view count incremented"
        )
    except NotFoundError as e:
        raise e
    except Exception as e:
        logger.error(f"Error incrementing view for product {product_id}: {str(e)}")
        raise APIError(500, "Failed to increment product view", "INTERNAL_ERROR")

# Cache invalidation helper
def invalidate_cache_pattern(pattern: str) -> None:
    """Invalidate cache entries matching a pattern"""
    cache.clear(pattern)
    logger.info(f"Invalidated cache entries matching pattern: {pattern}")

# Periodic cache cleanup
async def cleanup_cache_periodically():
    """Clean up expired cache entries every 10 minutes"""
    while True:
        await asyncio.sleep(600)  # 10 minutes
        removed_count = cache.cleanup_expired()
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} expired cache entries")

# Helper function to determine if endpoint should be public or protected
def is_public_endpoint(path: str, method: str = None) -> bool:
    """
    Determine if an endpoint should be public (no authentication required)
    
    Args:
        path: The endpoint path
        method: HTTP method (optional, for future method-specific logic)
    
    Returns:
        bool: True if endpoint should be public, False if protected
    """
    # Normalize path by removing trailing slashes for consistent matching
    normalized_path = path.rstrip('/')
    
    # Define public endpoint patterns
    public_patterns = [
        "/products/featured",
        "/products/active", 
        "/products/search",
        "/products/popular",
        "/products/{product_id}",
        "/categories",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json"
    ]
    
    # Check exact matches first
    if normalized_path in public_patterns:
        return True
    
    # Check pattern matches for parameterized paths
    for pattern in public_patterns:
        if "{" in pattern:
            # Convert OpenAPI path parameter format to regex-like matching
            pattern_regex = pattern.replace("{", "").replace("}", "")
            if pattern_regex in normalized_path and normalized_path.count("/") == pattern.count("/"):
                return True
    
    # Special cases for specific path patterns
    if normalized_path.startswith("/products/") and normalized_path.count("/") == 2:
        # Matches /products/{product_id} pattern - but not /products/ or /products
        path_parts = normalized_path.split("/")
        if len(path_parts) == 3 and path_parts[2]:  # Ensure there's actually a product ID
            return True
    
    return False

def validate_endpoint_security_requirements(openapi_schema: dict) -> list:
    """
    Validate that public endpoints don't have security requirements
    and protected endpoints do have them
    
    Args:
        openapi_schema: The OpenAPI schema dictionary
    
    Returns:
        list: List of validation issues found
    """
    issues = []
    
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                is_public = is_public_endpoint(path, method)
                has_security = "security" in operation and operation["security"]
                
                if is_public and has_security:
                    issues.append(f"Public endpoint {method.upper()} {path} has security requirements")
                elif not is_public and not has_security:
                    issues.append(f"Protected endpoint {method.upper()} {path} missing security requirements")
    
    return issues

# Custom OpenAPI schema with selective authorization
def custom_openapi():
    """
    Enhanced OpenAPI schema generation with clean authentication structure.
    
    This function ensures:
    1. Security is defined only at operation level, not parameter level
    2. Authorization parameters are excluded from endpoint parameter lists
    3. BearerAuth security scheme is properly configured
    4. Public endpoints don't have security requirements
    5. Protected endpoints have proper BearerAuth security requirements
    
    Requirements satisfied: 1.1, 1.4
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    # Generate base OpenAPI schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Ensure components section exists
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # Configure security schemes with proper BearerAuth configuration
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Firebase ID Token - Use the global 'Authorize' button to set your token"
        }
    }
    
    # Track statistics for logging
    auth_params_removed = 0
    protected_endpoints_configured = 0
    public_endpoints_configured = 0
    
    # Process each path and operation to optimize authentication
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                # Remove any authorization parameters from the parameters list
                if "parameters" in operation:
                    original_param_count = len(operation["parameters"])
                    operation["parameters"] = [
                        param for param in operation["parameters"]
                        if not (
                            param.get("name") in ["authorization", "Authorization"] and 
                            param.get("in") == "header"
                        )
                    ]
                    # Track removed parameters
                    removed_count = original_param_count - len(operation["parameters"])
                    auth_params_removed += removed_count
                    
                    # Remove empty parameters list
                    if not operation["parameters"]:
                        del operation["parameters"]
                
                # Determine if this endpoint should be public or protected
                if not is_public_endpoint(path, method):
                    # Add security requirement for protected endpoints
                    operation["security"] = [{"BearerAuth": []}]
                    protected_endpoints_configured += 1
                    
                    # Ensure operation has proper summary indicating authentication requirement
                    if "summary" in operation and "🔒" not in operation["summary"]:
                        operation["summary"] = f"🔒 {operation['summary']}"
                else:
                    # Ensure public endpoints don't have security requirements
                    operation.pop("security", None)
                    public_endpoints_configured += 1
                    
                    # Ensure operation has proper summary indicating public access
                    if "summary" in operation and "🌐" not in operation["summary"]:
                        operation["summary"] = f"🌐 {operation['summary']}"
    
    # Validate endpoint security configuration
    validation_issues = validate_endpoint_security_requirements(openapi_schema)
    if validation_issues:
        logger.warning(f"OpenAPI security validation issues found: {validation_issues}")
    else:
        logger.info(f"OpenAPI schema optimized successfully: "
                   f"{auth_params_removed} auth parameters removed, "
                   f"{protected_endpoints_configured} protected endpoints configured, "
                   f"{public_endpoints_configured} public endpoints configured")
    
    # Cache the optimized schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Enhanced database dependency with connection pooling
@lru_cache(maxsize=1)
def get_db_instance() -> FirestoreEcommerceDB:
    """Create a singleton database instance"""
    project_id = os.getenv("FIRESTORE_PROJECT_ID")
    return FirestoreEcommerceDB(project_id=project_id)

def get_db() -> FirestoreEcommerceDB:
    """Dependency to get optimized Firestore database instance"""
    return get_db_instance()

async def get_current_user(request: Request):
    """
    Firebase Authentication dependency for centralized authentication.
    
    This function provides:
    - Firebase ID token verification using firebase-admin SDK
    - Automatic user profile creation for new users
    - Role-based access control with custom claims support
    - Proper error handling with meaningful messages
    
    Usage:
    - Protected endpoints use: Depends(get_current_user)
    - Frontend sends: Authorization: Bearer <firebase_id_token>
    - Token is verified against Firebase Auth service
    """
    authorization = request.headers.get("authorization")
    if not authorization:
        log_security_event(
            event_type="missing_authorization_header",
            severity="INFO"
        )
        raise AuthenticationError(
            "Authorization header missing. Please include 'Authorization: Bearer <firebase_token>' header.",
            error_code="MISSING_AUTH_HEADER",
            context={"expected_format": "Bearer <firebase_id_token>"}
        )
    
    if not authorization.startswith("Bearer "):
        log_security_event(
            event_type="invalid_authorization_format",
            details={"provided_format": authorization[:20] + "..." if len(authorization) > 20 else authorization},
            severity="WARNING"
        )
        raise AuthenticationError(
            "Invalid authorization header format. Expected 'Bearer <firebase_id_token>'",
            error_code="INVALID_AUTH_FORMAT",
            context={"expected_format": "Bearer <firebase_id_token>"}
        )
    
    token = authorization.split(" ", 1)[1]  # Use split with maxsplit=1 to handle tokens with spaces
    
    if not token or len(token) < 10:
        raise AuthenticationError(
            "Invalid token format. Token appears to be empty or too short.",
            error_code="INVALID_TOKEN_FORMAT"
        )
    
    try:
        # Verify the Firebase ID token with enhanced validation
        decoded_token = auth.verify_id_token(token, check_revoked=True)
        uid = decoded_token['uid']
        email = decoded_token.get('email', '')
        
        # Log successful token verification
        auth_logger.debug(f"Firebase token verified successfully for UID: {uid}")
        
        # Get user data from Firestore by UID
        user_doc = firestore_client.collection('users').document(uid).get()
        
        if not user_doc.exists:
            # Check if user exists by email first (for migration scenarios)
            if email:
                existing_user_query = firestore_client.collection('users').where('email', '==', email).limit(1).get()
                
                if existing_user_query:
                    # User exists with this email, migrate to new UID
                    existing_user_doc = existing_user_query[0]
                    user_data = existing_user_doc.to_dict()
                    
                    # Update the existing user document with the new UID
                    user_data['uid'] = uid
                    user_data['updatedAt'] = datetime.now()
                    user_data['lastLoginAt'] = datetime.now()
                    
                    firestore_client.collection('users').document(uid).set(user_data)
                    
                    # Delete the old document if it has a different ID
                    if existing_user_doc.id != uid:
                        firestore_client.collection('users').document(existing_user_doc.id).delete()
                    
                    logger.info(f"Migrated existing user {email} to UID: {uid}")
                else:
                    # Create new user with default customer role
                    user_data = {
                        'uid': uid,
                        'email': email,
                        'displayName': decoded_token.get('name', decoded_token.get('firebase', {}).get('identities', {}).get('email', [''])[0].split('@')[0]),
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
                    firestore_client.collection('users').document(uid).set(user_data)
                    logger.info(f"Created new user profile for UID: {uid}, Email: {email}")
            else:
                raise AuthenticationError(
                    "User profile not found and email not available for auto-creation",
                    error_code="USER_PROFILE_REQUIRED"
                )
        else:
            user_data = user_doc.to_dict()
            
            # Update last login time asynchronously (don't wait for it)
            try:
                firestore_client.collection('users').document(uid).update({
                    'lastLoginAt': datetime.now()
                })
            except Exception as update_error:
                # Log but don't fail authentication for login time update errors
                logger.warning(f"Failed to update last login time for {uid}: {update_error}")
        
        # Check if user account is active
        if not user_data.get('isActive', True):
            log_security_event(
                event_type="deactivated_user_access_attempt",
                user_id=uid,
                details={"email": email},
                severity="WARNING"
            )
            raise AuthenticationError(
                "User account has been deactivated. Please contact support.",
                error_code="ACCOUNT_DEACTIVATED",
                context={"user_id": uid}
            )
        
        # Support custom claims for enhanced role management
        user_role = user_data.get('role', 'customer')
        if 'role' in decoded_token:  # Custom claim takes precedence
            user_role = decoded_token['role']
            # Update user role in Firestore if it changed
            if user_data.get('role') != user_role:
                firestore_client.collection('users').document(uid).update({'role': user_role})
        
        # Return user info in the format expected by the application
        user_info = {
            "id": uid,
            "email": user_data.get('email', email),
            "name": user_data.get('displayName', ''),
            "role": user_role,
            "email_verified": user_data.get('emailVerified', False),
            "phone": user_data.get('phone', ''),
            "photo_url": user_data.get('photoURL', '')
        }
        
        # Log successful authentication
        auth_logger.info(f"User authenticated successfully: {uid} ({email}) with role: {user_role}")
        
        return user_info
        
    except auth.InvalidIdTokenError as e:
        log_security_event(
            event_type="invalid_firebase_token",
            details={"token_prefix": token[:10] + "..." if len(token) > 10 else token, "error": str(e)},
            severity="WARNING"
        )
        raise AuthenticationError(
            "Invalid Firebase ID token. Please log in again.",
            error_code="INVALID_FIREBASE_TOKEN",
            context={"token_type": "firebase_id_token"}
        )
    except auth.ExpiredIdTokenError as e:
        log_security_event(
            event_type="expired_firebase_token",
            details={"token_prefix": token[:10] + "..." if len(token) > 10 else token},
            severity="INFO"
        )
        raise AuthenticationError(
            "Firebase ID token has expired. Please log in again.",
            error_code="EXPIRED_FIREBASE_TOKEN",
            context={"token_type": "firebase_id_token"}
        )
    except auth.RevokedIdTokenError as e:
        log_security_event(
            event_type="revoked_firebase_token",
            details={"token_prefix": token[:10] + "..." if len(token) > 10 else token},
            severity="WARNING"
        )
        raise AuthenticationError(
            "Firebase ID token has been revoked. Please log in again.",
            error_code="REVOKED_FIREBASE_TOKEN",
            context={"token_type": "firebase_id_token"}
        )
    except auth.CertificateFetchError as e:
        auth_logger.error(f"Firebase certificate fetch error: {str(e)}")
        log_security_event(
            event_type="firebase_certificate_error",
            details={"error": str(e)},
            severity="ERROR"
        )
        raise AuthenticationError(
            "Authentication service temporarily unavailable. Please try again.",
            error_code="AUTH_SERVICE_ERROR",
            context={"service": "firebase_auth"}
        )
    except Exception as e:
        auth_logger.error(f"Unexpected error in Firebase authentication: {str(e)}", exc_info=True)
        log_security_event(
            event_type="authentication_system_error",
            details={"error": str(e), "error_type": type(e).__name__},
            severity="ERROR"
        )
        raise AuthenticationError(
            "Authentication system temporarily unavailable. Please try again later.",
            error_code="AUTH_SYSTEM_ERROR",
            context={"original_error": str(e)}
        )

async def require_admin(current_user = Depends(get_current_user)):
    """Enhanced dependency to require admin role with detailed logging"""
    if current_user.get("role") != "admin":
        log_security_event(
            event_type="unauthorized_admin_access_attempt",
            user_id=current_user.get('id'),
            details={
                "user_role": current_user.get('role'),
                "required_role": "admin"
            },
            severity="WARNING"
        )
        raise AuthorizationError(
            "Admin access required",
            required_role="admin",
            user_role=current_user.get('role'),
            context={"user_id": current_user.get('id')}
        )
    return current_user

async def require_seller_or_admin(current_user = Depends(get_current_user)):
    """Enhanced dependency to require seller or admin role"""
    user_role = current_user.get("role")
    if user_role not in ["seller", "admin"]:
        log_security_event(
            event_type="unauthorized_seller_access_attempt",
            user_id=current_user.get('id'),
            details={
                "user_role": user_role,
                "required_roles": ["seller", "admin"]
            },
            severity="WARNING"
        )
        raise AuthorizationError(
            "Seller or admin access required",
            required_role="seller or admin",
            user_role=user_role,
            context={"user_id": current_user.get('id')}
        )
    return current_user

async def require_manager_or_admin(current_user = Depends(get_current_user)):
    """Enhanced dependency to require manager or admin role"""
    user_role = current_user.get("role")
    if user_role not in ["manager", "admin"]:
        log_security_event(
            event_type="unauthorized_manager_access_attempt",
            user_id=current_user.get('id'),
            details={
                "user_role": user_role,
                "required_roles": ["manager", "admin"]
            },
            severity="WARNING"
        )
        raise AuthorizationError(
            "Manager or admin access required",
            required_role="manager or admin",
            user_role=user_role,
            context={"user_id": current_user.get('id')}
        )
    return current_user

async def require_authenticated_user(current_user = Depends(get_current_user)):
    """Dependency to require any authenticated user"""
    return current_user

# Optional authentication dependency for endpoints that work with or without auth
async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """Optional authentication - returns user if authenticated, None if not"""
    try:
        return await get_current_user(request)
    except AuthenticationError:
        return None
    except Exception as e:
        logger.warning(f"Error in optional authentication: {str(e)}")
        return None

# ==================== STANDARDIZED RESPONSE MODELS ====================

class StandardResponse(BaseModel):
    """Standardized API response format"""
    success: bool
    data: Optional[Any] = None
    message: str
    timestamp: str
    error: Optional[str] = None
    error_code: Optional[str] = None

class PaginatedResponse(BaseModel):
    """Standardized paginated response format"""
    success: bool
    data: List[Any]
    pagination: Dict[str, Any]
    message: str
    timestamp: str
    error: Optional[str] = None

class ValidationErrorDetail(BaseModel):
    """Validation error detail"""
    field: str
    message: str
    value: Optional[Any] = None

class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    success: bool = False
    error: str = "Validation failed"
    error_code: str = "VALIDATION_ERROR"
    details: List[ValidationErrorDetail]
    timestamp: str

# ==================== CUSTOM EXCEPTIONS ====================

class APIError(HTTPException):
    """Enhanced custom API exception with error codes and context"""
    
    def __init__(
        self, 
        status_code: int, 
        detail: str, 
        error_code: str = None,
        context: Dict[str, Any] = None,
        user_message: str = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or f"HTTP_{status_code}"
        self.context = context or {}
        self.user_message = user_message or detail
        self.timestamp = datetime.utcnow().isoformat()

class ValidationError(APIError):
    """Enhanced validation error exception"""
    
    def __init__(
        self, 
        detail: str, 
        field: str = None, 
        value: Any = None,
        context: Dict[str, Any] = None
    ):
        super().__init__(422, detail, "VALIDATION_ERROR", context)
        self.field = field
        self.value = value

class AuthenticationError(APIError):
    """Enhanced authentication error exception"""
    
    def __init__(
        self, 
        detail: str = "Authentication required",
        error_code: str = "AUTHENTICATION_ERROR",
        context: Dict[str, Any] = None
    ):
        super().__init__(401, detail, error_code, context)

class AuthorizationError(APIError):
    """Enhanced authorization error exception"""
    
    def __init__(
        self, 
        detail: str = "Access denied",
        required_role: str = None,
        user_role: str = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if required_role:
            context['required_role'] = required_role
        if user_role:
            context['user_role'] = user_role
        super().__init__(403, detail, "AUTHORIZATION_ERROR", context)

class NotFoundError(APIError):
    """Enhanced resource not found exception"""
    
    def __init__(
        self, 
        detail: str = "Resource not found",
        resource_type: str = None,
        resource_id: str = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if resource_type:
            context['resource_type'] = resource_type
        if resource_id:
            context['resource_id'] = resource_id
        super().__init__(404, detail, "NOT_FOUND", context)

class ConflictError(APIError):
    """Enhanced resource conflict exception"""
    
    def __init__(
        self, 
        detail: str = "Resource conflict",
        conflict_type: str = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if conflict_type:
            context['conflict_type'] = conflict_type
        super().__init__(409, detail, "CONFLICT", context)

class DatabaseError(APIError):
    """Database operation error exception"""
    
    def __init__(
        self, 
        detail: str = "Database operation failed",
        operation: str = None,
        collection: str = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if operation:
            context['operation'] = operation
        if collection:
            context['collection'] = collection
        super().__init__(500, detail, "DATABASE_ERROR", context)

class RateLimitError(APIError):
    """Rate limit exceeded exception"""
    
    def __init__(
        self, 
        detail: str = "Rate limit exceeded",
        retry_after: int = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if retry_after:
            context['retry_after'] = retry_after
        super().__init__(429, detail, "RATE_LIMIT_EXCEEDED", context)

class ServiceUnavailableError(APIError):
    """Service unavailable exception"""
    
    def __init__(
        self, 
        detail: str = "Service temporarily unavailable",
        service_name: str = None,
        context: Dict[str, Any] = None
    ):
        context = context or {}
        if service_name:
            context['service_name'] = service_name
        super().__init__(503, detail, "SERVICE_UNAVAILABLE", context)

# ==================== ERROR HANDLING UTILITIES ====================

def log_user_action(
    user_id: str, 
    action: str, 
    resource_type: str = None, 
    resource_id: str = None,
    details: Dict[str, Any] = None,
    request_id: str = None
):
    """Log user actions for audit trail"""
    
    log_data = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if resource_type:
        log_data["resource_type"] = resource_type
    if resource_id:
        log_data["resource_id"] = resource_id
    if details:
        log_data["details"] = details
    if request_id:
        log_data["request_id"] = request_id
    
    api_logger.info(f"User action: {log_data}")

def log_security_event(
    event_type: str,
    user_id: str = None,
    ip_address: str = None,
    details: Dict[str, Any] = None,
    severity: str = "INFO"
):
    """Log security-related events"""
    
    log_data = {
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity
    }
    
    if user_id:
        log_data["user_id"] = user_id
    if ip_address:
        log_data["ip_address"] = ip_address
    if details:
        log_data["details"] = details
    
    # Use appropriate log level based on severity
    log_level = getattr(logging, severity.upper(), logging.INFO)
    auth_logger.log(log_level, f"Security event: {log_data}")

def handle_database_error(
    operation: str,
    collection: str,
    error: Exception,
    context: Dict[str, Any] = None
) -> DatabaseError:
    """Standardized database error handling"""
    
    error_context = {
        "operation": operation,
        "collection": collection,
        "original_error": str(error),
        "error_type": type(error).__name__
    }
    
    if context:
        error_context.update(context)
    
    # Log the database error
    db_logger.error(
        f"Database operation failed: {operation} on {collection} - {str(error)}",
        exc_info=True
    )
    
    # Return appropriate database error
    if "not found" in str(error).lower():
        return NotFoundError(
            f"Resource not found in {collection}",
            resource_type=collection,
            context=error_context
        )
    elif "permission" in str(error).lower() or "unauthorized" in str(error).lower():
        return AuthorizationError(
            f"Insufficient permissions for {operation} on {collection}",
            context=error_context
        )
    else:
        return DatabaseError(
            f"Database {operation} operation failed",
            operation=operation,
            collection=collection,
            context=error_context
        )

def validate_request_data(
    data: Dict[str, Any],
    required_fields: List[str],
    field_validators: Dict[str, callable] = None
) -> None:
    """Validate request data with detailed error reporting"""
    
    # Check required fields
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            field=missing_fields[0] if len(missing_fields) == 1 else "multiple",
            context={"missing_fields": missing_fields}
        )
    
    # Run custom validators
    if field_validators:
        for field, validator in field_validators.items():
            if field in data:
                try:
                    validator(data[field])
                except ValueError as e:
                    raise ValidationError(
                        f"Invalid value for field '{field}': {str(e)}",
                        field=field,
                        value=data[field]
                    )

# ==================== RESPONSE HELPERS ====================

def create_success_response(data: Any = None, message: str = "Operation successful") -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

def create_paginated_response(
    data: List[Any], 
    total_count: Optional[int] = None,
    page: int = 1,
    limit: int = 20,
    has_next: bool = False,
    next_cursor: Optional[str] = None,
    message: str = "Data retrieved successfully"
) -> Dict[str, Any]:
    """Create standardized paginated response"""
    pagination = {
        "page": page,
        "limit": limit,
        "count": len(data),
        "has_next": has_next
    }
    
    if total_count is not None:
        pagination["total_count"] = total_count
    
    if next_cursor:
        pagination["next_cursor"] = next_cursor
    
    return {
        "success": True,
        "data": data,
        "pagination": pagination,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

def create_error_response(
    error: str, 
    error_code: str = "INTERNAL_ERROR",
    details: Optional[Any] = None
) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "success": False,
        "error": error,
        "error_code": error_code,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if details:
        response["details"] = details
    
    return response

# ==================== INPUT VALIDATION HELPERS ====================

def validate_pagination_params(limit: int, page: int = 1) -> Tuple[int, int]:
    """Validate and normalize pagination parameters"""
    if limit < 1 or limit > 100:
        raise ValidationError("Limit must be between 1 and 100", "limit")
    
    if page < 1:
        raise ValidationError("Page must be greater than 0", "page")
    
    return limit, page

def validate_price_range(min_price: Optional[float], max_price: Optional[float]) -> None:
    """Validate price range parameters"""
    if min_price is not None and min_price < 0:
        raise ValidationError("Minimum price cannot be negative", "min_price")
    
    if max_price is not None and max_price < 0:
        raise ValidationError("Maximum price cannot be negative", "max_price")
    
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationError("Minimum price cannot be greater than maximum price", "price_range")

def validate_user_access(current_user: Dict[str, Any], target_user_id: str, allow_admin: bool = True) -> None:
    """Validate user access to resources"""
    if current_user['id'] != target_user_id:
        if not (allow_admin and current_user.get('role') == 'admin'):
            raise AuthorizationError("You can only access your own resources")

# ==================== PYDANTIC MODELS ====================

class UserCreate(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="Valid email address")
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    role: str = Field("customer", pattern=r'^(customer|seller|admin|manager)$', description="User role")
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,15}$', description="Phone number")
    address: Optional[Dict[str, Any]] = Field(None, description="User address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "name": "John Doe",
                "role": "customer",
                "phone": "+1234567890",
                "address": {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "zip": "12345",
                    "country": "US"
                }
            }
        }

class UserUpdate(BaseModel):
    # Frontend may send either name or displayName
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="User's full name")
    displayName: Optional[str] = Field(None, min_length=1, max_length=100, description="Display name")
    # Admin-only: may update another user's email via /users/{user_id}
    email: Optional[str] = Field(None, pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="Email address (admin only)")
    # Avatar may be sent as avatar or photoURL
    photoURL: Optional[str] = Field(None, description="Photo URL / Avatar URL")
    avatar: Optional[str] = Field(None, description="Alias for photoURL")
    phone: Optional[str] = Field(None, pattern=r'^\+?[\d\s\-\(\)]{10,15}$', description="Phone number")
    address: Optional[Dict[str, Any]] = Field(None, description="User address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")

class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Product title")
    description: str = Field(..., min_length=10, max_length=2000, description="Product description")
    price: float = Field(..., gt=0, le=1000000, description="Product price")
    category_id: str = Field(..., min_length=1, description="Category ID")
    subcategory_id: Optional[str] = Field(None, description="Subcategory ID")
    seller_id: str = Field(..., min_length=1, description="Seller ID")
    images: List[str] = Field(default_factory=list, max_items=10, description="Product images URLs")
    specifications: Optional[Dict[str, Any]] = Field(None, description="Product specifications")
    tags: List[str] = Field(default_factory=list, max_items=20, description="Product tags")
    inventory_quantity: int = Field(0, ge=0, description="Initial inventory quantity")
    sku: Optional[str] = Field(None, max_length=50, description="Stock Keeping Unit")
    weight: Optional[float] = Field(None, gt=0, description="Product weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Product dimensions")
    is_featured: bool = Field(False, description="Whether product is featured")

    class Config:
        schema_extra = {
            "example": {
                "title": "Wireless Bluetooth Headphones",
                "description": "High-quality wireless headphones with noise cancellation",
                "price": 99.99,
                "category_id": "electronics",
                "seller_id": "seller123",
                "images": ["https://example.com/image1.jpg"],
                "tags": ["wireless", "bluetooth", "headphones"],
                "inventory_quantity": 50,
                "sku": "WBH-001"
            }
        }

class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Product title")
    description: Optional[str] = Field(None, min_length=10, max_length=2000, description="Product description")
    price: Optional[float] = Field(None, gt=0, le=1000000, description="Product price")
    category_id: Optional[str] = Field(None, min_length=1, description="Category ID")
    subcategory_id: Optional[str] = Field(None, description="Subcategory ID")
    images: Optional[List[str]] = Field(None, max_items=10, description="Product images URLs")
    specifications: Optional[Dict[str, Any]] = Field(None, description="Product specifications")
    tags: Optional[List[str]] = Field(None, max_items=20, description="Product tags")
    inventory_quantity: Optional[int] = Field(None, ge=0, description="Inventory quantity")
    sku: Optional[str] = Field(None, max_length=50, description="Stock Keeping Unit")
    weight: Optional[float] = Field(None, gt=0, description="Product weight in kg")
    dimensions: Optional[Dict[str, float]] = Field(None, description="Product dimensions")
    is_featured: Optional[bool] = Field(None, description="Whether product is featured")
    status: Optional[str] = Field(None, pattern=r'^(active|inactive|archived|draft)$', description="Product status")

class OrderItem(BaseModel):
    product_id: str = Field(..., min_length=1, description="Product ID")
    quantity: int = Field(..., gt=0, le=1000, description="Quantity")
    price: float = Field(..., gt=0, description="Unit price")
    variant_id: Optional[str] = Field(None, description="Product variant ID")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Item attributes")

class OrderCreate(BaseModel):
    customer_id: str = Field(..., min_length=1, description="Customer ID")
    seller_id: str = Field(..., min_length=1, description="Seller ID")
    items: List[OrderItem] = Field(..., min_items=1, max_items=50, description="Order items")
    total_amount: float = Field(..., gt=0, le=1000000, description="Total order amount")
    currency: str = Field("USD", pattern=r'^[A-Z]{3}$', description="Currency code")
    shipping_address: Dict[str, Any] = Field(..., description="Shipping address")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="Billing address")
    payment_method: Optional[str] = Field(None, description="Payment method")
    shipping_method: Optional[str] = Field(None, description="Shipping method")
    notes: Optional[str] = Field(None, max_length=500, description="Order notes")

    class Config:
        schema_extra = {
            "example": {
                "customer_id": "customer123",
                "seller_id": "seller456",
                "items": [
                    {
                        "product_id": "prod123",
                        "quantity": 2,
                        "price": 29.99
                    }
                ],
                "total_amount": 59.98,
                "currency": "USD",
                "shipping_address": {
                    "street": "123 Main St",
                    "city": "Anytown",
                    "state": "CA",
                    "zip": "12345",
                    "country": "US"
                }
            }
        }

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(pending|confirmed|processing|shipped|delivered|cancelled|refunded)$', description="Order status")
    fulfillment_details: Optional[Dict[str, Any]] = Field(None, description="Fulfillment details")

class OrderCancel(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="Cancellation reason")
    refund_amount: Optional[float] = Field(None, ge=0, description="Refund amount")

class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    image_url: Optional[str] = Field(None, pattern=r'^https?://.+', description="Category image URL")
    sort_order: int = Field(0, ge=0, description="Sort order")
    meta_title: Optional[str] = Field(None, max_length=100, description="SEO meta title")
    meta_description: Optional[str] = Field(None, max_length=200, description="SEO meta description")

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(None, max_length=500, description="Category description")
    parent_id: Optional[str] = Field(None, description="Parent category ID")
    image_url: Optional[str] = Field(None, pattern=r'^https?://.+', description="Category image URL")
    sort_order: Optional[int] = Field(None, ge=0, description="Sort order")
    meta_title: Optional[str] = Field(None, max_length=100, description="SEO meta title")
    meta_description: Optional[str] = Field(None, max_length=200, description="SEO meta description")



class CartItemAdd(BaseModel):
    product_id: str = Field(..., min_length=1, description="Product ID")
    variant_id: Optional[str] = Field(None, description="Product variant ID")
    quantity: int = Field(1, gt=0, le=100, description="Quantity")
    price: float = Field(..., gt=0, description="Unit price")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Item attributes")

class CartItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, gt=0, le=100, description="Quantity")
    variant_id: Optional[str] = Field(None, description="Product variant ID")
    attributes: Optional[Dict[str, Any]] = Field(None, description="Item attributes")

class ReviewCreate(BaseModel):
    product_id: str = Field(..., min_length=1, description="Product ID")
    user_id: str = Field(..., min_length=1, description="User ID")
    order_id: Optional[str] = Field(None, description="Order ID for verified purchase")
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = Field(None, max_length=100, description="Review title")
    content: str = Field(..., min_length=10, max_length=2000, description="Review content")
    images: List[str] = Field(default_factory=list, max_items=5, description="Review images")
    verified_purchase: bool = Field(False, description="Whether this is a verified purchase")

    class Config:
        schema_extra = {
            "example": {
                "product_id": "prod123",
                "user_id": "user456",
                "rating": 5,
                "title": "Great product!",
                "content": "This product exceeded my expectations. Highly recommended!"
            }
        }

class ReviewUpdate(BaseModel):
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5")
    title: Optional[str] = Field(None, max_length=100, description="Review title")
    content: Optional[str] = Field(None, min_length=10, max_length=2000, description="Review content")
    images: Optional[List[str]] = Field(None, max_items=5, description="Review images")

class ReviewModerate(BaseModel):
    action: str = Field(..., pattern=r'^(approved|rejected)$', description="Moderation action")
    notes: Optional[str] = Field(None, max_length=500, description="Moderation notes")

class NotificationCreate(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID")
    type: str = Field(..., pattern=r'^(order_update|product_alert|promotion|system|security)$', description="Notification type")
    title: str = Field(..., min_length=1, max_length=100, description="Notification title")
    message: str = Field(..., min_length=1, max_length=500, description="Notification message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")
    channel: str = Field("app", pattern=r'^(app|email|sms|push)$', description="Notification channel")



# ==================== AUTHENTICATION ENDPOINTS ====================

@app.get("/auth/status", response_model=Dict[str, Any], summary="Check authentication status")
async def check_auth_status(
    request: Request
):
    """Check if user is authenticated without requiring authentication (optional auth)"""
    try:
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            return create_success_response(
                data={
                    "authenticated": False,
                    "user": None,
                    "requires_login": True
                },
                message="No authentication provided"
            )
        
        # Try to get current user without raising exceptions
        try:
            current_user = await get_current_user(request)
            return create_success_response(
                data={
                    "authenticated": True,
                    "user": current_user,
                    "requires_login": False
                },
                message="User is authenticated"
            )
        except AuthenticationError:
            return create_success_response(
                data={
                    "authenticated": False,
                    "user": None,
                    "requires_login": True,
                    "token_invalid": True
                },
                message="Authentication token is invalid or expired"
            )
            
    except Exception as e:
        logger.error(f"Error checking auth status: {str(e)}")
        return create_success_response(
            data={
                "authenticated": False,
                "user": None,
                "requires_login": True,
                "error": "Unable to verify authentication status"
            },
            message="Authentication status check failed"
        )

@app.get("/auth/me", response_model=Dict[str, Any], summary="Get current user profile")
async def get_current_user_profile(
    current_user = Depends(get_current_user)
):
    """Get the current authenticated user's profile with full details"""
    try:
        return create_success_response(
            data={
                "user": current_user,
                "authenticated": True,
                "session_valid": True
            },
            message="User profile retrieved successfully"
        )
    except Exception as e:
        logger.error(f"Error getting current user profile: {str(e)}")
        raise APIError(500, "Failed to retrieve user profile", "INTERNAL_ERROR")

@app.post("/auth/test", response_model=Dict[str, Any], summary="Test authentication")
async def test_authentication(
    current_user = Depends(get_current_user)
):
    """Test endpoint to verify Firebase authentication is working properly"""
    try:
        return create_success_response(
            data={
                "authenticated": True,
                "user_id": current_user["id"],
                "email": current_user["email"],
                "role": current_user["role"],
                "email_verified": current_user.get("email_verified", False),
                "auth_method": "firebase_id_token"
            },
            message="Firebase authentication successful"
        )
    except Exception as e:
        logger.error(f"Error in authentication test: {str(e)}")
        raise APIError(500, "Authentication test failed", "INTERNAL_ERROR")

@app.get("/users/profile", response_model=Dict[str, Any], summary="Get detailed user profile")
@cached_response(ttl_seconds=180, vary_by_user=True)
async def get_detailed_user_profile(
    request: Request,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get detailed user profile with preferences and settings.

    Optimizations:
    - Cached per-user for 180s using in-memory cache.
    - Returns a combined shape merging Firebase auth and Firestore profile.
    """
    try:
        request_id = getattr(request.state, 'request_id', 'unknown')
        api_logger.info(f"[{request_id}] GET /users/profile for user {current_user['id']}")
        result = db.get_user_profile(current_user['id'])
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")

        user_data = result.get('data', {})

        # Merge Firebase auth data with Firestore profile data
        detailed_profile = {
            **current_user,
            **user_data,
            "last_updated": user_data.get('updatedAt', ''),
            "member_since": user_data.get('createdAt', ''),
            "profile_complete": bool(
                user_data.get('displayName') and
                user_data.get('phone') and
                user_data.get('address', {}).get('street')
            ),
        }

        # Ensure a 'name' field is present for frontend display
        if not detailed_profile.get('name'):
            detailed_profile['name'] = (
                detailed_profile.get('displayName')
                or (detailed_profile.get('email', '').split('@')[0] if detailed_profile.get('email') else 'User')
            )

        return create_success_response(
            data=detailed_profile,
            message="Detailed user profile retrieved successfully"
        )

    except APIError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting detailed user profile: {str(e)}")
        raise APIError(500, "Failed to retrieve detailed user profile", "INTERNAL_ERROR")

@app.post("/users/profile", response_model=Dict[str, Any], summary="Update user profile")
async def update_user_profile(
    request: Request,
    profile_data: UserUpdate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update current user's profile information"""
    try:
        # Users can only update their own profile
        request_id = getattr(request.state, 'request_id', 'unknown')
        update_data = profile_data.dict(exclude_unset=True)
        # Map common frontend fields to Firestore schema
        if 'name' in update_data and update_data['name']:
            update_data['displayName'] = update_data.pop('name')
        if 'avatar' in update_data and update_data['avatar']:
            update_data['photoURL'] = update_data.pop('avatar')
        # Prevent email changes via self-service endpoints; admin-only through /users/{user_id}
        if 'email' in update_data:
            update_data.pop('email', None)

        # Normalize address field keys
        if 'address' in update_data and isinstance(update_data['address'], dict):
            addr = update_data['address']
            if 'zipcode' in addr and 'zip_code' not in addr:
                addr['zip_code'] = addr.pop('zipcode')
            if 'pin' in addr and 'zip_code' not in addr:
                addr['zip_code'] = addr.pop('pin')
            update_data['address'] = addr

        update_data['updatedAt'] = datetime.now()
        
        api_logger.info(f"[{request_id}] POST /users/profile by {current_user['id']} fields={list(update_data.keys())}")
        result = db.update_user_profile(current_user['id'], update_data)
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")
        # Invalidate cached detailed profile for this user so the next fetch is fresh
        try:
            invalidate_cache_pattern("get_detailed_user_profile")
        except Exception:
            pass

        return create_success_response(
            data={
                "user_id": current_user['id'],
                "updated_fields": list(update_data.keys()),
                "updated_at": update_data['updatedAt'].isoformat()
            },
            message="User profile updated successfully"
        )
        
    except APIError as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise APIError(500, "Failed to update user profile", "INTERNAL_ERROR")

# Support PUT semantics for updating user profile to align with REST expectations
@app.put("/users/profile", response_model=Dict[str, Any], summary="Update user profile")
async def put_user_profile(
    request: Request,
    profile_data: UserUpdate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Alias of POST /users/profile to prevent extra frontend retries"""
    try:
        request_id = getattr(request.state, 'request_id', 'unknown')
        update_data = profile_data.dict(exclude_unset=True)
        if 'name' in update_data and update_data['name']:
            update_data['displayName'] = update_data.pop('name')
        if 'avatar' in update_data and update_data['avatar']:
            update_data['photoURL'] = update_data.pop('avatar')
        # Prevent email changes via self-service endpoints; admin-only through /users/{user_id}
        if 'email' in update_data:
            update_data.pop('email', None)

        # Normalize address
        if 'address' in update_data and isinstance(update_data['address'], dict):
            addr = update_data['address']
            if 'zipcode' in addr and 'zip_code' not in addr:
                addr['zip_code'] = addr.pop('zipcode')
            if 'pin' in addr and 'zip_code' not in addr:
                addr['zip_code'] = addr.pop('pin')
            update_data['address'] = addr
        update_data['updatedAt'] = datetime.now()

        api_logger.info(f"[{request_id}] PUT /users/profile by {current_user['id']} fields={list(update_data.keys())}")
        result = db.update_user_profile(current_user['id'], update_data)
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")
        try:
            invalidate_cache_pattern("get_detailed_user_profile")
        except Exception:
            pass

        return create_success_response(
            data={
                "user_id": current_user['id'],
                "updated_fields": list(update_data.keys()),
                "updated_at": update_data['updatedAt'].isoformat()
            },
            message="User profile updated successfully"
        )
    except APIError as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating user profile via PUT: {str(e)}")
        raise APIError(500, "Failed to update user profile", "INTERNAL_ERROR")

# ==================== USER ENDPOINTS ====================

@app.post("/users", response_model=Dict[str, Any], summary="Create user profile")
async def create_user(
    user_data: UserCreate,
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Create a new user profile"""
    # Check if user already exists by email
    existing_user_query = firestore_client.collection('users').where('email', '==', user_data.email).limit(1).get()
    
    if existing_user_query:
        # User already exists, return existing user info
        existing_user_doc = existing_user_query[0]
        return {
            "success": True,
            "message": "User already exists",
            "user_id": existing_user_doc.id,
            "data": existing_user_doc.to_dict()
        }
    
    # Create new user if doesn't exist
    result = db.create_user_profile(user_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}", response_model=Dict[str, Any], summary="Get user profile")
async def get_user(
    request: Request,
    user_id: str = Path(..., min_length=1, description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get user profile by ID with enhanced error handling and logging"""
    
    request_id = getattr(request.state, 'request_id', 'unknown')
    
    try:
        # Log user access attempt
        log_user_action(
            user_id=current_user['id'],
            action="get_user_profile",
            resource_type="user",
            resource_id=user_id,
            request_id=request_id
        )
        
        # Validate user access with enhanced error context
        if current_user['id'] != user_id:
            if current_user.get('role') != 'admin':
                log_security_event(
                    event_type="unauthorized_user_access_attempt",
                    user_id=current_user['id'],
                    details={
                        "attempted_user_id": user_id,
                        "user_role": current_user.get('role')
                    },
                    severity="WARNING"
                )
                raise AuthorizationError(
                    "You can only access your own profile",
                    required_role="admin or self",
                    user_role=current_user.get('role'),
                    context={
                        "requested_user_id": user_id,
                        "current_user_id": current_user['id']
                    }
                )
        
        # Attempt to get user profile with enhanced error handling
        try:
            result = db.get_user_profile(user_id)
        except Exception as db_error:
            raise handle_database_error(
                operation="get_user_profile",
                collection="users",
                error=db_error,
                context={"user_id": user_id}
            )
        
        if not result['success']:
            if "not found" in result.get('error', '').lower():
                raise NotFoundError(
                    f"User profile not found",
                    resource_type="user",
                    resource_id=user_id,
                    context={"database_error": result.get('error')}
                )
            else:
                raise DatabaseError(
                    "Failed to retrieve user profile",
                    operation="get_user_profile",
                    collection="users",
                    context={
                        "user_id": user_id,
                        "database_error": result.get('error')
                    }
                )
        
        user_data = result.get('data')
        if not user_data:
            raise NotFoundError(
                f"User profile data is empty",
                resource_type="user",
                resource_id=user_id
            )
        
        # Log successful access
        api_logger.info(
            f"[{request_id}] User profile retrieved successfully - "
            f"User: {current_user['id']} accessed profile: {user_id}"
        )
        
        return create_success_response(
            data=user_data,
            message="User profile retrieved successfully"
        )
        
    except (AuthorizationError, NotFoundError, ValidationError, DatabaseError) as e:
        # These are expected errors that should be re-raised as-is
        raise e
    except Exception as e:
        # Unexpected errors - log and convert to generic error
        api_logger.error(
            f"[{request_id}] Unexpected error getting user {user_id}: {str(e)}",
            exc_info=True
        )
        raise APIError(
            500, 
            "An unexpected error occurred while retrieving user profile", 
            "INTERNAL_ERROR",
            context={
                "user_id": user_id,
                "operation": "get_user_profile"
            }
        )

@app.put("/users/{user_id}", response_model=Dict[str, Any], summary="Update user profile")
async def update_user(
    user_id: str = Path(..., description="User ID"),
    user_data: UserUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update user profile (admin can edit others; only admin can change email)"""
    # Users can only update their own profile unless admin
    if current_user['id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")

    update_data = user_data.dict(exclude_unset=True)
    # Map common frontend fields to Firestore schema
    if 'name' in update_data and update_data['name']:
        update_data['displayName'] = update_data.pop('name')
    if 'avatar' in update_data and update_data['avatar']:
        update_data['photoURL'] = update_data.pop('avatar')

    # Handle email update - admin only, and sync with Firebase Auth
    if 'email' in update_data:
        if current_user.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Only admin can update email")
        try:
            auth.update_user(user_id, email=update_data['email'])
            # Reflect verification state conservatively
            update_data['emailVerified'] = False
        except Exception as e:
            logger.error(f"Failed to update Firebase Auth email for user {user_id}: {str(e)}")
            raise APIError(400, f"Email update failed: {str(e)}", "EMAIL_UPDATE_FAILED")

    update_data['updatedAt'] = datetime.now()

    result = db.update_user_profile(user_id, update_data)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])

    # Invalidate cached profiles so subsequent fetches are fresh
    try:
        invalidate_cache_pattern("get_detailed_user_profile")
    except Exception:
        pass

    return create_success_response(
        data={
            "user_id": user_id,
            "updated_fields": list(update_data.keys()),
            "updated_at": update_data['updatedAt'].isoformat()
        },
        message="User profile updated successfully"
    )

@app.get("/users", response_model=Dict[str, Any], summary="Get users by role")
async def get_users_by_role(
    role: str = Query(..., description="User role to filter by"),
    limit: int = Query(50, description="Number of users to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Get users by role (admin only)"""
    result = db.get_users_by_role(role, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/users/{user_id}/deactivate", response_model=Dict[str, Any], summary="Deactivate user")
async def deactivate_user(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Deactivate a user (admin only)"""
    result = db.deactivate_user(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== PRODUCT ENDPOINTS ====================

@app.post("/products", response_model=Dict[str, Any], summary="Add new product")
async def add_product(
    product_data: ProductCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Add a new product with validation and standardized response"""
    try:
        # Ensure seller_id matches current user (unless admin)
        if current_user['role'] != 'admin' and product_data.seller_id != current_user['id']:
            raise AuthorizationError("You can only create products for yourself")
        
        # Validate product data
        product_dict = product_data.dict()
        
        # Additional business logic validation
        if product_dict.get('price', 0) <= 0:
            raise ValidationError("Product price must be greater than 0", "price")
        
        if len(product_dict.get('images', [])) == 0:
            logger.warning(f"Product created without images by user {current_user['id']}")
        
        result = db.add_product(product_dict)
        if not result['success']:
            if "already exists" in result.get('error', '').lower():
                raise ConflictError("Product with this SKU already exists")
            else:
                raise APIError(400, result['error'], "DATABASE_ERROR")
        
        product_id = result.get('data', {}).get('product_id')
        
        # Invalidate relevant caches
        cache.clear("get_featured_products")
        cache.clear("get_active_products")
        cache.clear("get_products")
        
        return create_success_response(
            data={
                "product_id": product_id,
                "seller_id": product_data.seller_id,
                "title": product_data.title
            },
            message="Product created successfully"
        )
        
    except (AuthorizationError, ValidationError, ConflictError) as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating product: {str(e)}")
        raise APIError(500, "Failed to create product", "INTERNAL_ERROR")

@app.get("/products/active", response_model=Dict[str, Any], summary="Get active products")
@cached_response(ttl_seconds=300, cache_key_params=['limit', 'last_doc_id'])  # Cache for 5 minutes
async def get_active_products(
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get all active products with pagination"""
    try:
        # Validate pagination parameters
        limit, _ = validate_pagination_params(limit)
        
        result = db.get_active_products(limit, last_doc_id)
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")
        
        # Convert to standardized paginated response
        products = result.get('data', [])
        has_next = len(products) == limit  # Simple check for more data
        
        return create_paginated_response(
            data=products,
            limit=limit,
            has_next=has_next,
            next_cursor=products[-1].get('id') if products else None,
            message="Active products retrieved successfully"
        )
        
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting active products: {str(e)}")
        raise APIError(500, "Failed to retrieve active products", "INTERNAL_ERROR")

@app.get("/products/featured", response_model=Dict[str, Any], summary="Get featured products")
@cached_response(ttl_seconds=600, cache_key_params=['limit'])  # Cache for 10 minutes
async def get_featured_products(
    limit: int = Query(10, ge=1, le=50, description="Number of featured products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get featured products - Public access"""
    try:
        # Validate pagination parameters
        limit, _ = validate_pagination_params(limit)
        
        result = db.get_featured_products(limit)
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")
        
        products = result.get('data', [])
        
        return create_success_response(
            data=products,
            message=f"Retrieved {len(products)} featured products"
        )
        
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting featured products: {str(e)}")
        raise APIError(500, "Failed to retrieve featured products", "INTERNAL_ERROR")

@app.get("/products", response_model=Dict[str, Any], summary="Get products with filters")
@cached_response(ttl_seconds=180, cache_key_params=['category_id', 'subcategory_id', 'seller_id', 'min_price', 'max_price', 'tags', 'limit', 'last_doc_id'])  # Cache for 3 minutes
async def get_products(
    category_id: Optional[str] = Query(None, min_length=1, description="Filter by category ID"),
    subcategory_id: Optional[str] = Query(None, min_length=1, description="Filter by subcategory ID"),
    seller_id: Optional[str] = Query(None, min_length=1, description="Filter by seller ID"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get products with optional filters and pagination"""
    try:
        # Validate parameters
        limit, _ = validate_pagination_params(limit)
        validate_price_range(min_price, max_price)
        
        # Build filters
        filters = {}
        if category_id:
            filters['category_id'] = category_id
        if subcategory_id:
            filters['subcategory_id'] = subcategory_id
        if seller_id:
            filters['seller_id'] = seller_id
        if min_price is not None:
            filters['min_price'] = min_price
        if max_price is not None:
            filters['max_price'] = max_price
        if tags:
            # Clean and validate tags
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tag_list) > 10:
                raise ValidationError("Maximum 10 tags allowed", "tags")
            filters['tags'] = tag_list
        
        result = db.get_products_with_filters(filters, limit, last_doc_id)
        if not result['success']:
            raise APIError(400, result['error'], "DATABASE_ERROR")
        
        products = result.get('data', [])
        has_next = len(products) == limit
        
        return create_paginated_response(
            data=products,
            limit=limit,
            has_next=has_next,
            next_cursor=products[-1].get('id') if products else None,
            message=f"Retrieved {len(products)} products with filters"
        )
        
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting products with filters: {str(e)}")
        raise APIError(500, "Failed to retrieve products", "INTERNAL_ERROR")

@app.get("/products/search", response_model=Dict[str, Any], summary="Search products")
@cached_response(ttl_seconds=120, cache_key_params=['q', 'limit'])  # Cache for 2 minutes
async def search_products(
    q: str = Query(..., min_length=1, max_length=100, description="Search keywords"),
    limit: int = Query(20, ge=1, le=100, description="Number of products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Search products by keywords with validation and standardized response"""
    try:
        # Validate parameters
        limit, _ = validate_pagination_params(limit)
        
        # Clean search query
        search_query = q.strip()
        if not search_query:
            raise ValidationError("Search query cannot be empty", "q")
        
        result = db.search_products(search_query, limit)
        if not result['success']:
            raise APIError(400, result['error'], "SEARCH_ERROR")
        
        products = result.get('data', [])
        
        return create_success_response(
            data=products,
            message=f"Found {len(products)} products matching '{search_query}'"
        )
        
    except ValidationError as e:
        raise e
    except Exception as e:
        logger.error(f"Error searching products: {str(e)}")
        raise APIError(500, "Search operation failed", "INTERNAL_ERROR")

@app.get("/products/popular", response_model=Dict[str, Any], summary="Get popular products")
@cached_response(ttl_seconds=900, cache_key_params=['metric', 'limit'])  # Cache for 15 minutes
async def get_popular_products(
    metric: str = Query("sales", description="Metric to sort by (sales, views)"),
    limit: int = Query(10, description="Number of products to return"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get popular products by sales or views"""
    result = db.get_popular_products(limit, metric)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/{product_id}", response_model=Dict[str, Any], summary="Get product by ID")
async def get_product(
    product_id: str = Path(..., min_length=1, description="Product ID"),
    increment_view: bool = Query(True, description="Whether to increment view count"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get product details by ID with optional view count increment"""
    try:
        result = db.get_product(product_id, increment_view)
        if not result['success']:
            if "not found" in result.get('error', '').lower():
                raise NotFoundError(f"Product with ID '{product_id}' not found")
            else:
                raise APIError(400, result['error'], "DATABASE_ERROR")
        
        product = result.get('data')
        if not product:
            raise NotFoundError(f"Product with ID '{product_id}' not found")
        
        return create_success_response(
            data=product,
            message="Product retrieved successfully"
        )
        
    except (NotFoundError, ValidationError) as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {str(e)}")
        raise APIError(500, "Failed to retrieve product", "INTERNAL_ERROR")

@app.put("/products/{product_id}", response_model=Dict[str, Any], summary="Update product")
async def update_product(
    product_id: str = Path(..., description="Product ID"),
    product_data: ProductUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Update product details"""
    # Check if user owns the product or is admin
    if current_user['role'] != 'admin':
        # Get product to check ownership
        product_result = db.get_product(product_id, increment_view=False)
        if not product_result['success']:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product = product_result['data']
        if product.get('seller_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only update your own products")
    
    result = db.update_product(product_id, product_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/products/{product_id}/archive", response_model=Dict[str, Any], summary="Archive product")
async def archive_product(
    product_id: str = Path(..., description="Product ID"),
    status: str = Query("archived", description="New status for the product"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Archive or deactivate a product"""
    # Check if user owns the product or is admin
    if current_user['role'] != 'admin':
        # Get product to check ownership
        product_result = db.get_product(product_id, increment_view=False)
        if not product_result['success']:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product = product_result['data']
        if product.get('seller_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only archive your own products")
    
    result = db.archive_product(product_id, status)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/products/batch", response_model=Dict[str, Any], summary="Batch update products")
async def batch_update_products(
    updates: List[Dict[str, Any]] = Body(..., description="List of product updates"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Batch update products (admin or seller only)"""
    # For sellers, verify they own all products being updated
    if current_user['role'] != 'admin':
        for update in updates:
            product_id = update.get('product_id')
            if product_id:
                product_result = db.get_product(product_id, increment_view=False)
                if product_result['success']:
                    product = product_result['data']
                    if product.get('seller_id') != current_user['id']:
                        raise HTTPException(status_code=403, detail=f"You can only update your own products (Product ID: {product_id})")
    
    result = db.batch_update_products(updates)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== ORDER ENDPOINTS ====================

@app.post("/orders", response_model=Dict[str, Any], summary="Create new order")
async def create_order(
    order_data: OrderCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Create a new order with validation and standardized response"""
    try:
        # Validate customer access
        if current_user['role'] != 'admin' and order_data.customer_id != current_user['id']:
            raise AuthorizationError("You can only create orders for yourself")
        
        # Validate order data
        order_dict = order_data.dict()
        
        # Business logic validation
        if not order_dict.get('items'):
            raise ValidationError("Order must contain at least one item", "items")
        
        # Validate total amount matches items
        calculated_total = sum(item['quantity'] * item['price'] for item in order_dict['items'])
        if abs(calculated_total - order_dict['total_amount']) > 0.01:
            raise ValidationError("Total amount does not match item prices", "total_amount")
        
        # Validate shipping address
        shipping_address = order_dict.get('shipping_address', {})
        required_address_fields = ['street', 'city', 'zip', 'country']
        missing_fields = [field for field in required_address_fields if not shipping_address.get(field)]
        if missing_fields:
            raise ValidationError(f"Missing required address fields: {', '.join(missing_fields)}", "shipping_address")
        
        result = db.create_order(order_dict)
        if not result['success']:
            if "insufficient inventory" in result.get('error', '').lower():
                raise ConflictError("Insufficient inventory for one or more items")
            else:
                raise APIError(400, result['error'], "DATABASE_ERROR")
        
        order_id = result.get('data', {}).get('order_id')
        
        return create_success_response(
            data={
                "order_id": order_id,
                "customer_id": order_data.customer_id,
                "total_amount": order_data.total_amount,
                "currency": order_data.currency,
                "status": "pending"
            },
            message="Order created successfully"
        )
        
    except (AuthorizationError, ValidationError, ConflictError) as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        raise APIError(500, "Failed to create order", "INTERNAL_ERROR")

@app.get("/orders/{order_id}", response_model=Dict[str, Any], summary="Get order by ID")
async def get_order(
    order_id: str = Path(..., description="Order ID"),
    include_items: bool = Query(True, description="Include order items"),
    include_timeline: bool = Query(False, description="Include order timeline"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Get order details by ID"""
    # Get order first to check ownership
    result = db.get_order(order_id, include_items, include_timeline)
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    
    order = result['data']
    # Customer can access own orders, seller can access their orders, admin can access all
    if (current_user['role'] != 'admin' and 
        order.get('customer_id') != current_user['id'] and 
        order.get('seller_id') != current_user['id']):
        raise HTTPException(status_code=403, detail="Access denied")
    if not result['success']:
        raise HTTPException(status_code=404, detail=result['error'])
    return result

@app.get("/users/{user_id}/orders", response_model=Dict[str, Any], summary="Get user orders")
async def get_user_orders(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, description="Number of orders to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Get all orders for a user"""
    # Users can only access their own orders unless admin
    if current_user['id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_orders(user_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/sellers/{seller_id}/orders", response_model=Dict[str, Any], summary="Get seller orders")
async def get_seller_orders(
    seller_id: str = Path(..., description="Seller ID"),
    limit: int = Query(20, description="Number of orders to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Get all orders for a seller"""
    # Sellers can only access their own orders unless admin
    if current_user['role'] != 'admin' and current_user['id'] != seller_id:
        raise HTTPException(status_code=403, detail="You can only access your own orders")
    
    result = db.get_seller_orders(seller_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/orders/{order_id}/status", response_model=Dict[str, Any], summary="Update order status")
async def update_order_status(
    order_id: str = Path(..., description="Order ID"),
    status_data: OrderStatusUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Update order status"""
    # Check if user is the seller for this order or admin
    if current_user['role'] != 'admin':
        order_result = db.get_order(order_id, include_items=False, include_timeline=False)
        if not order_result['success']:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order = order_result['data']
        if order.get('seller_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only update orders you are selling")
    
    result = db.update_order_status(
        order_id, 
        status_data.status, 
        status_data.fulfillment_details
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/orders/{order_id}/cancel", response_model=Dict[str, Any], summary="Cancel order")
async def cancel_order(
    order_id: str = Path(..., description="Order ID"),
    cancel_data: OrderCancel = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Cancel an order"""
    # Get order to check ownership and status
    order_result = db.get_order(order_id, include_items=False, include_timeline=False)
    if not order_result['success']:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order = order_result['data']
    
    # Customer can cancel their own pending orders, admin can cancel any
    if current_user['role'] != 'admin':
        if order.get('customer_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only cancel your own orders")
        
        # Check if order is in a cancellable state
        if order.get('status') not in ['pending', 'confirmed']:
            raise HTTPException(status_code=400, detail="Order cannot be cancelled in current status")
    
    result = db.cancel_order(order_id, cancel_data.reason, cancel_data.refund_amount)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.post("/orders/{order_id}/timeline", response_model=Dict[str, Any], summary="Add timeline event")
async def add_order_timeline_event(
    order_id: str = Path(..., description="Order ID"),
    event: str = Body(..., description="Event name"),
    details: str = Body(..., description="Event details"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Add a timeline event to an order"""
    # Check if user is the seller for this order or admin
    if current_user['role'] != 'admin':
        order_result = db.get_order(order_id, include_items=False, include_timeline=False)
        if not order_result['success']:
            raise HTTPException(status_code=404, detail="Order not found")
        
        order = order_result['data']
        if order.get('seller_id') != current_user['id']:
            raise HTTPException(status_code=403, detail="You can only add timeline events to orders you are selling")
    
    result = db.add_order_timeline_event(order_id, event, details, current_user['id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== CATEGORY ENDPOINTS ====================

@app.get("/categories", response_model=Dict[str, Any], summary="List categories")
@cached_response(ttl_seconds=1800, cache_key_params=['parent_id'])  # Cache for 30 minutes
async def list_categories(
    parent_id: Optional[str] = Query(None, description="Parent category ID for subcategories"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """List all categories or subcategories"""
    result = db.list_categories(parent_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.post("/categories", response_model=Dict[str, Any], summary="Add category")
async def add_category(
    category_data: CategoryCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Add a new category (admin only)"""
    result = db.add_category(category_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/categories/{category_id}", response_model=Dict[str, Any], summary="Update category")
async def update_category(
    category_id: str = Path(..., description="Category ID"),
    category_data: CategoryUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Update a category (admin only)"""
    result = db.update_category(category_id, category_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/categories/{category_id}/archive", response_model=Dict[str, Any], summary="Archive category")
async def archive_category(
    category_id: str = Path(..., description="Category ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Archive a category (admin only)"""
    result = db.archive_category(category_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result





# ==================== CART ENDPOINTS ====================


@app.post("/users/{user_id}/cart/items", response_model=Dict[str, Any], summary="Add item to cart")
async def add_item_to_cart(
    user_id: str = Path(..., description="User ID"),
    item_data: CartItemAdd = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Add an item to cart"""
    # Users can only modify their own cart
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.add_item_to_cart(user_id, item_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.delete("/users/{user_id}/cart/items/{product_id}", response_model=Dict[str, Any], summary="Remove item from cart")
async def remove_item_from_cart(
    user_id: str = Path(..., description="User ID"),
    product_id: str = Path(..., description="Product ID"),
    variant_id: Optional[str] = Query(None, description="Variant ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Remove an item from cart"""
    # Users can only modify their own cart
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.remove_item_from_cart(user_id, product_id, variant_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/users/{user_id}/cart/items/{product_id}", response_model=Dict[str, Any], summary="Update cart item")
async def update_cart_item(
    user_id: str = Path(..., description="User ID"),
    product_id: str = Path(..., description="Product ID"),
    update_data: CartItemUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Update quantity or variant of a cart item"""
    # Users can only modify their own cart
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.update_cart_item(user_id, product_id, update_data.dict(exclude_unset=True))
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/cart", response_model=Dict[str, Any], summary="Get user cart")
async def get_user_cart(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Get cart for a user"""
    # Users can only access their own cart
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_cart(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.delete("/users/{user_id}/cart", response_model=Dict[str, Any], summary="Clear cart")
async def clear_cart(
    user_id: str = Path(..., description="User ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Clear/empty cart"""
    # Users can only clear their own cart
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.clear_cart(user_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== REVIEW ENDPOINTS ====================

@app.post("/reviews", response_model=Dict[str, Any], summary="Submit review")
async def submit_review(
    review_data: ReviewCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Submit a review for a product"""
    # Ensure the user_id matches the authenticated user
    if review_data.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="You can only submit reviews for yourself")
    
    # Note: Purchase verification should be implemented in the database layer
    result = db.submit_review(review_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/products/{product_id}/reviews", response_model=Dict[str, Any], summary="Get product reviews")
async def get_product_reviews(
    product_id: str = Path(..., description="Product ID"),
    status: str = Query("approved", description="Review status filter"),
    limit: int = Query(20, description="Number of reviews to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get reviews for a product"""
    result = db.get_product_reviews(product_id, status, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/reviews", response_model=Dict[str, Any], summary="Get user reviews")
async def get_user_reviews(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, description="Number of reviews to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Get reviews by user"""
    # Users can only access their own reviews unless admin
    if current_user['id'] != user_id and current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_reviews(user_id, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.put("/reviews/{review_id}", response_model=Dict[str, Any], summary="Update review")
async def update_review(
    review_id: str = Path(..., description="Review ID"),
    review_data: ReviewUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Update a review"""
    # Users can only update their own reviews within time limit
    # The database method will handle ownership and time limit validation
    result = db.update_review(review_id, review_data.dict(exclude_unset=True), current_user['id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/reviews/{review_id}/moderate", response_model=Dict[str, Any], summary="Moderate review")
async def moderate_review(
    review_id: str = Path(..., description="Review ID"),
    moderation_data: ReviewModerate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """Moderate (approve/reject) a review (admin only)"""
    result = db.moderate_review(
        review_id, 
        moderation_data.action, 
        admin_user['id'], 
        moderation_data.notes
    )
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== NOTIFICATION ENDPOINTS ====================

@app.post("/notifications", response_model=Dict[str, Any], summary="Create notification")
async def create_notification(
    notification_data: NotificationCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Create/send a notification to a user"""
    
    result = db.create_notification(notification_data.dict())
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/users/{user_id}/notifications", response_model=Dict[str, Any], summary="Get user notifications")
async def get_user_notifications(
    user_id: str = Path(..., description="User ID"),
    unread_only: bool = Query(False, description="Return only unread notifications"),
    limit: int = Query(20, description="Number of notifications to return"),
    last_doc_id: Optional[str] = Query(None, description="Last document ID for pagination"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Get notifications for a user"""
    # Users can only access their own notifications
    if current_user['id'] != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_user_notifications(user_id, unread_only, limit, last_doc_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.patch("/notifications/{notification_id}/read", response_model=Dict[str, Any], summary="Mark notification as read")
async def mark_notification_read(
    notification_id: str = Path(..., description="Notification ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    """Mark notification as read"""
    # Users can only mark their own notifications as read
    # The database method will handle ownership validation
    result = db.mark_notification_read(notification_id, current_user['id'])
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result



# ==================== DASHBOARD & ANALYTICS ENDPOINTS ====================

@app.get("/dashboard/stats", response_model=Dict[str, Any], summary="Get dashboard stats")
async def get_dashboard_stats(
    seller_id: Optional[str] = Query(None, description="Seller ID for seller-specific stats"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Get dashboard statistics"""
    # Admin can see all stats, sellers can see only their stats
    if seller_id and current_user['role'] != 'admin' and current_user['id'] != seller_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # If no seller_id specified and user is seller, default to their own stats
    if not seller_id and current_user['role'] == 'seller':
        seller_id = current_user['id']
    
    result = db.get_dashboard_stats(seller_id)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/sellers/{seller_id}/sales-stats", response_model=Dict[str, Any], summary="Get sales stats")
async def get_sales_stats(
    seller_id: str = Path(..., description="Seller ID"),
    start_date: datetime = Query(..., description="Start date for stats"),
    end_date: datetime = Query(..., description="End date for stats"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    """Get sales statistics for a seller"""
    # Sellers can only see their own stats, admin can see any seller's stats
    if current_user['role'] != 'admin' and current_user['id'] != seller_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = db.get_sales_stats(seller_id, start_date, end_date)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

@app.get("/analytics/low-stock-alerts", response_model=Dict[str, Any], summary="Get low stock alerts")
async def get_low_stock_alerts(
    limit: int = Query(20, description="Number of alerts to return"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_manager_or_admin)
):
    """Get real-time low stock alerts"""
    # Admin or warehouse managers can access low stock alerts
    
    result = db.get_low_stock_alerts(limit)
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['error'])
    return result

# ==================== USER LOOKUP ENDPOINTS ====================

class UserLookupRequest(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', description="User email address")

@app.post("/users/lookup", response_model=Dict[str, Any], summary="Get user profile ID by email")
async def get_user_profile_by_email(
    lookup_request: UserLookupRequest,
    current_user = Depends(get_current_user)
):
    """Get user profile ID from Firestore by email address"""
    try:
        email = lookup_request.email.lower().strip()
        
        # Query Firestore for user by email
        users_query = firestore_client.collection('users').where('email', '==', email).limit(1).get()
        
        if not users_query:
            raise NotFoundError(
                f"No user found with email: {email}",
                resource_type="user",
                context={"email": email}
            )
        
        user_doc = users_query[0]
        user_data = user_doc.to_dict()
        
        # Log admin lookup action
        log_user_action(
            user_id=current_user['id'],
            action="user_lookup_by_email",
            resource_type="user",
            resource_id=user_doc.id,
            details={"lookup_email": email}
        )
        
        return create_success_response(
            data={
                "user_id": user_doc.id,
                "email": user_data.get('email'),
                "name": user_data.get('displayName', ''),
                "role": user_data.get('role', 'customer'),
                "is_active": user_data.get('isActive', True),
                "created_at": user_data.get('createdAt', ''),
                "last_login_at": user_data.get('lastLoginAt', '')
            },
            message=f"User profile found for email: {email}"
        )
        
    except NotFoundError as e:
        raise e
    except Exception as e:
        logger.error(f"Error looking up user by email {lookup_request.email}: {str(e)}")
        raise APIError(500, "Failed to lookup user by email", "INTERNAL_ERROR")

# ==================== UTILITY ENDPOINTS ====================

@app.get("/favicon.ico")
async def favicon():
    """Handle favicon requests"""
    return JSONResponse(status_code=204, content=None)

@app.get("/health", response_model=Dict[str, Any], summary="Comprehensive health check")
async def health_check(db: FirestoreEcommerceDB = Depends(get_db)):
    """Comprehensive health check including database, cache, and system status"""
    try:
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "checks": {}
        }
        
        # Database health check
        db_start = datetime.utcnow()
        db_result = db.health_check()
        db_time = (datetime.utcnow() - db_start).total_seconds()
        
        health_data["checks"]["database"] = {
            "status": "healthy" if db_result['success'] else "unhealthy",
            "response_time_ms": round(db_time * 1000, 2),
            "details": db_result.get('message', 'Database connection successful')
        }
        
        # Cache health check
        cache_start = datetime.utcnow()
        cache.set("health_check", {}, {"test": True})
        cached_value = cache.get("health_check", {})
        cache_time = (datetime.utcnow() - cache_start).total_seconds()
        
        health_data["checks"]["cache"] = {
            "status": "healthy" if cached_value else "unhealthy",
            "response_time_ms": round(cache_time * 1000, 2),
            "cache_size": len(cache._cache)
        }
        
        # System health
        health_data["checks"]["system"] = {
            "status": "healthy",
            "uptime_seconds": (datetime.utcnow() - startup_time).total_seconds() if 'startup_time' in globals() else 0,
            "memory_usage": "N/A"  # Could add psutil for memory monitoring
        }
        
        # Overall status
        all_healthy = all(check["status"] == "healthy" for check in health_data["checks"].values())
        if not all_healthy:
            health_data["status"] = "degraded"
            return JSONResponse(
                status_code=503,
                content=health_data
            )
        
        return create_success_response(
            data=health_data,
            message="All systems healthy"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# ==================== PERFORMANCE MONITORING ENDPOINTS ====================

@app.get("/admin/cache/stats", response_model=Dict[str, Any], summary="Get cache statistics")
async def get_cache_stats(current_user = Depends(require_admin)):
    """Get detailed cache performance statistics - Admin only"""
    try:
        stats = cache.get_stats()
        
        return create_success_response(
            data={
                "cache_statistics": stats,
                "cache_entries": len(cache._cache),
                "memory_usage_estimate": len(str(cache._cache)),  # Rough estimate
                "recommendations": {
                    "hit_rate_status": "good" if stats["hit_rate_percent"] > 70 else "needs_improvement",
                    "cache_size_status": "normal" if stats["cache_size"] < stats["max_size"] * 0.8 else "near_full"
                }
            },
            message="Cache statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise APIError(500, "Failed to retrieve cache statistics", "INTERNAL_ERROR")

@app.post("/admin/cache/clear", response_model=Dict[str, Any], summary="Clear cache")
async def clear_cache(
    pattern: Optional[str] = Query(None, description="Pattern to match for selective clearing"),
    current_user = Depends(require_admin)
):
    """Clear cache entries - Admin only"""
    try:
        if pattern:
            cache.clear(pattern)
            message = f"Cleared cache entries matching pattern: {pattern}"
        else:
            cache.clear()
            message = "Cleared all cache entries"
        
        logger.info(f"Cache cleared by admin {current_user['id']}: {message}")
        
        return create_success_response(
            message=message
        )
        
    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise APIError(500, "Failed to clear cache", "INTERNAL_ERROR")

@app.get("/admin/performance/metrics", response_model=Dict[str, Any], summary="Get performance metrics")
async def get_performance_metrics(current_user = Depends(require_admin)):
    """Get system performance metrics - Admin only"""
    try:
        # Get cache stats
        cache_stats = cache.get_stats()
        
        # Get connection pool stats (if available)
        connection_stats = {
            "active_connections": len(connection_pool._connections),
            "max_connections": connection_pool.max_connections,
            "connection_utilization": len(connection_pool._connections) / connection_pool.max_connections * 100
        }
        
        # Calculate uptime
        startup_time = globals().get('startup_time', datetime.utcnow())
        uptime_seconds = (datetime.utcnow() - startup_time).total_seconds()
        
        performance_data = {
            "cache_performance": cache_stats,
            "connection_pool": connection_stats,
            "system": {
                "uptime_seconds": uptime_seconds,
                "uptime_formatted": str(timedelta(seconds=int(uptime_seconds))),
                "compression_enabled": True,  # GZip middleware is enabled
                "async_operations": True
            },
            "recommendations": []
        }
        
        # Add performance recommendations
        if cache_stats["hit_rate_percent"] < 50:
            performance_data["recommendations"].append({
                "type": "cache",
                "message": "Cache hit rate is low. Consider increasing TTL or reviewing cache strategy."
            })
        
        if connection_stats["connection_utilization"] > 80:
            performance_data["recommendations"].append({
                "type": "connections",
                "message": "Connection pool utilization is high. Consider increasing max_connections."
            })
        
        return create_success_response(
            data=performance_data,
            message="Performance metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        raise APIError(500, "Failed to retrieve performance metrics", "INTERNAL_ERROR")

# ==================== ENHANCED ERROR HANDLERS ====================

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

def get_request_context(request) -> Dict[str, Any]:
    """Extract request context for error logging"""
    return {
        "method": request.method,
        "url": str(request.url),
        "client_ip": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "request_id": getattr(request.state, 'request_id', 'unknown')
    }

@app.exception_handler(RequestValidationError)
async def enhanced_validation_exception_handler(request, exc: RequestValidationError):
    """Enhanced Pydantic validation error handler with detailed logging"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Process validation errors
    details = []
    for error in exc.errors():
        field = ".".join(str(x) for x in error["loc"][1:])  # Skip 'body' prefix
        details.append({
            "field": field,
            "message": error["msg"],
            "value": error.get("input"),
            "type": error.get("type")
        })
    
    # Log validation error with context
    api_logger.warning(
        f"[{request_id}] Validation error on {request.method} {request.url.path} - "
        f"Fields: {[d['field'] for d in details]}"
    )
    
    response_content = {
        "success": False,
        "error": "Validation failed",
        "error_code": "VALIDATION_ERROR",
        "details": details,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    return JSONResponse(status_code=422, content=response_content)

@app.exception_handler(APIError)
async def enhanced_api_exception_handler(request, exc: APIError):
    """Enhanced custom API exception handler with context and logging"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Determine log level based on status code
    if exc.status_code >= 500:
        log_level = logging.ERROR
    elif exc.status_code >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO
    
    # Log the API error with context
    api_logger.log(
        log_level,
        f"[{request_id}] API Error {exc.status_code}: {exc.detail} - "
        f"Code: {exc.error_code} - Context: {exc.context}"
    )
    
    response_content = {
        "success": False,
        "error": exc.user_message,
        "error_code": exc.error_code,
        "timestamp": exc.timestamp,
        "request_id": request_id
    }
    
    # Include context in development/debug mode
    if exc.context and logger.level <= logging.DEBUG:
        response_content["context"] = exc.context
    
    return JSONResponse(status_code=exc.status_code, content=response_content)

@app.exception_handler(StarletteHTTPException)
async def enhanced_http_exception_handler(request, exc: StarletteHTTPException):
    """Enhanced HTTP exception handler with improved error mapping"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Enhanced error code mapping
    error_code_map = {
        400: "BAD_REQUEST",
        401: "AUTHENTICATION_ERROR", 
        403: "AUTHORIZATION_ERROR",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        406: "NOT_ACCEPTABLE",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        410: "GONE",
        413: "PAYLOAD_TOO_LARGE",
        415: "UNSUPPORTED_MEDIA_TYPE",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
        501: "NOT_IMPLEMENTED",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
    
    # Log HTTP error
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    api_logger.log(
        log_level,
        f"[{request_id}] HTTP Error {exc.status_code}: {exc.detail} - "
        f"Code: {error_code}"
    )
    
    response_content = {
        "success": False,
        "error": exc.detail,
        "error_code": error_code,
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id
    }
    
    return JSONResponse(status_code=exc.status_code, content=response_content)

@app.exception_handler(Exception)
async def enhanced_general_exception_handler(request, exc: Exception):
    """Enhanced general exception handler with detailed error tracking"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Generate error ID for tracking
    error_id = str(uuid.uuid4())[:8]
    
    # Log detailed error information
    api_logger.error(
        f"[{request_id}] Unhandled exception (Error ID: {error_id}): {str(exc)} - "
        f"Type: {type(exc).__name__} - Context: {request_context}",
        exc_info=True
    )
    
    # Log stack trace to separate error logger
    logger.error(
        f"[{request_id}] Full stack trace for Error ID {error_id}:",
        exc_info=True
    )
    
    response_content = {
        "success": False,
        "error": "Internal server error",
        "error_code": "INTERNAL_ERROR",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "error_id": error_id
    }
    
    # Include exception details in development mode
    if logger.level <= logging.DEBUG:
        response_content["debug_info"] = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        }
    
    return JSONResponse(status_code=500, content=response_content)

# ==================== ADDITIONAL ERROR HANDLERS ====================

@app.exception_handler(DatabaseError)
async def database_exception_handler(request, exc: DatabaseError):
    """Handle database-specific errors"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Log database error with operation context
    db_logger.error(
        f"[{request_id}] Database error: {exc.detail} - "
        f"Operation: {exc.context.get('operation', 'unknown')} - "
        f"Collection: {exc.context.get('collection', 'unknown')}"
    )
    
    response_content = {
        "success": False,
        "error": "Database operation failed",
        "error_code": exc.error_code,
        "timestamp": exc.timestamp,
        "request_id": request_id
    }
    
    return JSONResponse(status_code=exc.status_code, content=response_content)

@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request, exc: RateLimitError):
    """Handle rate limit errors with retry information"""
    
    request_context = get_request_context(request)
    request_id = request_context.get('request_id', 'unknown')
    
    # Log rate limit hit
    api_logger.warning(
        f"[{request_id}] Rate limit exceeded for {request_context['client_ip']} - "
        f"Endpoint: {request.method} {request.url.path}"
    )
    
    response_content = {
        "success": False,
        "error": exc.detail,
        "error_code": exc.error_code,
        "timestamp": exc.timestamp,
        "request_id": request_id
    }
    
    # Add retry-after header if specified
    headers = {}
    if exc.context.get('retry_after'):
        headers["Retry-After"] = str(exc.context['retry_after'])
        response_content["retry_after"] = exc.context['retry_after']
    
    return JSONResponse(
        status_code=exc.status_code, 
        content=response_content,
        headers=headers
    )

# ==================== CATEGORY ENDPOINTS ====================

@app.get("/categories", response_model=Dict[str, Any], summary="Get categories")
@cached_response(ttl_seconds=600, cache_key_params=['parent_id'])
async def list_categories(
    parent_id: Optional[str] = Query(None, description="Parent category ID to list children for"),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    """Get root categories or children of a category."""
    result = db.list_categories(parent_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/categories", response_model=Dict[str, Any], summary="Create category")
async def create_category(
    category: CategoryCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.add_category(category.dict())
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    invalidate_cache_pattern("list_categories")
    return result

@app.put("/categories/{category_id}", response_model=Dict[str, Any], summary="Update category")
async def update_category_endpoint(
    category_id: str = Path(..., description="Category ID"),
    update: CategoryUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.update_category(category_id, update.dict(exclude_unset=True))
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    invalidate_cache_pattern("list_categories")
    return result

@app.patch("/categories/{category_id}/archive", response_model=Dict[str, Any], summary="Archive category")
async def archive_category_endpoint(
    category_id: str = Path(..., description="Category ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.archive_category(category_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    invalidate_cache_pattern("list_categories")
    return result

# ==================== CART ENDPOINTS ====================

@app.get("/cart", response_model=Dict[str, Any], summary="Get my cart")
async def get_my_cart(
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.get_user_cart(current_user['id'])
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/cart/items", response_model=Dict[str, Any], summary="Add item to cart")
async def add_cart_item(
    item: CartItemAdd,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.add_item_to_cart(current_user['id'], item.dict())
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.patch("/cart/items/{product_id}", response_model=Dict[str, Any], summary="Update cart item")
async def update_cart_item_endpoint(
    product_id: str = Path(..., description="Product ID"),
    update: CartItemUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.update_cart_item(current_user['id'], product_id, update.dict(exclude_unset=True))
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.delete("/cart/items/{product_id}", response_model=Dict[str, Any], summary="Remove cart item")
async def remove_cart_item_endpoint(
    product_id: str = Path(..., description="Product ID"),
    variant_id: Optional[str] = Query(None, description="Variant ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.remove_item_from_cart(current_user['id'], product_id, variant_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/cart/clear", response_model=Dict[str, Any], summary="Clear cart")
async def clear_cart_endpoint(
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.clear_cart(current_user['id'])
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== REVIEW ENDPOINTS ====================

@app.get("/products/{product_id}/reviews", response_model=Dict[str, Any], summary="Get product reviews")
@cached_response(ttl_seconds=300, cache_key_params=['product_id', 'limit'])
async def get_product_reviews_endpoint(
    product_id: str = Path(..., description="Product ID"),
    limit: int = Query(20, ge=1, le=100),
    db: FirestoreEcommerceDB = Depends(get_db)
):
    result = db.get_product_reviews(product_id, status='approved', limit=limit)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/reviews", response_model=Dict[str, Any], summary="Submit review")
async def submit_review_endpoint(
    review: ReviewCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    if review.user_id != current_user['id'] and current_user.get('role') != 'admin':
        raise AuthorizationError("You can only submit reviews as yourself")
    result = db.submit_review(review.dict())
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    invalidate_cache_pattern("get_product_reviews_endpoint")
    return result

@app.get("/users/{user_id}/reviews", response_model=Dict[str, Any], summary="Get my reviews")
async def get_user_reviews_endpoint(
    user_id: str = Path(..., description="User ID"),
    limit: int = Query(20, ge=1, le=100),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    validate_user_access(current_user, user_id)
    result = db.get_user_reviews(user_id, limit=limit)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.put("/reviews/{review_id}", response_model=Dict[str, Any], summary="Update review")
async def update_review_endpoint(
    review_id: str = Path(..., description="Review ID"),
    update: ReviewUpdate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.update_review(review_id, update.dict(exclude_unset=True), current_user['id'])
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/reviews/{review_id}/moderate", response_model=Dict[str, Any], summary="Moderate review")
async def moderate_review_endpoint(
    review_id: str = Path(..., description="Review ID"),
    data: ReviewModerate = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_manager_or_admin)
):
    result = db.moderate_review(review_id, data.action, admin['id'], data.notes)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== NOTIFICATIONS ENDPOINTS ====================

@app.get("/notifications", response_model=Dict[str, Any], summary="Get my notifications")
async def get_notifications(
    unread_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    last_doc_id: Optional[str] = Query(None),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.get_user_notifications(current_user['id'], unread_only, limit, last_doc_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/notifications", response_model=Dict[str, Any], summary="Create notification")
async def create_notification_endpoint(
    notification: NotificationCreate,
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.create_notification(notification.dict())
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.patch("/notifications/{notification_id}/read", response_model=Dict[str, Any], summary="Mark notification read")
async def mark_notification_read_endpoint(
    notification_id: str = Path(..., description="Notification ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    result = db.mark_notification_read(notification_id, current_user['id'])
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== INVENTORY AND WAREHOUSES ENDPOINTS ====================

@app.post("/inventory", response_model=Dict[str, Any], summary="Add inventory record")
async def add_inventory_record_endpoint(
    payload: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    result = db.add_inventory_record(payload)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.patch("/inventory/adjust", response_model=Dict[str, Any], summary="Adjust inventory quantities")
async def adjust_inventory_endpoint(
    product_id: str = Body(...),
    warehouse_id: str = Body(...),
    quantity_change: int = Body(...),
    movement_type: str = Body(...),
    notes: Optional[str] = Body(None),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    result = db.update_inventory_quantities(product_id, warehouse_id, quantity_change, movement_type, notes)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/inventory/products/{product_id}", response_model=Dict[str, Any], summary="Get product inventory")
async def get_product_inventory_endpoint(
    product_id: str = Path(..., description="Product ID"),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    result = db.get_product_inventory(product_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/inventory/low-stock", response_model=Dict[str, Any], summary="Get low stock items")
async def get_low_stock_items_endpoint(
    limit: int = Query(50, ge=1, le=100),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_manager_or_admin)
):
    result = db.get_low_stock_items(limit)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/warehouses", response_model=Dict[str, Any], summary="List warehouses")
async def list_warehouses_endpoint(
    active_only: bool = Query(True),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    result = db.list_warehouses(active_only)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.post("/warehouses", response_model=Dict[str, Any], summary="Create warehouse")
async def create_warehouse_endpoint(
    payload: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.create_warehouse(payload)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/warehouses/{warehouse_id}", response_model=Dict[str, Any], summary="Get warehouse details")
async def get_warehouse_details_endpoint(
    warehouse_id: str = Path(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    result = db.get_warehouse_details(warehouse_id)
    if not result['success']:
        raise APIError(404, result['error'], "DATABASE_ERROR")
    return result

@app.put("/warehouses/{warehouse_id}", response_model=Dict[str, Any], summary="Update warehouse")
async def update_warehouse_endpoint(
    warehouse_id: str = Path(...),
    update: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.update_warehouse_details(warehouse_id, update)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== SUPPLIERS ENDPOINTS ====================

@app.post("/suppliers", response_model=Dict[str, Any], summary="Add supplier")
async def add_supplier_endpoint(
    payload: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.add_supplier(payload)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/suppliers", response_model=Dict[str, Any], summary="List suppliers")
async def list_suppliers_endpoint(
    active_only: bool = Query(True),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.list_suppliers(active_only)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

@app.get("/suppliers/{supplier_id}", response_model=Dict[str, Any], summary="Get supplier")
async def get_supplier_endpoint(
    supplier_id: str = Path(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.get_supplier_by_id(supplier_id)
    if not result['success']:
        raise APIError(404, result['error'], "DATABASE_ERROR")
    return result

@app.put("/suppliers/{supplier_id}", response_model=Dict[str, Any], summary="Update supplier")
async def update_supplier_endpoint(
    supplier_id: str = Path(...),
    update: Dict[str, Any] = Body(...),
    db: FirestoreEcommerceDB = Depends(get_db),
    admin = Depends(require_admin)
):
    result = db.update_supplier_info(supplier_id, update)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== DASHBOARD/ANALYTICS ENDPOINTS ====================

@app.get("/dashboard/stats", response_model=Dict[str, Any], summary="Get dashboard stats")
async def get_dashboard_stats_endpoint(
    seller_id: Optional[str] = Query(None),
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_authenticated_user)
):
    # Restrict seller_id to self unless admin
    if seller_id and current_user.get('role') != 'admin' and seller_id != current_user['id']:
        raise AuthorizationError("You can only view your own stats")
    result = db.get_dashboard_stats(seller_id)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

class SalesStatsRequest(BaseModel):
    seller_id: str
    start_date: datetime
    end_date: datetime

@app.post("/dashboard/sales", response_model=Dict[str, Any], summary="Get sales stats")
async def get_sales_stats_endpoint(
    payload: SalesStatsRequest,
    db: FirestoreEcommerceDB = Depends(get_db),
    current_user = Depends(require_seller_or_admin)
):
    # Non-admins can only request their own seller_id
    if current_user.get('role') != 'admin' and payload.seller_id != current_user['id']:
        raise AuthorizationError("You can only view your own sales stats")
    result = db.get_sales_stats(payload.seller_id, payload.start_date, payload.end_date)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    return result

# ==================== HEALTH ENDPOINT ====================

@app.get("/health", response_model=Dict[str, Any], summary="Health check")
async def health_endpoint(db: FirestoreEcommerceDB = Depends(get_db)):
    result = db.health_check()
    if not result['success']:
        raise APIError(503, "Unhealthy", "SERVICE_UNAVAILABLE")
    return result

# ==================== WISHLIST ENDPOINTS ====================

class WishlistItem(BaseModel):
    product_id: str = Field(..., min_length=1)

@app.get("/users/me/wishlist", response_model=Dict[str, Any], summary="Get my wishlist")
async def get_my_wishlist(
    current_user = Depends(require_authenticated_user)
):
    doc = firestore_client.collection('wishlists').document(current_user['id']).get()
    data = doc.to_dict() if doc.exists else {"items": []}
    return create_success_response(data=data)

@app.post("/users/me/wishlist", response_model=Dict[str, Any], summary="Add to wishlist")
async def add_to_wishlist(
    item: WishlistItem,
    current_user = Depends(require_authenticated_user)
):
    ref = firestore_client.collection('wishlists').document(current_user['id'])
    doc = ref.get()
    items = (doc.to_dict() or {}).get('items', []) if doc.exists else []
    if item.product_id not in items:
        items.append(item.product_id)
    ref.set({"user_id": current_user['id'], "items": items, "updatedAt": datetime.now()}, merge=True)
    return create_success_response(message="Added to wishlist")

@app.delete("/users/me/wishlist/{product_id}", response_model=Dict[str, Any], summary="Remove from wishlist")
async def remove_from_wishlist(
    product_id: str = Path(...),
    current_user = Depends(require_authenticated_user)
):
    ref = firestore_client.collection('wishlists').document(current_user['id'])
    doc = ref.get()
    if not doc.exists:
        return create_success_response(message="Wishlist updated")
    items = (doc.to_dict() or {}).get('items', [])
    items = [pid for pid in items if pid != product_id]
    ref.set({"items": items, "updatedAt": datetime.now()}, merge=True)
    return create_success_response(message="Removed from wishlist")

# ==================== ADDRESS BOOK ENDPOINTS ====================

class AddressCreate(BaseModel):
    name: Optional[str]
    street: str
    city: str
    state: Optional[str]
    zip: str
    country: str
    phone: Optional[str]
    is_default: bool = False

class AddressUpdate(BaseModel):
    name: Optional[str]
    street: Optional[str]
    city: Optional[str]
    state: Optional[str]
    zip: Optional[str]
    country: Optional[str]
    phone: Optional[str]
    is_default: Optional[bool]

@app.get("/users/me/addresses", response_model=Dict[str, Any], summary="List my addresses")
async def list_my_addresses(current_user = Depends(require_authenticated_user)):
    col = firestore_client.collection('users').document(current_user['id']).collection('addresses')
    docs = list(col.stream())
    addresses = [{"id": d.id, **d.to_dict()} for d in docs]
    return create_success_response(data=addresses)

@app.post("/users/me/addresses", response_model=Dict[str, Any], summary="Add address")
async def add_address(address: AddressCreate, current_user = Depends(require_authenticated_user)):
    col = firestore_client.collection('users').document(current_user['id']).collection('addresses')
    doc_ref = col.document()
    doc_ref.set({**address.dict(), "createdAt": datetime.now(), "updatedAt": datetime.now()})
    return create_success_response(data={"address_id": doc_ref.id}, message="Address added")

@app.put("/users/me/addresses/{address_id}", response_model=Dict[str, Any], summary="Update address")
async def update_address(address_id: str = Path(...), update: AddressUpdate = Body(...), current_user = Depends(require_authenticated_user)):
    ref = firestore_client.collection('users').document(current_user['id']).collection('addresses').document(address_id)
    if not ref.get().exists:
        raise NotFoundError("Address not found")
    ref.update({**update.dict(exclude_unset=True), "updatedAt": datetime.now()})
    return create_success_response(message="Address updated")

@app.delete("/users/me/addresses/{address_id}", response_model=Dict[str, Any], summary="Delete address")
async def delete_address(address_id: str = Path(...), current_user = Depends(require_authenticated_user)):
    ref = firestore_client.collection('users').document(current_user['id']).collection('addresses').document(address_id)
    if ref.get().exists:
        ref.delete()
    return create_success_response(message="Address deleted")

# ==================== SUPPORT TICKETS (BASIC) ====================

class SupportTicketCreate(BaseModel):
    subject: str
    message: str
    order_id: Optional[str] = None

class SupportTicketUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(open|in_progress|resolved|closed)$')
    admin_notes: Optional[str] = None

@app.post("/support/tickets", response_model=Dict[str, Any], summary="Create support ticket")
async def create_support_ticket(payload: SupportTicketCreate, current_user = Depends(require_authenticated_user)):
    ref = firestore_client.collection('support_tickets').document()
    ref.set({
        **payload.dict(),
        "ticket_id": ref.id,
        "user_id": current_user['id'],
        "status": "open",
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    })
    return create_success_response(data={"ticket_id": ref.id}, message="Ticket created")

@app.get("/support/tickets", response_model=Dict[str, Any], summary="List my tickets")
async def list_my_tickets(current_user = Depends(require_authenticated_user)):
    q = firestore_client.collection('support_tickets').where('user_id', '==', current_user['id'])
    docs = list(q.stream())
    tickets = [d.to_dict() for d in docs]
    return create_success_response(data=tickets)

@app.get("/admin/support/tickets", response_model=Dict[str, Any], summary="List all tickets")
async def list_all_tickets(admin = Depends(require_admin)):
    docs = list(firestore_client.collection('support_tickets').stream())
    tickets = [d.to_dict() for d in docs]
    return create_success_response(data=tickets)

@app.patch("/admin/support/tickets/{ticket_id}", response_model=Dict[str, Any], summary="Update ticket")
async def update_ticket_admin(ticket_id: str = Path(...), update: SupportTicketUpdate = Body(...), admin = Depends(require_admin)):
    ref = firestore_client.collection('support_tickets').document(ticket_id)
    if not ref.get().exists:
        raise NotFoundError("Ticket not found")
    ref.update({**update.dict(exclude_unset=True), "updatedAt": datetime.now()})
    return create_success_response(message="Ticket updated")

# ==================== SHIPPING (BASIC STUBS) ====================

class ShippingRateRequest(BaseModel):
    destination_country: str
    weight_kg: float
    carrier: Optional[str] = None

@app.post("/shipping/rates", response_model=Dict[str, Any], summary="Get shipping rates")
async def get_shipping_rates(payload: ShippingRateRequest):
    base = 5.0
    per_kg = 2.0
    amount = base + max(0.0, payload.weight_kg) * per_kg
    return create_success_response(data={"currency": "USD", "amount": round(amount, 2), "carrier": payload.carrier or "generic"})

@app.get("/shipping/track/{tracking_number}", response_model=Dict[str, Any], summary="Track shipment")
async def track_shipment(tracking_number: str = Path(...)):
    return create_success_response(data={"tracking_number": tracking_number, "status": "in_transit"})

# ==================== PAYMENTS (BASIC STUBS) ====================

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    order_id: Optional[str] = None

@app.post("/payments/intent", response_model=Dict[str, Any], summary="Create payment intent")
async def create_payment_intent(payload: PaymentIntentRequest, current_user = Depends(require_authenticated_user)):
    # Stub: integrate with Stripe/Razorpay in production
    client_secret = f"test_secret_{hashlib.md5(f'{payload.amount}{payload.currency}'.encode()).hexdigest()[:10]}"
    return create_success_response(data={"client_secret": client_secret, "order_id": payload.order_id})

@app.post("/payments/webhook", summary="Payment webhook receiver")
async def payments_webhook(event: Dict[str, Any] = Body(...)):
    api_logger.info(f"Received payment webhook: {event.get('type', 'unknown')}")
    return JSONResponse(status_code=200, content={"received": True})

# ==================== COLLECTIONS AND PRICE RULES ====================

class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    product_ids: List[str] = []
    is_active: bool = True

class CollectionUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    product_ids: Optional[List[str]]
    is_active: Optional[bool]

@app.post("/collections", response_model=Dict[str, Any], summary="Create collection")
async def create_collection_endpoint(payload: CollectionCreate, admin = Depends(require_admin)):
    ref = firestore_client.collection('collections').document()
    data = {**payload.dict(), "collection_id": ref.id, "createdAt": datetime.now(), "updatedAt": datetime.now()}
    ref.set(data)
    return create_success_response(data={"collection_id": ref.id}, message="Collection created")

@app.get("/collections", response_model=Dict[str, Any], summary="List collections")
async def list_collections_endpoint(active_only: bool = Query(True)):
    q = firestore_client.collection('collections')
    if active_only:
        q = q.where('is_active', '==', True)
    docs = list(q.stream())
    return create_success_response(data=[d.to_dict() for d in docs])

@app.put("/collections/{collection_id}", response_model=Dict[str, Any], summary="Update collection")
async def update_collection_endpoint(collection_id: str = Path(...), update: CollectionUpdate = Body(...), admin = Depends(require_admin)):
    ref = firestore_client.collection('collections').document(collection_id)
    if not ref.get().exists:
        raise NotFoundError("Collection not found")
    ref.update({**update.dict(exclude_unset=True), "updatedAt": datetime.now()})
    return create_success_response(message="Collection updated")

class PriceRuleCreate(BaseModel):
    name: str
    type: str = Field(..., pattern=r'^(percentage|fixed)$')
    value: float
    applies_to: str = Field(..., pattern=r'^(product|category|collection|cart)$')
    target_ids: List[str] = []
    active: bool = True

class PriceRuleUpdate(BaseModel):
    name: Optional[str]
    type: Optional[str]
    value: Optional[float]
    applies_to: Optional[str]
    target_ids: Optional[List[str]]
    active: Optional[bool]

@app.post("/price-rules", response_model=Dict[str, Any], summary="Create price rule")
async def create_price_rule(payload: PriceRuleCreate, admin = Depends(require_admin)):
    ref = firestore_client.collection('price_rules').document()
    ref.set({**payload.dict(), "rule_id": ref.id, "createdAt": datetime.now(), "updatedAt": datetime.now()})
    return create_success_response(data={"rule_id": ref.id}, message="Price rule created")

@app.get("/price-rules", response_model=Dict[str, Any], summary="List price rules")
async def list_price_rules(active_only: bool = Query(True), admin = Depends(require_admin)):
    q = firestore_client.collection('price_rules')
    if active_only:
        q = q.where('active', '==', True)
    docs = list(q.stream())
    return create_success_response(data=[d.to_dict() for d in docs])

@app.put("/price-rules/{rule_id}", response_model=Dict[str, Any], summary="Update price rule")
async def update_price_rule(rule_id: str = Path(...), update: PriceRuleUpdate = Body(...), admin = Depends(require_admin)):
    ref = firestore_client.collection('price_rules').document(rule_id)
    if not ref.get().exists:
        raise NotFoundError("Rule not found")
    ref.update({**update.dict(exclude_unset=True), "updatedAt": datetime.now()})
    return create_success_response(message="Price rule updated")

@app.post("/cart/preview-discounts", response_model=Dict[str, Any], summary="Preview cart discounts")
async def preview_cart_discounts(current_user = Depends(require_authenticated_user)):
    cart = firestore_client.collection('carts').document(current_user['id']).get().to_dict() or {}
    rules_docs = list(firestore_client.collection('price_rules').where('active', '==', True).stream())
    total = cart.get('total_amount', 0.0)
    discount = 0.0
    for d in rules_docs:
        rule = d.to_dict()
        if rule.get('applies_to') == 'cart':
            if rule.get('type') == 'percentage':
                discount += total * float(rule.get('value', 0)) / 100.0
            elif rule.get('type') == 'fixed':
                discount += float(rule.get('value', 0))
    discount = max(0.0, min(discount, total))
    return create_success_response(data={"cart_total": total, "discount": round(discount, 2), "payable": round(total - discount, 2)})

# ==================== SEO: SLUGS, SITEMAP, FEEDS ====================

class SlugSetRequest(BaseModel):
    slug: str
    target_type: str = Field(..., pattern=r'^(product|category|collection)$')
    target_id: str

@app.post("/seo/slug", response_model=Dict[str, Any], summary="Set slug mapping")
async def set_slug(payload: SlugSetRequest, admin = Depends(require_admin)):
    # Ensure slug uniqueness
    existing = list(firestore_client.collection('slugs').where('slug', '==', payload.slug).limit(1).get())
    if existing:
        raise ConflictError("Slug already in use")
    ref = firestore_client.collection('slugs').document()
    ref.set({**payload.dict(), "createdAt": datetime.now(), "updatedAt": datetime.now()})
    return create_success_response(message="Slug set")

@app.get("/seo/slug/{slug}", response_model=Dict[str, Any], summary="Resolve slug")
async def resolve_slug(slug: str = Path(...)):
    docs = list(firestore_client.collection('slugs').where('slug', '==', slug).limit(1).get())
    if not docs:
        raise NotFoundError("Slug not found")
    return create_success_response(data=docs[0].to_dict())

from fastapi import Response

@app.get("/sitemap.xml", summary="Sitemap")
async def sitemap_xml() -> Response:
    base = "https://kynora.onrender.com"
    urls = [f"{base}/"]
    # Add product and category URLs if slugs exist
    slug_docs = list(firestore_client.collection('slugs').stream())
    for d in slug_docs:
        s = d.to_dict()
        urls.append(f"{base}/{s.get('target_type','item')}/{s.get('slug')}")
    body = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" \
           "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">" + \
           "".join([f"<url><loc>{u}</loc></url>" for u in urls]) + \
           "</urlset>"
    return Response(content=body, media_type="application/xml")

@app.get("/feeds/products.json", response_model=Dict[str, Any], summary="Products feed")
async def products_feed(db: FirestoreEcommerceDB = Depends(get_db)):
    res = db.get_active_products(limit=100)
    if not res['success']:
        raise APIError(400, res['error'], "DATABASE_ERROR")
    return create_success_response(data=res.get('data', []))

# ==================== CHECKOUT SESSIONS ====================

class CheckoutSessionCreate(BaseModel):
    address_id: Optional[str] = None

@app.post("/checkout/session", response_model=Dict[str, Any], summary="Create checkout session")
async def create_checkout_session(payload: CheckoutSessionCreate, db: FirestoreEcommerceDB = Depends(get_db), current_user = Depends(require_authenticated_user)):
    cart_doc = firestore_client.collection('carts').document(current_user['id']).get()
    cart = cart_doc.to_dict() if cart_doc.exists else None
    if not cart or not cart.get('items'):
        raise ValidationError("Cart is empty")
    session_id = hashlib.md5(f"{current_user['id']}{datetime.now().isoformat()}".encode()).hexdigest()[:16]
    firestore_client.collection('checkout_sessions').document(session_id).set({
        "session_id": session_id,
        "user_id": current_user['id'],
        "cart_snapshot": cart,
        "address_id": payload.address_id,
        "status": "created",
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    })
    return create_success_response(data={"session_id": session_id})

class CheckoutConfirm(BaseModel):
    session_id: str

@app.post("/checkout/confirm", response_model=Dict[str, Any], summary="Confirm checkout session")
async def confirm_checkout(payload: CheckoutConfirm, db: FirestoreEcommerceDB = Depends(get_db), current_user = Depends(require_authenticated_user)):
    sess_ref = firestore_client.collection('checkout_sessions').document(payload.session_id)
    sess = sess_ref.get()
    if not sess.exists:
        raise NotFoundError("Checkout session not found")
    sdata = sess.to_dict()
    if sdata.get('user_id') != current_user['id']:
        raise AuthorizationError("You can only confirm your own session")
    order_payload = {
        "customer_id": current_user['id'],
        "seller_id": sdata['cart_snapshot']['items'][0].get('seller_id') if sdata['cart_snapshot'].get('items') else "",
        "items": sdata['cart_snapshot'].get('items', []),
        "total_amount": sdata['cart_snapshot'].get('total_amount', 0.0),
        "currency": sdata['cart_snapshot'].get('currency', 'USD'),
        "shipping_address": {}
    }
    result = db.create_order(order_payload)
    if not result['success']:
        raise APIError(400, result['error'], "DATABASE_ERROR")
    db.clear_cart(current_user['id'])
    sess_ref.update({"status": "confirmed", "updatedAt": datetime.now(), "order_id": result.get('data', {}).get('order_id')})
    return create_success_response(data={"order_id": result.get('data', {}).get('order_id')}, message="Checkout confirmed")

# ==================== RETURNS / RMA ====================

class ReturnCreate(BaseModel):
    order_id: str
    reason: str
    items: Optional[List[Dict[str, Any]]] = None

class ReturnUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern=r'^(requested|approved|rejected|received|refunded)$')
    admin_notes: Optional[str] = None

@app.post("/returns", response_model=Dict[str, Any], summary="Create return request")
async def create_return(payload: ReturnCreate, current_user = Depends(require_authenticated_user)):
    ref = firestore_client.collection('returns').document()
    ref.set({**payload.dict(), "return_id": ref.id, "user_id": current_user['id'], "status": "requested", "createdAt": datetime.now(), "updatedAt": datetime.now()})
    return create_success_response(data={"return_id": ref.id}, message="Return requested")

@app.get("/returns", response_model=Dict[str, Any], summary="List my returns")
async def list_my_returns(current_user = Depends(require_authenticated_user)):
    docs = list(firestore_client.collection('returns').where('user_id', '==', current_user['id']).stream())
    return create_success_response(data=[d.to_dict() for d in docs])

@app.get("/admin/returns", response_model=Dict[str, Any], summary="List all returns")
async def list_all_returns(admin = Depends(require_admin)):
    docs = list(firestore_client.collection('returns').stream())
    return create_success_response(data=[d.to_dict() for d in docs])

@app.patch("/admin/returns/{return_id}", response_model=Dict[str, Any], summary="Update return")
async def update_return(return_id: str = Path(...), update: ReturnUpdate = Body(...), admin = Depends(require_admin)):
    ref = firestore_client.collection('returns').document(return_id)
    if not ref.get().exists:
        raise NotFoundError("Return not found")
    ref.update({**update.dict(exclude_unset=True), "updatedAt": datetime.now()})
    return create_success_response(message="Return updated")

# ==================== ANALYTICS EVENTS ====================

class AnalyticsEvent(BaseModel):
    event: str
    user_id: Optional[str] = None
    product_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/analytics/events", response_model=Dict[str, Any], summary="Capture analytics event")
async def capture_event(payload: AnalyticsEvent, request: Request, user = Depends(get_optional_user)):
    ref = firestore_client.collection('events').document()
    ref.set({
        **payload.dict(),
        "event_id": ref.id,
        "user_id": (user or {}).get('id') or payload.user_id,
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get('user-agent'),
        "createdAt": datetime.now()
    })
    return create_success_response(message="Event captured")

# ==================== STARTUP EVENT ====================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    global startup_time
    startup_time = datetime.utcnow()
    
    logger.info("FastAPI E-commerce server starting up...")
    
    # Test database connection
    try:
        db = get_db()
        health_result = db.health_check()
        if health_result['success']:
            logger.info("Database connection successful")
        else:
            logger.error(f"Database connection failed: {health_result['error']}")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
    
    # Initialize cache
    cache.clear()
    logger.info("Cache initialized")
    
    logger.info("FastAPI E-commerce server startup complete")


