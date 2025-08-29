# KYNORA E-commerce API - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
4. [Usage Examples](#usage-examples)
5. [Error Handling](#error-handling)
6. [Testing Guide](#testing-guide)
7. [Deployment Guide](#deployment-guide)

## Overview

The KYNORA E-commerce API is a comprehensive FastAPI-based platform providing complete functionality for online marketplace operations. Built with Firebase Firestore backend, it offers robust authentication, role-based access control, and optimized performance features.

### Key Features
- **Firebase Authentication**: Secure JWT-based authentication
- **Role-Based Access Control**: Admin, Seller, Customer, and Manager roles
- **Performance Optimizations**: Response caching, connection pooling, compression
- **Comprehensive Error Handling**: Standardized error responses with detailed logging
- **Real-time Operations**: Live inventory tracking, order status updates
- **Scalable Architecture**: Designed for high-traffic e-commerce operations

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### API Documentation
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI Schema**: `/openapi.json`

## Authentication

### Firebase ID Token Authentication
All protected endpoints require a Firebase ID token in the Authorization header:

```http
Authorization: Bearer <firebase-id-token>
```

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all endpoints and data |
| **Seller** | Manage own products, inventory, and orders |
| **Customer** | Manage own profile, cart, orders, and reviews |
| **Manager** | Access to analytics and warehouse management |

### Getting Authentication Token

```javascript
// Frontend JavaScript example
import { getAuth, signInWithEmailAndPassword } from 'firebase/auth';

const auth = getAuth();
const userCredential = await signInWithEmailAndPassword(auth, email, password);
const idToken = await userCredential.user.getIdToken();

// Use token in API requests
const response = await fetch('/api/auth/me', {
  headers: {
    'Authorization': `Bearer ${idToken}`,
    'Content-Type': 'application/json'
  }
});
```

## API Endpoints

### Authentication Endpoints

#### GET /auth/me
Get current authenticated user's profile.

**Security**: Requires authentication  
**Response**: User profile with role and preferences

```json
{
  "success": true,
  "data": {
    "id": "user123",
    "email": "user@example.com",
    "name": "John Doe",
    "role": "customer"
  },
  "message": "User profile retrieved successfully",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### POST /auth/test
Test authentication functionality.

**Security**: Requires authentication  
**Response**: Authentication confirmation

### User Management Endpoints

#### POST /users
Create a new user profile.

**Security**: Authenticated users only  
**Request Body**:
```json
{
  "email": "user@example.com",
  "displayName": "John Doe",
  "role": "customer",
  "phone": "+1234567890",
  "address": {
    "street": "123 Main St",
    "city": "Anytown",
    "state": "ST",
    "zipCode": "12345",
    "country": "US"
  },
  "preferences": {
    "currency": "USD",
    "language": "en",
    "notifications": {
      "email": true,
      "sms": false,
      "push": true
    }
  }
}
```

#### GET /users/{user_id}
Retrieve user profile by ID.

**Security**: Users can access own profile, admins can access any  
**Path Parameters**: `user_id` (string) - User identifier

#### PUT /users/{user_id}
Update user profile information.

**Security**: Users can update own profile, admins can update any  
**Path Parameters**: `user_id` (string) - User identifier

### Product Management Endpoints

#### POST /products
Add a new product to the catalog.

**Security**: Sellers and admins only  
**Request Body**:
```json
{
  "title": "Premium Wireless Headphones",
  "description": "High-quality wireless headphones with noise cancellation",
  "price": 299.99,
  "category_id": "electronics",
  "subcategory_id": "audio",
  "seller_id": "seller123",
  "images": [
    "https://example.com/image1.jpg",
    "https://example.com/image2.jpg"
  ],
  "specifications": {
    "brand": "TechBrand",
    "model": "WH-1000XM5",
    "color": "Black",
    "weight": "250g",
    "battery_life": "30 hours"
  },
  "inventory": {
    "stock_quantity": 100,
    "low_stock_threshold": 10,
    "warehouse_id": "warehouse1"
  },
  "tags": ["wireless", "noise-cancelling", "premium"],
  "is_featured": false,
  "status": "active"
}
```

#### GET /products
Get products with advanced filtering.

**Security**: Public access  
**Query Parameters**:
- `category_id` (string, optional) - Filter by category
- `subcategory_id` (string, optional) - Filter by subcategory
- `seller_id` (string, optional) - Filter by seller
- `min_price` (number, optional) - Minimum price filter
- `max_price` (number, optional) - Maximum price filter
- `tags` (string, optional) - Comma-separated tags
- `limit` (integer, optional, default: 20) - Number of results
- `last_doc_id` (string, optional) - Pagination cursor

#### GET /products/{product_id}
Get detailed product information.

**Security**: Public access  
**Path Parameters**: `product_id` (string) - Product identifier  
**Query Parameters**: `increment_view` (boolean, optional) - Increment view count

### Order Management Endpoints

#### POST /orders
Create a new order.

**Security**: Authenticated users only  
**Request Body**:
```json
{
  "customer_id": "user123",
  "seller_id": "seller456",
  "items": [
    {
      "product_id": "prod789",
      "variant_id": "var001",
      "quantity": 2,
      "price": 299.99,
      "attributes": {
        "color": "Black",
        "size": "Medium"
      }
    }
  ],
  "total_amount": 599.98,
  "shipping_address": {
    "name": "John Doe",
    "street": "123 Main St",
    "city": "Anytown",
    "state": "ST",
    "zipCode": "12345",
    "country": "US",
    "phone": "+1234567890"
  },
  "billing_address": {
    "name": "John Doe",
    "street": "123 Main St",
    "city": "Anytown",
    "state": "ST",
    "zipCode": "12345",
    "country": "US"
  },
  "payment_info": {
    "method": "credit_card",
    "transaction_id": "txn_123456789"
  }
}
```

#### GET /orders/{order_id}
Get order details by ID.

**Security**: Customer can access own orders, seller can access their orders, admin can access all  
**Path Parameters**: `order_id` (string) - Order identifier  
**Query Parameters**:
- `include_items` (boolean, optional) - Include order items
- `include_timeline` (boolean, optional) - Include order timeline

#### PATCH /orders/{order_id}/status
Update order status and fulfillment details.

**Security**: Seller or admin only  
**Path Parameters**: `order_id` (string) - Order identifier  
**Request Body**:
```json
{
  "status": "shipped",
  "fulfillment_details": {
    "tracking_number": "TRK123456789",
    "carrier": "FedEx",
    "estimated_delivery": "2024-01-05T00:00:00.000Z",
    "notes": "Package shipped via express delivery"
  }
}
```

### Shopping Cart Endpoints

#### POST /users/{user_id}/cart/items
Add an item to the shopping cart.

**Security**: Users can only modify own cart  
**Path Parameters**: `user_id` (string) - User identifier  
**Request Body**:
```json
{
  "product_id": "prod789",
  "variant_id": "var001",
  "quantity": 2,
  "price": 299.99,
  "attributes": {
    "color": "Black",
    "size": "Medium"
  }
}
```

#### GET /users/{user_id}/cart
Get user's current cart contents.

**Security**: Users can only access own cart  
**Path Parameters**: `user_id` (string) - User identifier

**Response**:
```json
{
  "success": true,
  "data": {
    "user_id": "user123",
    "items": [
      {
        "product_id": "prod789",
        "variant_id": "var001",
        "quantity": 2,
        "price": 299.99,
        "subtotal": 599.98,
        "product_title": "Premium Wireless Headphones",
        "attributes": {
          "color": "Black",
          "size": "Medium"
        }
      }
    ],
    "total_items": 2,
    "total_amount": 599.98,
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T12:00:00.000Z"
  },
  "message": "Cart retrieved successfully",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Category Management Endpoints

#### GET /categories
List all categories or subcategories.

**Security**: Public access  
**Query Parameters**: `parent_id` (string, optional) - Get subcategories of parent

#### POST /categories
Add a new category.

**Security**: Admin only  
**Request Body**:
```json
{
  "name": "Electronics",
  "description": "Electronic devices and accessories",
  "parent_id": null,
  "image_url": "https://example.com/electronics.jpg",
  "sort_order": 1,
  "seo_data": {
    "meta_title": "Electronics - Shop Latest Gadgets",
    "meta_description": "Discover the latest electronic devices and accessories",
    "keywords": ["electronics", "gadgets", "devices"]
  }
}
```

### Review Management Endpoints

#### POST /reviews
Submit a product review.

**Security**: Authenticated users only, must have purchased product  
**Request Body**:
```json
{
  "product_id": "prod789",
  "user_id": "user123",
  "rating": 5,
  "title": "Excellent product!",
  "content": "These headphones exceeded my expectations. Great sound quality and comfort.",
  "images": [
    "https://example.com/review1.jpg"
  ]
}
```

#### GET /products/{product_id}/reviews
Get all reviews for a product.

**Security**: Public access for approved reviews  
**Path Parameters**: `product_id` (string) - Product identifier  
**Query Parameters**:
- `status` (string, optional) - Filter by review status
- `limit` (integer, optional) - Number of results
- `last_doc_id` (string, optional) - Pagination cursor

## Usage Examples

### Complete E-commerce Flow Example

```javascript
// 1. User Authentication
const auth = getAuth();
const userCredential = await signInWithEmailAndPassword(auth, 'user@example.com', 'password');
const idToken = await userCredential.user.getIdToken();

const headers = {
  'Authorization': `Bearer ${idToken}`,
  'Content-Type': 'application/json'
};

// 2. Browse Products
const productsResponse = await fetch('/products?category_id=electronics&limit=10', {
  headers: { 'Content-Type': 'application/json' }
});
const products = await productsResponse.json();

// 3. Add Product to Cart
const cartResponse = await fetch('/users/user123/cart/items', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    product_id: 'prod789',
    quantity: 1,
    price: 299.99
  })
});

// 4. Get Cart Contents
const cartContents = await fetch('/users/user123/cart', { headers });
const cart = await cartContents.json();

// 5. Create Order
const orderResponse = await fetch('/orders', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    customer_id: 'user123',
    seller_id: 'seller456',
    items: cart.data.items,
    total_amount: cart.data.total_amount,
    shipping_address: {
      name: 'John Doe',
      street: '123 Main St',
      city: 'Anytown',
      state: 'ST',
      zipCode: '12345',
      country: 'US'
    },
    payment_info: {
      method: 'credit_card',
      transaction_id: 'txn_123456789'
    }
  })
});

// 6. Track Order
const order = await orderResponse.json();
const orderTracking = await fetch(`/orders/${order.data.id}?include_timeline=true`, {
  headers
});
```

### Seller Management Example

```javascript
// Seller adds a new product
const productData = {
  title: 'Smart Watch Pro',
  description: 'Advanced fitness tracking smartwatch',
  price: 399.99,
  category_id: 'electronics',
  subcategory_id: 'wearables',
  seller_id: 'seller123',
  images: ['https://example.com/watch1.jpg'],
  specifications: {
    brand: 'TechBrand',
    model: 'SW-Pro-2024',
    battery_life: '7 days',
    water_resistance: 'IP68'
  },
  inventory: {
    stock_quantity: 50,
    low_stock_threshold: 5
  },
  tags: ['smartwatch', 'fitness', 'health']
};

const addProductResponse = await fetch('/products', {
  method: 'POST',
  headers,
  body: JSON.stringify(productData)
});

// Check seller orders
const sellerOrders = await fetch('/sellers/seller123/orders?limit=20', {
  headers
});

// Update order status
const statusUpdate = await fetch('/orders/order456/status', {
  method: 'PATCH',
  headers,
  body: JSON.stringify({
    status: 'shipped',
    fulfillment_details: {
      tracking_number: 'TRK789',
      carrier: 'UPS',
      estimated_delivery: '2024-01-05T00:00:00.000Z'
    }
  })
});
```

### Admin Operations Example

```javascript
// Admin creates a new category
const categoryData = {
  name: 'Smart Home',
  description: 'Smart home devices and automation',
  parent_id: 'electronics',
  image_url: 'https://example.com/smarthome.jpg',
  sort_order: 3
};

const categoryResponse = await fetch('/categories', {
  method: 'POST',
  headers,
  body: JSON.stringify(categoryData)
});

// Admin gets all users by role
const customers = await fetch('/users?role=customer&limit=50', {
  headers
});

// Admin moderates a review
const moderateReview = await fetch('/reviews/review789/moderate', {
  method: 'PATCH',
  headers,
  body: JSON.stringify({
    action: 'approve',
    notes: 'Review meets community guidelines'
  })
});

// Admin creates system notification
const notification = await fetch('/notifications', {
  method: 'POST',
  headers,
  body: JSON.stringify({
    user_id: 'user123',
    type: 'system',
    title: 'System Maintenance',
    message: 'Scheduled maintenance on Jan 15th from 2-4 AM EST',
    data: {
      maintenance_window: '2024-01-15T02:00:00.000Z'
    },
    channels: ['email', 'push']
  })
});
```

## Error Handling

### Standard Error Response Format

```json
{
  "success": false,
  "error": "Product not found",
  "error_code": "PRODUCT_NOT_FOUND",
  "status_code": 404,
  "timestamp": "2024-01-01T00:00:00.000Z",
  "context": {
    "product_id": "invalid_id"
  }
}
```

### Common Error Codes

| Error Code | Status | Description |
|------------|--------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | Missing or invalid authentication token |
| `AUTHORIZATION_DENIED` | 403 | Insufficient permissions for operation |
| `VALIDATION_ERROR` | 400 | Request data validation failed |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `DUPLICATE_RESOURCE` | 409 | Resource already exists |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server internal error |

### Validation Error Response

```json
{
  "success": false,
  "error": "Validation failed",
  "error_code": "VALIDATION_ERROR",
  "details": [
    {
      "field": "email",
      "message": "Invalid email format",
      "value": "invalid-email"
    },
    {
      "field": "price",
      "message": "Price must be greater than 0",
      "value": -10
    }
  ],
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Testing Guide

### Running the Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
python -m pytest test_endpoints_comprehensive.py -v

# Run specific test categories
python -m pytest test_authentication.py -v
python -m pytest test_database_operations.py -v
python -m pytest test_performance_optimizations.py -v
```

### Manual API Testing

#### Using curl

```bash
# Test health endpoint
curl -X GET "http://localhost:8000/health"

# Test authentication (replace with actual token)
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"

# Test product search
curl -X GET "http://localhost:8000/products/search?q=headphones&limit=5"

# Test creating a product (requires seller/admin token)
curl -X POST "http://localhost:8000/products" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Product",
    "description": "A test product",
    "price": 99.99,
    "category_id": "electronics",
    "seller_id": "seller123"
  }'
```

#### Using Python requests

```python
import requests

# Base configuration
BASE_URL = "http://localhost:8000"
headers = {
    "Authorization": "Bearer YOUR_FIREBASE_TOKEN",
    "Content-Type": "application/json"
}

# Test authentication
auth_response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
print(f"Auth Status: {auth_response.status_code}")
print(f"User Data: {auth_response.json()}")

# Test product creation
product_data = {
    "title": "API Test Product",
    "description": "Created via API testing",
    "price": 149.99,
    "category_id": "electronics",
    "seller_id": "seller123"
}

product_response = requests.post(
    f"{BASE_URL}/products", 
    headers=headers, 
    json=product_data
)
print(f"Product Creation: {product_response.status_code}")
print(f"Product Data: {product_response.json()}")
```

### Performance Testing

```python
import asyncio
import aiohttp
import time

async def performance_test():
    """Test API performance with concurrent requests"""
    
    async def make_request(session, url):
        start_time = time.time()
        async with session.get(url) as response:
            await response.json()
            return time.time() - start_time
    
    async with aiohttp.ClientSession() as session:
        # Test concurrent product requests
        tasks = []
        for i in range(50):  # 50 concurrent requests
            task = make_request(session, "http://localhost:8000/products/active")
            tasks.append(task)
        
        response_times = await asyncio.gather(*tasks)
        
        print(f"Average response time: {sum(response_times) / len(response_times):.3f}s")
        print(f"Max response time: {max(response_times):.3f}s")
        print(f"Min response time: {min(response_times):.3f}s")

# Run performance test
asyncio.run(performance_test())
```

## Deployment Guide

### Environment Setup

#### Required Environment Variables

```bash
# Firebase Configuration
FIRESTORE_PROJECT_ID=your-project-id
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com
FIREBASE_UNIVERSE_DOMAIN=googleapis.com

# Optional Configuration
LOG_LEVEL=INFO
CACHE_TTL=300
MAX_CONNECTIONS=15
```

### Docker Deployment

#### Dockerfile

```dockerfile
FROM python:3.11.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "fastapi_ecommerce_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FIRESTORE_PROJECT_ID=${FIRESTORE_PROJECT_ID}
      - FIREBASE_TYPE=${FIREBASE_TYPE}
      - FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
      - FIREBASE_PRIVATE_KEY_ID=${FIREBASE_PRIVATE_KEY_ID}
      - FIREBASE_PRIVATE_KEY=${FIREBASE_PRIVATE_KEY}
      - FIREBASE_CLIENT_EMAIL=${FIREBASE_CLIENT_EMAIL}
      - FIREBASE_CLIENT_ID=${FIREBASE_CLIENT_ID}
      - FIREBASE_AUTH_URI=${FIREBASE_AUTH_URI}
      - FIREBASE_TOKEN_URI=${FIREBASE_TOKEN_URI}
      - FIREBASE_AUTH_PROVIDER_X509_CERT_URL=${FIREBASE_AUTH_PROVIDER_X509_CERT_URL}
      - FIREBASE_CLIENT_X509_CERT_URL=${FIREBASE_CLIENT_X509_CERT_URL}
      - FIREBASE_UNIVERSE_DOMAIN=${FIREBASE_UNIVERSE_DOMAIN}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped
```

### Production Deployment Steps

1. **Prepare Environment**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd kynora-ecommerce-api
   
   # Set up environment variables
   cp .env.example .env
   # Edit .env with your Firebase credentials
   ```

2. **Build and Deploy**
   ```bash
   # Using Docker Compose
   docker-compose up -d
   
   # Or using Docker directly
   docker build -t kynora-api .
   docker run -d -p 8000:8000 --env-file .env kynora-api
   ```

3. **Verify Deployment**
   ```bash
   # Check health
   curl http://localhost:8000/health
   
   # Check API documentation
   curl http://localhost:8000/docs
   ```

### Production Considerations

#### Security
- Enable HTTPS with SSL certificates
- Configure CORS for your frontend domains
- Implement rate limiting
- Set up Web Application Firewall (WAF)
- Regular security updates

#### Monitoring
- Set up application monitoring (e.g., New Relic, DataDog)
- Configure log aggregation (e.g., ELK stack)
- Set up alerts for errors and performance issues
- Monitor Firebase usage and costs

#### Performance
- Use a reverse proxy (Nginx) for load balancing
- Enable response compression
- Configure CDN for static assets
- Implement database connection pooling
- Set up caching layers (Redis)

#### Backup and Recovery
- Regular Firestore backups
- Environment configuration backups
- Disaster recovery procedures
- Database migration strategies

---

**API Version**: 1.0.0  
**Last Updated**: January 2024  
**Built with**: FastAPI, Firebase Firestore, Python 3.11.9