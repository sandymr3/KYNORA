# KYNORA E-commerce API

A comprehensive FastAPI-based e-commerce platform with Firebase Firestore backend, providing complete functionality for online marketplace operations.

## 🚀 Quick Start

### Prerequisites
- Python 3.11.9 or higher
- Firebase project with Firestore enabled
- Firebase service account credentials
- Git (for cloning the repository)

### Installation

#### 1. Clone the Repository
```bash
git clone <repository-url>
cd kynora-ecommerce-api
```

#### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### Environment Setup

#### 1. Firebase Project Setup
1. Create a Firebase project at https://console.firebase.google.com
2. Enable Firestore Database
3. Create a service account:
   - Go to Project Settings > Service Accounts
   - Click "Generate new private key"
   - Download the JSON file

#### 2. Environment Configuration
Create a `.env` file in the project root with your Firebase credentials:

```bash
# Firebase Configuration
FIRESTORE_PROJECT_ID=your-project-id
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY_HERE\n-----END PRIVATE KEY-----\n"
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

#### 3. Firestore Security Rules
Configure Firestore security rules in the Firebase Console:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
      allow read: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role in ['admin'];
    }
    
    // Products are publicly readable, sellers/admins can write
    match /products/{productId} {
      allow read: if true;
      allow write: if request.auth != null && 
        (get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role in ['seller', 'admin'] ||
         resource.data.seller_id == request.auth.uid);
    }
    
    // Orders are private to customer/seller/admin
    match /orders/{orderId} {
      allow read, write: if request.auth != null && 
        (resource.data.customer_id == request.auth.uid ||
         resource.data.seller_id == request.auth.uid ||
         get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin');
    }
    
    // Categories are publicly readable, admin can write
    match /categories/{categoryId} {
      allow read: if true;
      allow write: if request.auth != null && 
        get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role == 'admin';
    }
    
    // Reviews are publicly readable for approved reviews
    match /reviews/{reviewId} {
      allow read: if resource.data.status == 'approved';
      allow write: if request.auth != null && 
        (request.auth.uid == resource.data.user_id ||
         get(/databases/$(database)/documents/users/$(request.auth.uid)).data.role in ['admin']);
    }
  }
}
```

### Running the Server

#### Development Mode
```bash
# Start with auto-reload for development
uvicorn fastapi_ecommerce_server:app --reload --host 0.0.0.0 --port 8000

# Or use the provided start script
python start_server.py
```

#### Production Mode
```bash
# Start with optimized settings for production
uvicorn fastapi_ecommerce_server:app --host 0.0.0.0 --port 8000 --workers 4
```

### Verify Installation
```bash
# Check API health
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 📚 Documentation

### Complete Documentation Files
- **[API Documentation](api_documentation.md)** - Complete API reference with examples
- **[Usage Examples](api_usage_examples.py)** - Realistic usage scenarios and code examples
- **[Testing Guide](endpoint_testing_guide.md)** - Comprehensive testing procedures
- **[Performance Optimizations](performance_optimizations_summary.md)** - Performance features and optimizations

### Quick Links
- [Authentication Setup](#authentication-setup)
- [API Endpoints Overview](#api-endpoints-overview)
- [Usage Examples](#usage-examples)
- [Testing Guide](#testing-guide)
- [Deployment Guide](#deployment-guide)

## 📋 API Endpoints Overview

### 🔐 Authentication Endpoints

#### `GET /auth/me`
**Description**: Get current authenticated user's profile  
**Security**: Requires Firebase ID token  
**Response**: User profile data including role, preferences, and account details

#### `POST /auth/test`
**Description**: Test authentication functionality  
**Security**: Requires Firebase ID token  
**Response**: Confirmation of successful authentication with basic user info

---

### 👥 User Management Endpoints

#### `POST /users`
**Description**: Create a new user profile  
**Security**: Authenticated users only  
**Body**: User data including email, name, role, phone, address, preferences  
**Response**: Created user ID and success confirmation

#### `GET /users/{user_id}`
**Description**: Retrieve user profile by ID  
**Security**: Users can access own profile, admins can access any  
**Response**: Complete user profile data

#### `PUT /users/{user_id}`
**Description**: Update user profile information  
**Security**: Users can update own profile, admins can update any  
**Body**: Updated user data (name, phone, address, preferences)  
**Response**: Update confirmation

#### `GET /users`
**Description**: Get users filtered by role (admin only)  
**Security**: Admin access required  
**Query Params**: `role`, `limit`, `last_doc_id` (pagination)  
**Response**: List of users with specified role

#### `PATCH /users/{user_id}/deactivate`
**Description**: Deactivate a user account  
**Security**: Admin only  
**Response**: Deactivation confirmation

---

### 🛍️ Product Management Endpoints

#### `POST /products`
**Description**: Add a new product to the catalog  
**Security**: Sellers and admins only  
**Body**: Product details (title, description, price, category, images, specifications, inventory)  
**Response**: Created product ID

#### `GET /products/{product_id}`
**Description**: Get detailed product information  
**Security**: Public access  
**Query Params**: `increment_view` (boolean) - whether to increment view count  
**Response**: Complete product data including specifications and images

#### `PUT /products/{product_id}`
**Description**: Update product details  
**Security**: Product owner or admin  
**Body**: Updated product data  
**Response**: Update confirmation

#### `GET /products`
**Description**: Get products with advanced filtering  
**Security**: Public access  
**Query Params**: 
- `category_id` - Filter by category
- `subcategory_id` - Filter by subcategory  
- `seller_id` - Filter by seller
- `min_price`, `max_price` - Price range filter
- `tags` - Comma-separated tags
- `limit`, `last_doc_id` - Pagination
**Response**: Filtered product list with pagination info

#### `GET /products/active`
**Description**: Get all active products  
**Security**: Public access  
**Query Params**: `limit`, `last_doc_id`  
**Response**: List of active products

#### `GET /products/featured`
**Description**: Get featured products  
**Security**: Public access  
**Query Params**: `limit`  
**Response**: List of featured products

#### `GET /products/search`
**Description**: Search products by keywords  
**Security**: Public access  
**Query Params**: `q` (search query), `limit`  
**Response**: Matching products based on title/description

#### `GET /products/popular`
**Description**: Get popular products by sales or views  
**Security**: Public access  
**Query Params**: `metric` (sales/views), `limit`  
**Response**: Popular products sorted by specified metric

#### `PATCH /products/{product_id}/archive`
**Description**: Archive or deactivate a product  
**Security**: Product owner or admin  
**Query Params**: `status` (archived/inactive)  
**Response**: Archive confirmation

#### `PUT /products/batch`
**Description**: Batch update multiple products  
**Security**: Admin or seller  
**Body**: Array of product updates  
**Response**: Batch operation results

---

### 📦 Order Management Endpoints

#### `POST /orders`
**Description**: Create a new order  
**Security**: Authenticated users only  
**Body**: Order details (customer_id, seller_id, items, total_amount, addresses, payment info)  
**Response**: Created order ID and order number

#### `GET /orders/{order_id}`
**Description**: Get order details by ID  
**Security**: Customer can access own orders, seller can access their orders, admin can access all  
**Query Params**: `include_items`, `include_timeline` (booleans)  
**Response**: Complete order data with optional items and timeline

#### `GET /users/{user_id}/orders`
**Description**: Get all orders for a specific user  
**Security**: Users can access own orders only  
**Query Params**: `limit`, `last_doc_id`  
**Response**: User's order history with pagination

#### `GET /sellers/{seller_id}/orders`
**Description**: Get all orders for a specific seller  
**Security**: Sellers can access own orders only  
**Query Params**: `limit`, `last_doc_id`  
**Response**: Seller's order list with pagination

#### `PATCH /orders/{order_id}/status`
**Description**: Update order status and fulfillment details  
**Security**: Seller or admin only  
**Body**: New status and fulfillment details (tracking, carrier info)  
**Response**: Status update confirmation

#### `PATCH /orders/{order_id}/cancel`
**Description**: Cancel an order with reason  
**Security**: Customer can cancel pending orders, admin can cancel any  
**Body**: Cancellation reason and optional refund amount  
**Response**: Cancellation confirmation

#### `POST /orders/{order_id}/timeline`
**Description**: Add a timeline event to an order  
**Security**: Seller or admin only  
**Body**: Event name and details  
**Response**: Timeline event creation confirmation

---

### 🏷️ Category Management Endpoints

#### `GET /categories`
**Description**: List all categories or subcategories  
**Security**: Public access  
**Query Params**: `parent_id` (optional) - get subcategories of parent  
**Response**: Hierarchical category list

#### `POST /categories`
**Description**: Add a new category  
**Security**: Admin only  
**Body**: Category data (name, description, parent_id, image_url, sort_order, SEO data)  
**Response**: Created category ID

#### `PUT /categories/{category_id}`
**Description**: Update category information  
**Security**: Admin only  
**Body**: Updated category data  
**Response**: Update confirmation

#### `PATCH /categories/{category_id}/archive`
**Description**: Archive a category (soft delete)  
**Security**: Admin only  
**Response**: Archive confirmation

---

### 📊 Inventory Management Endpoints

#### `POST /inventory`
**Description**: Add new inventory record for a product at a warehouse  
**Security**: Seller or admin only  
**Body**: Inventory data (product_id, warehouse_id, stock levels, thresholds)  
**Response**: Created inventory record ID

#### `PATCH /inventory/{product_id}/{warehouse_id}`
**Description**: Update inventory quantities with movement tracking  
**Security**: Seller or admin only  
**Body**: Quantity change, movement type, notes  
**Response**: Inventory update confirmation

#### `GET /products/{product_id}/inventory`
**Description**: Get inventory for a product across all warehouses  
**Security**: Seller can view own products, admin can view all  
**Response**: Complete inventory data with total stock

#### `GET /inventory/low-stock`
**Description**: Get items with low stock levels  
**Security**: Seller can view own products, admin can view all  
**Query Params**: `limit`  
**Response**: List of low stock items with current levels

#### `GET /warehouses/{warehouse_id}/inventory`
**Description**: Get all inventory for a specific warehouse  
**Security**: Warehouse staff or admin only  
**Query Params**: `limit`, `last_doc_id`  
**Response**: Warehouse inventory with pagination

---

### 🏢 Warehouse Management Endpoints

#### `POST /warehouses`
**Description**: Create a new warehouse  
**Security**: Admin only  
**Body**: Warehouse data (name, address, contact info, capacity, manager)  
**Response**: Created warehouse ID

#### `GET /warehouses`
**Description**: List all warehouses  
**Security**: Admin or warehouse staff  
**Query Params**: `active_only` (boolean)  
**Response**: List of warehouses

#### `GET /warehouses/{warehouse_id}`
**Description**: Get detailed warehouse information  
**Security**: Admin or warehouse staff  
**Response**: Complete warehouse data

#### `PUT /warehouses/{warehouse_id}`
**Description**: Update warehouse details  
**Security**: Admin only  
**Body**: Updated warehouse data  
**Response**: Update confirmation

---

### 🛒 Shopping Cart Endpoints

#### `POST /users/{user_id}/cart/initialize`
**Description**: Initialize a shopping cart for a user  
**Security**: Users can only initialize own cart  
**Response**: Cart initialization confirmation

#### `POST /users/{user_id}/cart/items`
**Description**: Add an item to the shopping cart  
**Security**: Users can only modify own cart  
**Body**: Item data (product_id, variant_id, quantity, price, attributes)  
**Response**: Item addition confirmation

#### `DELETE /users/{user_id}/cart/items/{product_id}`
**Description**: Remove an item from the cart  
**Security**: Users can only modify own cart  
**Query Params**: `variant_id` (optional)  
**Response**: Item removal confirmation

#### `PUT /users/{user_id}/cart/items/{product_id}`
**Description**: Update cart item quantity or variant  
**Security**: Users can only modify own cart  
**Body**: Updated item data  
**Response**: Item update confirmation

#### `GET /users/{user_id}/cart`
**Description**: Get user's current cart contents  
**Security**: Users can only access own cart  
**Response**: Complete cart data with items and totals

#### `DELETE /users/{user_id}/cart`
**Description**: Clear/empty the entire cart  
**Security**: Users can only clear own cart  
**Response**: Cart clear confirmation

---

### ⭐ Review Management Endpoints

#### `POST /reviews`
**Description**: Submit a product review  
**Security**: Authenticated users only, must have purchased product  
**Body**: Review data (product_id, user_id, rating, title, content, images)  
**Response**: Created review ID

#### `GET /products/{product_id}/reviews`
**Description**: Get all reviews for a product  
**Security**: Public access for approved reviews  
**Query Params**: `status`, `limit`, `last_doc_id`  
**Response**: Product reviews with pagination

#### `GET /users/{user_id}/reviews`
**Description**: Get all reviews by a specific user  
**Security**: Users can access own reviews only  
**Query Params**: `limit`, `last_doc_id`  
**Response**: User's reviews with pagination

#### `PUT /reviews/{review_id}`
**Description**: Update an existing review  
**Security**: Users can update own reviews within time limit  
**Body**: Updated review data  
**Response**: Review update confirmation

#### `PATCH /reviews/{review_id}/moderate`
**Description**: Moderate a review (approve/reject)  
**Security**: Admin only  
**Body**: Moderation action and notes  
**Response**: Moderation confirmation

---

### 🔔 Notification Endpoints

#### `POST /notifications`
**Description**: Create/send a notification to a user  
**Security**: Admin only  
**Body**: Notification data (user_id, type, title, message, data, channel)  
**Response**: Created notification ID

#### `GET /users/{user_id}/notifications`
**Description**: Get notifications for a user  
**Security**: Users can access own notifications only  
**Query Params**: `unread_only`, `limit`, `last_doc_id`  
**Response**: User notifications with pagination

#### `PATCH /notifications/{notification_id}/read`
**Description**: Mark a notification as read  
**Security**: Users can mark own notifications only  
**Response**: Mark as read confirmation

---

### 🏭 Supplier Management Endpoints

#### `POST /suppliers`
**Description**: Add a new supplier  
**Security**: Admin only  
**Body**: Supplier data (name, contact info, address, payment terms, lead times)  
**Response**: Created supplier ID

#### `PUT /suppliers/{supplier_id}`
**Description**: Update supplier information  
**Security**: Admin only  
**Body**: Updated supplier data  
**Response**: Update confirmation

#### `GET /suppliers`
**Description**: List all suppliers  
**Security**: Admin or manager only  
**Query Params**: `active_only` (boolean)  
**Response**: List of suppliers

#### `GET /suppliers/{supplier_id}`
**Description**: Get detailed supplier information  
**Security**: Admin or manager only  
**Response**: Complete supplier data

---

### 📈 Analytics & Dashboard Endpoints

#### `GET /dashboard/stats`
**Description**: Get dashboard statistics  
**Security**: Admin can see all stats, sellers can see own stats  
**Query Params**: `seller_id` (optional) - for seller-specific stats  
**Response**: Dashboard metrics (orders, products, users, reviews)

#### `GET /sellers/{seller_id}/sales-stats`
**Description**: Get detailed sales statistics for a seller  
**Security**: Sellers can see own stats, admin can see any seller's stats  
**Query Params**: `start_date`, `end_date`  
**Response**: Sales metrics (revenue, orders, items sold, average order value)

#### `GET /analytics/low-stock-alerts`
**Description**: Get real-time low stock alerts  
**Security**: Admin or warehouse staff only  
**Query Params**: `limit`  
**Response**: Critical and warning level stock alerts

---

### 🔧 Utility Endpoints

#### `POST /batch-operations`
**Description**: Perform multiple database operations in a single batch  
**Security**: Admin only  
**Body**: Array of operations (set, update, delete)  
**Response**: Batch operation results

#### `GET /health`
**Description**: Database and API health check  
**Security**: Public access  
**Response**: System health status and database connectivity

---

## 🔒 Security & Authentication

### Firebase Authentication
The API uses Firebase Authentication with ID tokens. Include the token in the Authorization header:
```
Authorization: Bearer <firebase-id-token>
```

### Role-Based Access Control
- **Admin**: Full access to all endpoints
- **Seller**: Can manage own products, inventory, and orders
- **Customer**: Can manage own profile, cart, orders, and reviews
- **Warehouse Staff**: Can manage inventory for assigned warehouses

### Security Features
- JWT token validation
- Role-based permissions
- User data isolation
- Input validation and sanitization
- Rate limiting (recommended for production)

## 📊 Database Collections

### Core Collections
- **users**: User profiles and authentication data
- **products**: Product catalog with specifications and media
- **orders**: Order management with items and timeline
- **categories**: Hierarchical product categorization
- **inventory**: Stock management across warehouses
- **warehouses**: Warehouse information and management
- **carts**: User shopping carts with items
- **reviews**: Product reviews and ratings
- **notifications**: User notifications and alerts
- **suppliers**: Supplier information and management

### Subcollections
- **orders/{order_id}/items**: Order line items
- **orders/{order_id}/timeline**: Order status history
- **inventory/{inventory_id}/movements**: Stock movement history

## 🚀 Deployment

### Environment Variables
Ensure all Firebase configuration variables are set in production:
- `FIRESTORE_PROJECT_ID`
- `FIREBASE_TYPE`
- `FIREBASE_PROJECT_ID`
- `FIREBASE_PRIVATE_KEY_ID`
- `FIREBASE_PRIVATE_KEY`
- `FIREBASE_CLIENT_EMAIL`
- `FIREBASE_CLIENT_ID`
- And other Firebase service account credentials

### Production Considerations
- Enable CORS for your frontend domains
- Implement rate limiting
- Set up monitoring and logging
- Configure Firebase Security Rules
- Enable SSL/TLS
- Set up backup strategies

## 📝 API Response Format

All endpoints return responses in a consistent format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Error description",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## 🔄 Pagination

Endpoints that return lists support cursor-based pagination:
- `limit`: Number of items to return (default varies by endpoint)
- `last_doc_id`: ID of the last document from previous page
- Response includes `has_more` boolean and `last_doc_id` for next page

## 📞 Support

For API support and documentation updates, please refer to the inline code documentation and Swagger UI at `/docs`.

## 🚀 Deployment Guide

### Docker Deployment

#### 1. Create Dockerfile
```dockerfile
FROM python:3.11.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
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

#### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
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

#### 3. Deploy with Docker
```bash
# Build and start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

### Cloud Deployment

#### Render.com Deployment
1. Connect your GitHub repository to Render
2. Create a new Web Service
3. Configure environment variables in Render dashboard
4. Deploy automatically on git push

#### Railway Deployment
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

#### Google Cloud Run
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/kynora-api

# Deploy to Cloud Run
gcloud run deploy kynora-api \
  --image gcr.io/PROJECT_ID/kynora-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Production Configuration

#### Nginx Configuration (nginx.conf)
```nginx
events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";

        # Gzip compression
        gzip on;
        gzip_types text/plain application/json application/javascript text/css;

        location / {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

#### Environment Variables for Production
```bash
# Production environment variables
ENVIRONMENT=production
LOG_LEVEL=WARNING
CACHE_TTL=600
MAX_CONNECTIONS=20

# Security
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CORS_ORIGINS=https://your-frontend.com,https://www.your-frontend.com

# Monitoring
SENTRY_DSN=your-sentry-dsn
NEW_RELIC_LICENSE_KEY=your-newrelic-key
```

### Monitoring and Maintenance

#### Health Monitoring
```bash
# Set up health check monitoring
curl -f https://your-domain.com/health || exit 1

# Monitor logs
tail -f logs/ecommerce_api.log
tail -f logs/ecommerce_errors.log
```

#### Performance Monitoring
- Set up application monitoring (New Relic, DataDog)
- Configure log aggregation (ELK stack, Splunk)
- Set up alerts for errors and performance issues
- Monitor Firebase usage and costs

#### Backup Strategy
- Regular Firestore exports
- Environment configuration backups
- Code repository backups
- SSL certificate backups

### Security Checklist

#### Production Security
- [ ] HTTPS enabled with valid SSL certificates
- [ ] CORS configured for specific domains
- [ ] Rate limiting implemented
- [ ] Web Application Firewall (WAF) configured
- [ ] Security headers configured
- [ ] Input validation and sanitization
- [ ] Regular security updates
- [ ] Firestore security rules configured
- [ ] Service account permissions minimized

#### Monitoring Setup
- [ ] Application performance monitoring
- [ ] Error tracking and alerting
- [ ] Log aggregation and analysis
- [ ] Uptime monitoring
- [ ] Database performance monitoring
- [ ] Security event monitoring

## 🧪 Testing Guide

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
python -m pytest test_endpoints_comprehensive.py -v

# Run specific test categories
python -m pytest test_authentication.py -v
python -m pytest test_database_operations.py -v
python -m pytest test_performance_optimizations.py -v

# Run with coverage
pip install pytest-cov
python -m pytest --cov=. --cov-report=html
```

### Manual Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test with authentication (replace with actual token)
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_FIREBASE_TOKEN"

# Test product search
curl "http://localhost:8000/products/search?q=headphones&limit=5"
```

### Load Testing
```bash
# Install load testing tools
pip install locust

# Run load tests
locust -f load_test.py --host=http://localhost:8000
```

## 🔧 Usage Examples

### Authentication Example
```python
import requests

# Get Firebase ID token (implement based on your auth method)
firebase_token = get_firebase_token()

headers = {
    "Authorization": f"Bearer {firebase_token}",
    "Content-Type": "application/json"
}

# Test authentication
response = requests.get("http://localhost:8000/auth/me", headers=headers)
user_data = response.json()
print(f"Authenticated as: {user_data['data']['name']}")
```

### Product Management Example
```python
# Create a new product (seller/admin only)
product_data = {
    "title": "Premium Wireless Headphones",
    "description": "High-quality wireless headphones with noise cancellation",
    "price": 299.99,
    "category_id": "electronics",
    "seller_id": "seller123",
    "images": ["https://example.com/headphones.jpg"],
    "specifications": {
        "brand": "AudioTech",
        "model": "AT-WH-2024",
        "battery_life": "30 hours"
    }
}

response = requests.post(
    "http://localhost:8000/products",
    headers=headers,
    json=product_data
)
```

### Order Processing Example
```python
# Create an order
order_data = {
    "customer_id": "customer123",
    "seller_id": "seller456",
    "items": [
        {
            "product_id": "prod789",
            "quantity": 1,
            "price": 299.99
        }
    ],
    "total_amount": 299.99,
    "shipping_address": {
        "name": "John Doe",
        "street": "123 Main St",
        "city": "Anytown",
        "state": "CA",
        "zipCode": "12345",
        "country": "US"
    }
}

response = requests.post(
    "http://localhost:8000/orders",
    headers=headers,
    json=order_data
)
```

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints
- Add docstrings for functions and classes
- Write comprehensive tests

### Commit Guidelines
- Use conventional commit messages
- Include tests with new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Getting Help
- Check the [API Documentation](api_documentation.md)
- Review [Usage Examples](api_usage_examples.py)
- Read the [Testing Guide](endpoint_testing_guide.md)
- Open an issue on GitHub

### Common Issues
- **Authentication errors**: Verify Firebase configuration and token format
- **Permission errors**: Check user roles and Firestore security rules
- **Performance issues**: Review caching configuration and database indexes
- **Deployment issues**: Verify environment variables and network configuration

---

**Built with FastAPI, Firebase Firestore, and Python 3.11.9**  
**Version**: 1.0.0  
**Last Updated**: January 2024