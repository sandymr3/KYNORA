# KYNORA E-commerce API

A comprehensive FastAPI-based e-commerce platform with Firebase Firestore backend, providing complete functionality for online marketplace operations.

## 🚀 Quick Start

### Prerequisites
- Python 3.11.9
- Firebase project with Firestore enabled
- Service account credentials

### Installation
```bash
pip install -r requirements.txt
```

### Environment Setup
Configure your `.env` file with Firebase credentials (see `.env` for reference).

### Running the Server
```bash
uvicorn fastapi_ecommerce_server:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📋 API Endpoints Overview

### 🔐 Authentication Endpoints

#### `GET /auth/me`
**Description**: Get current authenticated user's profile  
**Security**: Requires Firebase ID token  
**Response**: User profile data with id, email, name, and role
```json
{
  "id": "string",
  "email": "string", 
  "name": "string",
  "role": "admin" | "seller" | "customer"
}
```

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

Most endpoints return responses in a consistent format:

### Success Response
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation successful",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Authentication Endpoint (`/auth/me`)
Returns user data directly:
```json
{
  "id": "user123",
  "email": "user@example.com",
  "name": "John Doe",
  "role": "customer"
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

---

**Built with FastAPI, Firebase Firestore, and Python 3.11.9**