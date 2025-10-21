"""
KYNORA E-Commerce Backend API (FastAPI)
Main entry point with modular endpoint structure
Run with: py -3.11 -m uvicorn main:app --host 0.0.0.0 --port 8000
Swagger UI: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import RedirectResponse
from fastapi.openapi.utils import get_openapi
import logging

# Import configuration
from core.config import (
    API_TITLE, API_VERSION, API_DESCRIPTION,
    CORS_ORIGINS
)

# Import database initialization
from core.database import initialize_firebase

# Import all endpoint routers
from endpoints import (
    auth,
    users,
    products,
    cart,
    orders,
    reviews,
    categories
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase on startup
logger.info("Initializing Firebase...")
db = initialize_firebase()
if db:
    logger.info("✅ Firebase initialized successfully")
else:
    logger.warning("⚠️ Running without Firebase - using mock data")

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add compression middleware
app.add_middleware(GZipMiddleware, minimum_size=500)

# Include all routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(products.router, prefix="/products", tags=["Products"])
app.include_router(cart.router, prefix="/cart", tags=["Cart"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])
app.include_router(reviews.router, prefix="/reviews", tags=["Reviews"])
app.include_router(categories.router, prefix="/categories", tags=["Categories"])

# Root endpoint - redirect to docs
@app.get("/", include_in_schema=False)
async def root():
    """Redirect to API documentation"""
    return RedirectResponse(url="/docs")

# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    
    health_status = {
        "status": "healthy",
        "api": API_TITLE,
        "version": API_VERSION,
        "database": "connected" if db else "disconnected",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check Firestore connection if available
    if db:
        try:
            # Perform a simple write/read operation
            health_ref = db.collection('_health').document('check')
            health_ref.set({'timestamp': datetime.utcnow()})
            health_status["database_check"] = "passed"
        except Exception as e:
            health_status["database_check"] = f"failed: {str(e)}"
            health_status["status"] = "degraded"
    
    return health_status

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run startup tasks"""
    logger.info("=" * 60)
    logger.info(f"🚀 {API_TITLE} v{API_VERSION}")
    logger.info("=" * 60)
    logger.info("📚 Swagger UI: http://localhost:8000/docs")
    logger.info("📖 ReDoc: http://localhost:8000/redoc")
    logger.info("🔥 Firebase: " + ("Connected" if db else "Not connected (using mock data)"))
    logger.info("=" * 60)

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run cleanup tasks"""
    logger.info("Shutting down API...")

# Helper function to determine public vs protected endpoints
def is_public_endpoint(path: str, method: str = None) -> bool:
    """
    Determine if an endpoint should be public (no authentication required)
    
    Args:
        path: The endpoint path
        method: HTTP method (optional)
    
    Returns:
        bool: True if endpoint should be public, False if protected
    """
    # Normalize path by removing trailing slashes
    normalized_path = path.rstrip('/')
    
    # Define public endpoint patterns
    public_patterns = [
        "/products/featured",
        "/products/popular",
        "/products/search",
        "/products",
        "/categories",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/"
    ]
    
    # Check exact matches first
    if normalized_path in public_patterns:
        return True
    
    # Special cases for specific path patterns
    if normalized_path.startswith("/products/") and method in ["GET", "get", None]:
        # GET /products/{product_id} is public
        path_parts = normalized_path.split("/")
        if len(path_parts) == 3 and path_parts[2]:
            return True
    
    # All /auth/status endpoint is public
    if normalized_path == "/auth/status":
        return True
    
    return False

# Custom OpenAPI schema with BearerAuth security
def custom_openapi():
    """
    Enhanced OpenAPI schema generation with clean authentication structure.
    
    This function ensures:
    1. BearerAuth security scheme is properly configured
    2. Protected endpoints have security requirements
    3. Public endpoints don't have security requirements
    4. Authorization appears as global "Authorize" button in Swagger UI
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
    
    # Configure security schemes with BearerAuth
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Firebase ID Token - Use the global 'Authorize' button to set your token"
        }
    }
    
    # Track statistics
    protected_count = 0
    public_count = 0
    
    # Process each path and operation
    for path, path_item in openapi_schema["paths"].items():
        for method, operation in path_item.items():
            if isinstance(operation, dict):
                # Remove authorization parameters from parameter list
                if "parameters" in operation:
                    operation["parameters"] = [
                        param for param in operation["parameters"]
                        if not (
                            param.get("name") in ["authorization", "Authorization"] and 
                            param.get("in") == "header"
                        )
                    ]
                    # Remove empty parameters list
                    if not operation["parameters"]:
                        del operation["parameters"]
                
                # Determine if endpoint should be public or protected
                if not is_public_endpoint(path, method):
                    # Add security requirement for protected endpoints
                    operation["security"] = [{"BearerAuth": []}]
                    protected_count += 1
                    
                    # Add lock emoji to indicate protected endpoint
                    if "summary" in operation and "🔒" not in operation["summary"]:
                        operation["summary"] = f"🔒 {operation['summary']}"
                else:
                    # Ensure public endpoints don't have security requirements
                    operation.pop("security", None)
                    public_count += 1
                    
                    # Add globe emoji to indicate public endpoint
                    if "summary" in operation and "🌐" not in operation["summary"]:
                        operation["summary"] = f"🌐 {operation['summary']}"
    
    logger.info(f"OpenAPI schema configured: {protected_count} protected, {public_count} public endpoints")
    
    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Apply custom OpenAPI schema
app.openapi = custom_openapi

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
