# 🔄 KYNORA E-Commerce Backend - Complete Reproduction Guide

This guide will help you reproduce and set up the KYNORA e-commerce backend from scratch on any machine.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Step 1: Environment Setup](#step-1-environment-setup)
- [Step 2: Install Dependencies](#step-2-install-dependencies)
- [Step 3: Firebase Configuration](#step-3-firebase-configuration)
- [Step 4: Cloudinary Setup](#step-4-cloudinary-setup)
- [Step 5: Environment Variables](#step-5-environment-variables)
- [Step 6: Initialize Database](#step-6-initialize-database)
- [Step 7: Deploy Firestore Indexes](#step-7-deploy-firestore-indexes)
- [Step 8: Run the Application](#step-8-run-the-application)
- [Step 9: Verify Setup](#step-9-verify-setup)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Purpose | Download Link |
|----------|----------------|---------|---------------|
| **Python** | 3.11+ | Runtime environment | [python.org](https://www.python.org/downloads/) |
| **pip** | Latest | Package manager | Comes with Python |
| **Git** | 2.0+ | Version control | [git-scm.com](https://git-scm.com/) |
| **Node.js** | 16+ | Firebase CLI | [nodejs.org](https://nodejs.org/) |
| **npm** | 8+ | Package manager | Comes with Node.js |

### Required Accounts

1. **Firebase Account** - [console.firebase.google.com](https://console.firebase.google.com)
2. **Cloudinary Account** - [cloudinary.com](https://cloudinary.com) (Free tier available)

---

## Step 1: Environment Setup

### 1.1 Clone or Download Repository

```bash
# If using Git
git clone <your-repo-url>
cd KYNORA

# Or download and extract the ZIP file
```

### 1.2 Create Python Virtual Environment

**Windows (PowerShell/CMD):**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify activation (you should see (venv) in your prompt)
```

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (you should see (venv) in your prompt)
```

### 1.3 Verify Python Version

```bash
python --version
# Should show Python 3.11.x or higher
```

---

## Step 2: Install Dependencies

### 2.1 Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 2.2 Install All Requirements

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI 0.109.0 - Web framework
- Firebase Admin SDK 6.4.0 - Database & authentication
- Pydantic 2.5.3 - Data validation
- Uvicorn 0.27.0 - ASGI server
- And 20+ other dependencies

### 2.3 Verify Installation

```bash
pip list
# Check that all packages are installed
```

---

## Step 3: Firebase Configuration

### 3.1 Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click **"Add project"** or **"Create a project"**
3. **Project name:** `kynora-ecommerce` (or your preferred name)
4. **Google Analytics:** Enable (optional)
5. Click **"Create project"**

### 3.2 Enable Firestore Database

1. In Firebase Console, navigate to **Build → Firestore Database**
2. Click **"Create database"**
3. **Location:** Choose closest to you (e.g., `us-central1`, `asia-south1`)
4. **Security rules:** Start in **Test mode** (for development)
   ```
   allow read, write: if request.time < timestamp.date(2025, 12, 31);
   ```
5. Click **"Enable"**

### 3.3 Enable Authentication

1. Navigate to **Build → Authentication**
2. Click **"Get started"**
3. Enable **Email/Password** sign-in method
4. Click **"Enable"** → **"Save"**

### 3.4 Generate Service Account Key

1. Click **⚙️ Settings** → **Project settings**
2. Navigate to **"Service accounts"** tab
3. Click **"Generate new private key"**
4. Click **"Generate key"** (JSON file will download)
5. **Important:** Rename downloaded file to `serviceAccountKey.json`
6. Move `serviceAccountKey.json` to project root directory
7. **Security:** Ensure `.gitignore` includes `serviceAccountKey.json`

### 3.5 Note Your Project Details

From the Service Account page, note down:
- **Project ID:** `kynora-ecommerce` (or your chosen name)
- **Client Email:** `firebase-adminsdk-xxxxx@kynora-ecommerce.iam.gserviceaccount.com`

---

## Step 4: Cloudinary Setup

### 4.1 Create Cloudinary Account

1. Go to [cloudinary.com](https://cloudinary.com)
2. Click **"Sign Up for Free"**
3. Complete registration

### 4.2 Get API Credentials

1. After login, you'll see your **Dashboard**
2. Note down these credentials:
   - **Cloud Name:** `dxxxxxxxxx`
   - **API Key:** `123456789012345`
   - **API Secret:** `abcdefghijklmnopqrstuvwxyz123`

---

## Step 5: Environment Variables

### 5.1 Copy Environment Template

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

### 5.2 Edit .env File

Open `.env` in a text editor and update these critical values:

```env
# ============================================
# FIREBASE CONFIGURATION
# ============================================
FIREBASE_PROJECT_ID=kynora-ecommerce
# Note: Other Firebase settings will be read from serviceAccountKey.json

# ============================================
# CLOUDINARY CONFIGURATION
# ============================================
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here

# ============================================
# SECURITY & JWT
# ============================================
JWT_SECRET_KEY=change_this_to_random_32_char_string_in_production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# ADMIN SETTINGS
# ============================================
ADMIN_EMAIL=admin@kynora.com
ADMIN_PASSWORD=Admin@123456
```

### 5.3 Generate Secure JWT Secret

**Using Python:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Using OpenSSL:**
```bash
openssl rand -base64 32
```

Copy the output and paste it as your `JWT_SECRET_KEY`.

---

## Step 6: Initialize Database

### 6.1 Check Current Database Status

```bash
python check_database.py
```

### 6.2 Run Setup Script (If Needed)

If database is empty or you want fresh data:

```bash
python scripts/setup_firestore.py --seed=true
```

This will create:
- ✅ Collections: `users`, `products`, `categories`, `orders`, `carts`, `reviews`
- ✅ Sample admin user
- ✅ Sample products (20+)
- ✅ Sample categories
- ✅ Sample orders

### 6.3 Verify Data in Firebase Console

1. Go to Firebase Console → Firestore Database
2. You should see collections populated with data

---

## Step 7: Deploy Firestore Indexes

Firestore requires composite indexes for complex queries.

### 7.1 Install Firebase CLI

```bash
npm install -g firebase-tools
```

### 7.2 Login to Firebase

```bash
firebase login
```

Follow the browser authentication flow.

### 7.3 Initialize Firebase in Project (First Time Only)

```bash
firebase init
```

- Select **Firestore**
- Use existing project: `kynora-ecommerce`
- Accept default file names

### 7.4 Deploy Indexes

**Option 1: Using Python Script (Recommended)**
```bash
python scripts/deploy_indexes.py
```

**Option 2: Using Firebase CLI**
```bash
firebase deploy --only firestore:indexes
```

**Option 3: Using Windows Batch File**
```bash
deploy_indexes.bat
```

### 7.5 Monitor Index Creation

1. Indexes take 5-15 minutes to build
2. Check status: Firebase Console → Firestore Database → Indexes
3. Wait for all indexes to show **"Enabled"** (green checkmark)

---

## Step 8: Run the Application

### 8.1 Start the Server

**Option 1: Using start script**
```bash
# Windows
start.bat

# Linux/macOS
chmod +x start.sh
./start.sh
```

**Option 2: Using Uvicorn directly**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Option 3: Using Python**
```bash
python main.py
```

### 8.2 Expected Output

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
============================================================
🚀 KYNORA E-Commerce API v2.0.0
============================================================
📚 Swagger UI: http://localhost:8000/docs
📖 ReDoc: http://localhost:8000/redoc
🔥 Firebase: Connected
============================================================
INFO:     Application startup complete.
```

---

## Step 9: Verify Setup

### 9.1 Health Check

Open browser or use curl:

```bash
curl http://localhost:8000/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "api": "KYNORA E-Commerce API",
  "version": "2.0.0",
  "database": "connected",
  "timestamp": "2024-XX-XXTXX:XX:XX.XXXXXX"
}
```

### 9.2 Access API Documentation

Open in browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### 9.3 Test Featured Products Endpoint

```bash
curl http://localhost:8000/products/featured?limit=5
```

### 9.4 Test Authentication

**Register new user:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test@123456",
    "username": "testuser",
    "full_name": "Test User"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@kynora.com",
    "password": "Admin@123456"
  }'
```

Save the `access_token` from the response.

### 9.5 Test Protected Endpoint

```bash
curl http://localhost:8000/cart \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

---

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'XXX'`

**Solution:**
```bash
# Ensure venv is activated
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

---

### Issue: Firebase Connection Failed

**Possible Causes & Solutions:**

1. **Service account key missing**
   ```bash
   # Check if file exists
   ls serviceAccountKey.json  # Linux/Mac
   dir serviceAccountKey.json # Windows
   ```

2. **Wrong project ID in .env**
   - Verify `FIREBASE_PROJECT_ID` matches your Firebase project

3. **Firewall blocking Firebase**
   - Check network/firewall settings
   - Try from different network

---

### Issue: Pydantic Validation Errors

**Cause:** Pydantic v2 has breaking changes from v1.

**Solution:** The updated `requirements.txt` uses Pydantic v2 with compatible syntax.

If you see validation errors:
```bash
pip install --upgrade pydantic pydantic-settings
```

---

### Issue: Port 8000 Already in Use

**Solution 1: Use different port**
```bash
uvicorn main:app --port 8001
```

**Solution 2: Kill existing process**

**Windows:**
```bash
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -ti:8000 | xargs kill -9
```

---

### Issue: Firestore Index Required Error

**Error Message:**
```
The query requires an index. You can create it here: https://console.firebase.google.com/...
```

**Solution:**
1. Click the provided link to create the index
2. Or run: `python scripts/deploy_indexes.py`
3. Wait 5-10 minutes for index to build

---

### Issue: CORS Errors from Frontend

**Solution:** Add your frontend URL to CORS_ORIGINS in `.env`:

```env
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001", "https://yourdomain.com"]
```

Restart the server after changing.

---

## 📁 Project Structure Reference

```
KYNORA/
├── config/                   # Configuration files
│   ├── cloudinary.py        # Cloudinary config
│   ├── firebase.py          # Firebase config (legacy)
│   └── settings.py          # App settings
├── core/                     # Core application logic
│   ├── config.py            # Main configuration
│   ├── database.py          # Database initialization
│   ├── dependencies.py      # FastAPI dependencies
│   └── utils.py             # Utility functions
├── endpoints/               # API endpoint handlers
│   ├── auth.py             # Authentication endpoints
│   ├── cart.py             # Shopping cart endpoints
│   ├── categories.py       # Category endpoints
│   ├── orders.py           # Order endpoints
│   ├── products.py         # Product endpoints
│   ├── reviews.py          # Review endpoints
│   └── users.py            # User endpoints
├── routers/                 # Additional routers
│   ├── newsletter.py       # Newsletter subscription
│   ├── product_comparison.py
│   ├── recently_viewed.py
│   └── wishlist.py
├── models/                  # Pydantic models/schemas
│   ├── cart.py
│   ├── category.py
│   ├── order.py
│   ├── product.py
│   ├── review.py
│   └── user.py
├── services/                # Business logic services
│   ├── cart_service.py
│   └── order_service.py
├── utils/                   # Utility functions
│   ├── auth.py             # JWT & auth helpers
│   ├── helpers.py          # Common utilities
│   └── validators.py       # Custom validators
├── scripts/                 # Setup & maintenance scripts
│   ├── deploy_indexes.py   # Deploy Firestore indexes
│   ├── setup_firestore.py  # Initialize database
│   └── ...
├── middleware/              # Custom middleware
│   └── error_handler.py
├── main.py                  # Application entry point
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── .gitignore              # Git ignore rules
├── serviceAccountKey.json  # Firebase credentials (excluded from git)
├── firebase.json           # Firebase config
├── firestore.indexes.json  # Firestore index definitions
├── firestore.rules         # Firestore security rules
└── README.md               # Documentation
```

---

## 🎯 Quick Command Reference

```bash
# Activate virtual environment
venv\Scripts\activate                    # Windows
source venv/bin/activate                # Linux/Mac

# Install/Update dependencies
pip install -r requirements.txt

# Check database status
python check_database.py

# Seed database with sample data
python scripts/setup_firestore.py --seed=true

# Deploy Firestore indexes
python scripts/deploy_indexes.py

# Run development server
uvicorn main:app --reload

# Run production server
uvicorn main:app --host 0.0.0.0 --port 8000

# Run tests
pytest

# Format code
black .

# Lint code
flake8 .
```

---

## 🔒 Security Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET_KEY` to a strong random value
- [ ] Set `DEBUG=False` in `.env`
- [ ] Update `ADMIN_PASSWORD` to a strong password
- [ ] Configure Firebase Security Rules for production
- [ ] Add production domain to `CORS_ORIGINS`
- [ ] Enable HTTPS
- [ ] Never commit `serviceAccountKey.json` or `.env` to version control
- [ ] Review and restrict Firestore indexes
- [ ] Enable rate limiting
- [ ] Set up monitoring and logging

---

## 📚 Additional Resources

- **FastAPI Documentation:** https://fastapi.tiangolo.com
- **Firebase Admin SDK:** https://firebase.google.com/docs/admin/setup
- **Firestore Documentation:** https://firebase.google.com/docs/firestore
- **Cloudinary Docs:** https://cloudinary.com/documentation
- **Pydantic v2:** https://docs.pydantic.dev/latest/

---

## 💬 Support

For issues:
1. Check the troubleshooting section above
2. Review logs in `kynora.log`
3. Check Firebase Console for database/auth issues
4. Ensure all environment variables are set correctly

---

**🎉 Setup Complete!**

Your KYNORA e-commerce backend should now be fully operational.

Test it at: http://localhost:8000/docs
