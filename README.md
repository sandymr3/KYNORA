# KYNORA E-Commerce Backend

A modern, scalable e-commerce backend built with FastAPI, Firebase Firestore, and Cloudinary.

## 🚀 Features

- **FastAPI Framework**: Modern, fast, and production-ready
- **Firebase Firestore**: NoSQL database for scalable data storage
- **Firebase Auth**: Secure user authentication
- **Cloudinary**: Image storage and optimization
- **JWT Authentication**: Secure API endpoints
- **Modular Architecture**: Clean, maintainable code structure
- **Type Safety**: Full Pydantic models for data validation
- **API Documentation**: Auto-generated Swagger/OpenAPI docs

## 📁 Project Structure

```
backend/
├── config/              # Configuration files
│   ├── firebase.py      # Firebase initialization
│   ├── cloudinary.py    # Cloudinary setup
│   └── settings.py      # Application settings
├── models/              # Pydantic models/schemas
│   ├── user.py         # User schemas
│   ├── product.py      # Product schemas
│   ├── cart.py         # Cart schemas
│   ├── order.py        # Order schemas
│   └── ...
├── routers/            # API endpoints
│   ├── auth.py         # Authentication routes
│   ├── products.py     # Product routes
│   ├── cart.py         # Cart routes
│   ├── orders.py       # Order routes
│   └── ...
├── services/           # Business logic
│   ├── cart_service.py # Cart operations
│   ├── order_service.py # Order processing
│   └── ...
├── utils/              # Utility functions
│   ├── auth.py         # JWT helpers
│   ├── validators.py   # Input validation
│   └── helpers.py      # Common utilities
├── scripts/            # Setup scripts
│   ├── setup_firestore.py # Database initialization
│   └── deploy_indexes.py  # Firestore index deployment
├── main.py             # Application entry point
├── requirements.txt    # Dependencies
└── .env.example        # Environment template
```

## 🛠️ Setup Instructions

### Prerequisites

- Python 3.11 or higher
- Firebase account with a project
- Cloudinary account
- Node.js (for Firebase CLI)

### Step 1: Clone and Navigate

```bash
cd c:\Users\santh_xhfmz63\Desktop\projects\kynora\backend
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Firebase Setup

#### 4.1 Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Create Project"
3. Name it: `kynora-ecommerce`
4. Enable Google Analytics (optional)

#### 4.2 Enable Firestore

1. In Firebase Console, go to "Firestore Database"
2. Click "Create Database"
3. Choose location (e.g., `us-central1`)
4. Start in **Test Mode** for development
5. Click "Enable"

#### 4.3 Enable Authentication

1. Go to "Authentication"
2. Click "Get Started"
3. Enable Email/Password provider
4. Enable Google OAuth (optional)

#### 4.4 Get Service Account Key

1. Go to Project Settings (gear icon)
2. Click "Service Accounts" tab
3. Click "Generate new private key"
4. Save as `serviceAccountKey.json` in backend folder
5. **IMPORTANT**: Add to `.gitignore` (already included)

### Step 5: Cloudinary Setup

1. Go to [Cloudinary](https://cloudinary.com)
2. Sign up for free account
3. Get your credentials from Dashboard:
   - Cloud Name
   - API Key
   - API Secret

### Step 6: Environment Configuration

```bash
# Copy environment template
cp .env.example .env
```

Edit `.env` file with your credentials:

```env
# Firebase Configuration
FIREBASE_PROJECT_ID=kynora-ecommerce
FIREBASE_PRIVATE_KEY_ID=<from serviceAccountKey.json>
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
FIREBASE_CLIENT_EMAIL=<from serviceAccountKey.json>
FIREBASE_CLIENT_ID=<from serviceAccountKey.json>

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=<your_cloud_name>
CLOUDINARY_API_KEY=<your_api_key>
CLOUDINARY_API_SECRET=<your_api_secret>

# Security
JWT_SECRET_KEY=<generate_a_32_char_random_string>

# Admin
ADMIN_EMAIL=admin@kynora.com
ADMIN_PASSWORD=Admin@123456
```

### Step 7: Initialize Database

```bash
# Run setup script to create collections and sample data
python scripts/setup_firestore.py --seed=true
```

This will create:
- All required collections
- Sample users (admin, customer, seller)
- Sample categories
- Sample products
- Analytics structure

### Step 8: Deploy Firestore Indexes

Firestore requires composite indexes for complex queries. Deploy them using:

```bash
# Windows PowerShell
.\deploy_indexes.ps1

# Windows Command Prompt
deploy_indexes.bat

# Python (cross-platform)
python scripts/deploy_indexes.py

# Dry run (preview without deploying)
python scripts/deploy_indexes.py --dry-run
```

**Prerequisites:**
- Firebase CLI installed: `npm install -g firebase-tools`
- Logged in to Firebase: `firebase login`

Index creation takes several minutes. Check status in [Firebase Console](https://console.firebase.google.com) → Firestore Database → Indexes.

### Step 9: Run the Server

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python main.py
```

The server will start at: http://localhost:8000

### Step 10: Access API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 🔐 Default Credentials

### Admin User
- Email: `admin@kynora.com`
- Password: `Admin@123456`

### Test Customer
- Email: `customer@example.com`
- Password: `Test@123456`

### Test Seller
- Email: `seller@example.com`
- Password: `Test@123456`

## 📚 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login user
- `POST /auth/refresh` - Refresh token
- `GET /auth/me` - Get current user
- `POST /auth/logout` - Logout user

### Products
- `GET /products` - List products
- `GET /products/featured` - Get featured products
- `GET /products/{id}` - Get product details
- `POST /products` - Create product (seller/admin)
- `PUT /products/{id}` - Update product (seller/admin)

### Cart
- `GET /cart` - Get user cart
- `POST /cart/items` - Add item to cart
- `PUT /cart/items/{id}` - Update item quantity
- `DELETE /cart/items/{id}` - Remove item
- `DELETE /cart` - Clear cart
- `GET /cart/summary` - Get cart totals

### Orders
- `POST /orders` - Create order
- `GET /orders` - List user orders
- `GET /orders/{id}` - Get order details
- `PATCH /orders/{id}/cancel` - Cancel order
- `GET /orders/{id}/tracking` - Get tracking info

## 🧪 Testing the API

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Get featured products
curl http://localhost:8000/products/featured

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@kynora.com","password":"Admin@123456"}'
```

### Using HTTPie

```bash
# Install HTTPie
pip install httpie

# Health check
http GET localhost:8000/health

# Get products
http GET localhost:8000/products

# Login
http POST localhost:8000/auth/login \
  email=admin@kynora.com \
  password=Admin@123456
```

## 🐛 Troubleshooting

### Firebase Connection Issues

1. **Check credentials**: Ensure `serviceAccountKey.json` exists
2. **Verify project ID**: Must match Firebase project
3. **Check network**: Firewall might block Firebase

### Port Already in Use

```bash
# Change port in .env or use different port
uvicorn main:app --port 8001
```

### Module Not Found

```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

### Database Not Initialized

```bash
# Run setup script
python scripts/setup_firestore.py --seed=true
```

## 🚀 Deployment

### Option 1: Deploy to Render

1. Push code to GitHub
2. Connect GitHub repo to Render
3. Set environment variables
4. Deploy

### Option 2: Deploy to Railway

1. Install Railway CLI
2. Run `railway login`
3. Run `railway init`
4. Run `railway up`

### Option 3: Deploy to Google Cloud Run

1. Install gcloud CLI
2. Build Docker image
3. Push to Container Registry
4. Deploy to Cloud Run

## 📝 Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `FIREBASE_PROJECT_ID` | Firebase project ID | Yes |
| `FIREBASE_PRIVATE_KEY` | Service account private key | Yes |
| `FIREBASE_CLIENT_EMAIL` | Service account email | Yes |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | Yes |
| `CLOUDINARY_API_KEY` | Cloudinary API key | Yes |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | Yes |
| `JWT_SECRET_KEY` | JWT signing key (32+ chars) | Yes |
| `ENVIRONMENT` | Environment (development/production) | No |
| `DEBUG` | Debug mode (true/false) | No |

## 📄 License

This project is proprietary and confidential.

## 💬 Support

For issues or questions, contact: development@kynora.com

---

**Built with ❤️ by KYNORA Development Team**
