# Firebase Authentication Guide for Frontend Development

## 🎯 Overview

This guide explains how to integrate Firebase token authentication with the FastAPI e-commerce backend. The system uses a **centralized authentication approach** where you set the Firebase ID token once and it automatically works for all protected endpoints.

## 🔐 Authentication System Architecture

### **Two Types of Endpoints**

#### **Public Endpoints (🌐) - No Authentication Required**
These endpoints are accessible without any Firebase token:

```http
GET /products/active          # Get active products
GET /products/featured        # Get featured products  
GET /products/search          # Search products with query
GET /products/popular         # Get popular products
GET /products/{product_id}    # Get specific product details
GET /categories               # Get all product categories
GET /health                   # API health check
```

#### **Protected Endpoints (🔒) - Firebase Token Required**
These endpoints require a valid Firebase ID token in the Authorization header:

```http
# User Authentication & Profile
GET /auth/me                  # Get current user profile
POST /auth/test              # Test authentication status
GET /users/profile           # Get detailed user profile
POST /users/profile          # Update user profile

# Shopping Cart Operations  
GET /users/{user_id}/cart                    # Get user's shopping cart
POST /users/{user_id}/cart/items            # Add item to cart
PUT /users/{user_id}/cart/items/{product_id} # Update cart item quantity
DELETE /users/{user_id}/cart/items/{product_id} # Remove item from cart

# Order Management
POST /orders                 # Create new order
GET /orders/{order_id}       # Get specific order details
GET /users/{user_id}/orders  # Get user's order history

# Product Reviews
POST /reviews                # Create product review
PUT /reviews/{review_id}     # Update existing review
GET /users/{user_id}/reviews # Get user's reviews

# Admin Functions (Admin role required)
GET /users                   # List all users (admin only)
PATCH /users/{user_id}/deactivate # Deactivate user (admin only)
POST /categories             # Create new category (admin only)
PUT /categories/{category_id} # Update category (admin only)

# Seller Functions (Seller/Admin role required)
POST /products               # Create new product (seller/admin)
PUT /products/{product_id}   # Update product (seller/admin)
PATCH /products/{product_id}/archive # Archive product (seller/admin)
```

## 🚀 Frontend Implementation Guide

### **Step 1: Firebase Configuration**

First, set up Firebase in your frontend application:

```javascript
// firebase-config.js
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  // Your Firebase configuration
  apiKey: "your-api-key",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  // ... other config
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

### **Step 2: Create API Client with Centralized Authentication**

```javascript
// api-client.js
import axios from 'axios';

class EcommerceAPI {
  constructor() {
    this.client = axios.create({
      baseURL: 'http://localhost:8001', // Your FastAPI server URL
      headers: {
        'Content-Type': 'application/json'
      }
    });

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          console.error('Authentication required or token expired');
          // Handle authentication error (redirect to login, refresh token, etc.)
        }
        return Promise.reject(error);
      }
    );
  }

  /**
   * Set Firebase ID token for all subsequent requests
   * Call this once after user logs in
   */
  setAuthToken(token) {
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    console.log('✅ Authentication token set globally');
  }

  /**
   * Clear authentication token
   * Call this when user logs out
   */
  clearAuth() {
    delete this.client.defaults.headers.common['Authorization'];
    console.log('🔓 Authentication token cleared');
  }

  // ==================== PUBLIC ENDPOINTS ====================
  // These work without authentication

  async getActiveProducts() {
    const response = await this.client.get('/products/active');
    return response.data;
  }

  async getFeaturedProducts() {
    const response = await this.client.get('/products/featured');
    return response.data;
  }

  async searchProducts(query) {
    const response = await this.client.get('/products/search', {
      params: { q: query }
    });
    return response.data;
  }

  async getCategories() {
    const response = await this.client.get('/categories');
    return response.data;
  }

  async getProduct(productId) {
    const response = await this.client.get(`/products/${productId}`);
    return response.data;
  }

  async healthCheck() {
    const response = await this.client.get('/health');
    return response.data;
  }

  // ==================== PROTECTED ENDPOINTS ====================
  // These require Firebase authentication token

  async getCurrentUser() {
    const response = await this.client.get('/auth/me');
    return response.data;
  }

  async testAuthentication() {
    const response = await this.client.post('/auth/test', {});
    return response.data;
  }

  async getUserProfile() {
    const response = await this.client.get('/users/profile');
    return response.data;
  }

  async updateUserProfile(profileData) {
    const response = await this.client.post('/users/profile', profileData);
    return response.data;
  }

  // Cart Operations
  async getUserCart(userId) {
    const response = await this.client.get(`/users/${userId}/cart`);
    return response.data;
  }

  async addToCart(userId, productId, quantity, price) {
    const response = await this.client.post(`/users/${userId}/cart/items`, {
      product_id: productId,
      quantity: quantity,
      price: price
    });
    return response.data;
  }

  async updateCartItem(userId, productId, quantity) {
    const response = await this.client.put(`/users/${userId}/cart/items/${productId}`, {
      quantity: quantity
    });
    return response.data;
  }

  async removeFromCart(userId, productId) {
    const response = await this.client.delete(`/users/${userId}/cart/items/${productId}`);
    return response.data;
  }

  // Order Operations
  async createOrder(orderData) {
    const response = await this.client.post('/orders', orderData);
    return response.data;
  }

  async getOrder(orderId) {
    const response = await this.client.get(`/orders/${orderId}`);
    return response.data;
  }

  async getUserOrders(userId) {
    const response = await this.client.get(`/users/${userId}/orders`);
    return response.data;
  }

  // Review Operations
  async createReview(reviewData) {
    const response = await this.client.post('/reviews', reviewData);
    return response.data;
  }

  async updateReview(reviewId, reviewData) {
    const response = await this.client.put(`/reviews/${reviewId}`, reviewData);
    return response.data;
  }

  async getUserReviews(userId) {
    const response = await this.client.get(`/users/${userId}/reviews`);
    return response.data;
  }
}

// Export singleton instance
export const api = new EcommerceAPI();
```

### **Step 3: Authentication Hook (React)**

```javascript
// hooks/useAuth.js
import { useEffect, useState } from 'react';
import { auth } from '../firebase-config';
import { api } from '../api-client';

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const unsubscribe = auth.onAuthStateChanged(async (firebaseUser) => {
      setLoading(true);
      setError(null);

      if (firebaseUser) {
        try {
          // Get Firebase ID token
          const token = await firebaseUser.getIdToken();
          
          // Set token globally for all API requests
          api.setAuthToken(token);
          
          // Get user profile from your API
          const userProfile = await api.getCurrentUser();
          setUser(userProfile.user);
          
          console.log('✅ User authenticated successfully');
        } catch (error) {
          console.error('Authentication error:', error);
          setError(error.message);
          api.clearAuth();
          setUser(null);
        }
      } else {
        // User logged out
        api.clearAuth();
        setUser(null);
        console.log('🔓 User logged out');
      }
      
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  const logout = async () => {
    try {
      await auth.signOut();
      api.clearAuth();
      setUser(null);
    } catch (error) {
      console.error('Logout error:', error);
      setError(error.message);
    }
  };

  return { user, loading, error, logout };
};
```

### **Step 4: Token Refresh Management**

```javascript
// hooks/useTokenRefresh.js
import { useEffect } from 'react';
import { auth } from '../firebase-config';
import { api } from '../api-client';

export const useTokenRefresh = () => {
  useEffect(() => {
    const refreshToken = async () => {
      const user = auth.currentUser;
      if (user) {
        try {
          // Force refresh the token (Firebase tokens expire after 1 hour)
          const token = await user.getIdToken(true);
          api.setAuthToken(token);
          console.log('🔄 Token refreshed successfully');
        } catch (error) {
          console.error('Token refresh failed:', error);
        }
      }
    };

    // Refresh token every 50 minutes (before 1-hour expiry)
    const interval = setInterval(refreshToken, 50 * 60 * 1000);
    
    return () => clearInterval(interval);
  }, []);
};
```

### **Step 5: Error Handling Utility**

```javascript
// utils/apiErrorHandler.js
import { auth } from '../firebase-config';
import { api } from '../api-client';

export const handleApiCall = async (apiFunction) => {
  try {
    return await apiFunction();
  } catch (error) {
    if (error.response?.status === 401) {
      // Token expired or invalid - try to refresh
      const user = auth.currentUser;
      if (user) {
        try {
          const newToken = await user.getIdToken(true); // Force refresh
          api.setAuthToken(newToken);
          return await apiFunction(); // Retry the original call
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          // Redirect to login or handle as needed
          window.location.href = '/login';
        }
      } else {
        // User not logged in - redirect to login
        window.location.href = '/login';
      }
    } else if (error.response?.status === 403) {
      // Access denied - user doesn't have required permissions
      throw new Error('You do not have permission to perform this action');
    } else {
      // Other errors
      throw error;
    }
  }
};
```

## 📱 Usage Examples in React Components

### **Public Endpoint Usage (No Auth Required)**

```javascript
// components/ProductList.js
import React, { useEffect, useState } from 'react';
import { api } from '../api-client';

const ProductList = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        // Public endpoint - no authentication needed
        const data = await api.getActiveProducts();
        setProducts(data.products || []);
      } catch (error) {
        console.error('Error fetching products:', error);
        setError('Failed to load products');
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  if (loading) return <div>Loading products...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Active Products</h2>
      {products.map(product => (
        <div key={product.id} className="product-card">
          <h3>{product.title}</h3>
          <p>Price: ${product.price}</p>
          <p>Stock: {product.stock_quantity}</p>
        </div>
      ))}
    </div>
  );
};

export default ProductList;
```

### **Protected Endpoint Usage (Auth Required)**

```javascript
// components/UserCart.js
import React, { useEffect, useState } from 'react';
import { api } from '../api-client';
import { useAuth } from '../hooks/useAuth';
import { handleApiCall } from '../utils/apiErrorHandler';

const UserCart = () => {
  const { user, loading: authLoading } = useAuth();
  const [cart, setCart] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user && user.uid) {
      fetchCart();
    }
  }, [user]);

  const fetchCart = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Protected endpoint - requires authentication
      const data = await handleApiCall(() => api.getUserCart(user.uid));
      setCart(data.cart);
    } catch (error) {
      console.error('Error fetching cart:', error);
      setError('Failed to load cart');
    } finally {
      setLoading(false);
    }
  };

  const addToCart = async (productId, quantity, price) => {
    try {
      // Protected endpoint - requires authentication
      await handleApiCall(() => 
        api.addToCart(user.uid, productId, quantity, price)
      );
      
      // Refresh cart after adding item
      await fetchCart();
    } catch (error) {
      console.error('Error adding to cart:', error);
      setError('Failed to add item to cart');
    }
  };

  const removeFromCart = async (productId) => {
    try {
      // Protected endpoint - requires authentication
      await handleApiCall(() => 
        api.removeFromCart(user.uid, productId)
      );
      
      // Refresh cart after removing item
      await fetchCart();
    } catch (error) {
      console.error('Error removing from cart:', error);
      setError('Failed to remove item from cart');
    }
  };

  if (authLoading) return <div>Checking authentication...</div>;
  if (!user) return <div>Please log in to view your cart</div>;
  if (loading) return <div>Loading cart...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      <h2>Your Shopping Cart</h2>
      {cart && cart.items && cart.items.length > 0 ? (
        <div>
          {cart.items.map(item => (
            <div key={item.product_id} className="cart-item">
              <h4>Product ID: {item.product_id}</h4>
              <p>Quantity: {item.quantity}</p>
              <p>Price: ${item.price}</p>
              <button onClick={() => removeFromCart(item.product_id)}>
                Remove from Cart
              </button>
            </div>
          ))}
          <div className="cart-total">
            <strong>Total: ${cart.total_amount}</strong>
          </div>
        </div>
      ) : (
        <p>Your cart is empty</p>
      )}
    </div>
  );
};

export default UserCart;
```

### **Search Component (Public Endpoint)**

```javascript
// components/ProductSearch.js
import React, { useState } from 'react';
import { api } from '../api-client';

const ProductSearch = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      // Public endpoint - no authentication needed
      const data = await api.searchProducts(query);
      setResults(data.products || []);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search products..."
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {results.length > 0 && (
        <div>
          <h3>Search Results</h3>
          {results.map(product => (
            <div key={product.id} className="search-result">
              <h4>{product.title}</h4>
              <p>${product.price}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ProductSearch;
```

## 🔧 Main App Setup

```javascript
// App.js
import React from 'react';
import { useAuth } from './hooks/useAuth';
import { useTokenRefresh } from './hooks/useTokenRefresh';
import ProductList from './components/ProductList';
import ProductSearch from './components/ProductSearch';
import UserCart from './components/UserCart';

function App() {
  const { user, loading, error, logout } = useAuth();
  
  // Automatically refresh tokens
  useTokenRefresh();

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="App">
      <header>
        <h1>E-commerce Store</h1>
        {user ? (
          <div>
            <span>Welcome, {user.displayName || user.email}!</span>
            <button onClick={logout}>Logout</button>
          </div>
        ) : (
          <div>
            <a href="/login">Login</a>
          </div>
        )}
      </header>

      <main>
        {/* Public components - work without authentication */}
        <ProductSearch />
        <ProductList />
        
        {/* Protected components - require authentication */}
        {user && <UserCart />}
      </main>

      {error && (
        <div className="error-message">
          Error: {error}
        </div>
      )}
    </div>
  );
}

export default App;
```

## ⚠️ Error Response Format

The API returns consistent error responses that you should handle:

### **Missing Authorization (401)**
```json
{
  "success": false,
  "error": "Authorization header missing",
  "error_code": "MISSING_AUTH_HEADER",
  "context": {
    "expected_format": "Bearer <token>"
  }
}
```

### **Invalid Token Format (401)**
```json
{
  "success": false,
  "error": "Invalid authorization header format. Expected 'Bearer <token>'",
  "error_code": "INVALID_AUTH_FORMAT",
  "context": {
    "expected_format": "Bearer <token>"
  }
}
```

### **Expired/Invalid Token (401)**
```json
{
  "success": false,
  "error": "Invalid Firebase ID token",
  "error_code": "INVALID_TOKEN",
  "context": {}
}
```

### **Insufficient Permissions (403)**
```json
{
  "success": false,
  "error": "Admin access required",
  "error_code": "AUTHORIZATION_ERROR",
  "context": {
    "user_id": "user-123",
    "required_role": "admin",
    "user_role": "customer"
  }
}
```

## 🎯 Key Points for Frontend Development

### **✅ Do This:**
1. **Set token once globally** using `api.setAuthToken(token)`
2. **Use public endpoints freely** - no authentication needed
3. **Handle 401 errors** by refreshing the token
4. **Clear token on logout** using `api.clearAuth()`
5. **Refresh tokens periodically** (every 50 minutes)
6. **Use the error handler utility** for consistent error handling

### **❌ Don't Do This:**
1. Don't pass tokens to individual API methods
2. Don't forget to handle token expiration
3. Don't store tokens in localStorage (Firebase handles this)
4. Don't make authenticated calls before setting the token
5. Don't ignore 401/403 error responses

### **🔍 Testing Your Integration:**

1. **Test public endpoints first** - they should work without authentication
2. **Test authentication flow** - login and verify `/auth/me` works
3. **Test protected endpoints** - cart, orders, profile operations
4. **Test error handling** - try accessing protected endpoints without auth
5. **Test token refresh** - wait for token expiration and verify refresh works

## 📚 Additional Resources

- **API Documentation**: `http://localhost:8001/docs`
- **Health Check**: `http://localhost:8001/health`
- **Firebase Auth Documentation**: [Firebase Auth Guide](https://firebase.google.com/docs/auth)

## 🚨 Security Best Practices

1. **Never log tokens** in console or store them in plain text
2. **Use HTTPS** in production
3. **Handle token expiration gracefully**
4. **Validate user permissions** on the client side
5. **Clear tokens completely on logout**
6. **Monitor for authentication errors** and handle them appropriately

---

*This guide provides everything you need to integrate Firebase authentication with the FastAPI e-commerce backend. The centralized token approach ensures clean, maintainable code while maintaining robust security.*