# ⚡ KYNORA Backend - Quick Start (5 Minutes)

This is a condensed version for experienced developers. For detailed setup, see [REPRODUCTION_GUIDE.md](REPRODUCTION_GUIDE.md).

## Prerequisites
- Python 3.11+
- Firebase account with project created
- Cloudinary account
- Node.js (for Firebase CLI)

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install packages
pip install -r requirements.txt
```

### 2. Firebase Setup
1. Create Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
2. Enable Firestore Database (test mode)
3. Enable Email/Password authentication
4. Download service account key → save as `serviceAccountKey.json` in project root

### 3. Configure Environment
```bash
# Copy template
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env and update:
# - FIREBASE_PROJECT_ID
# - CLOUDINARY_CLOUD_NAME
# - CLOUDINARY_API_KEY
# - CLOUDINARY_API_SECRET
# - JWT_SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### 4. Initialize Database
```bash
# Seed database with sample data
python scripts/setup_firestore.py --seed=true

# Verify
python check_database.py
```

### 5. Deploy Indexes (Optional but recommended)
```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Deploy indexes
python scripts/deploy_indexes.py
# Or: firebase deploy --only firestore:indexes
```

### 6. Run Server
```bash
uvicorn main:app --reload
```

### 7. Test
Open http://localhost:8000/docs

## ✅ Verification

**Health Check:**
```bash
curl http://localhost:8000/health
```

**Get Products:**
```bash
curl http://localhost:8000/products/featured
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@kynora.com","password":"Admin@123456"}'
```

## 📚 Default Credentials

**Admin:**
- Email: `admin@kynora.com`
- Password: `Admin@123456`

## 🔗 Important Links

- **API Docs:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Full Setup Guide:** [REPRODUCTION_GUIDE.md](REPRODUCTION_GUIDE.md)
- **Main README:** [README.md](README.md)

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| Module not found | `pip install -r requirements.txt` |
| Firebase connection failed | Check `serviceAccountKey.json` and `FIREBASE_PROJECT_ID` |
| Port 8000 in use | Use `uvicorn main:app --port 8001` |
| Pydantic errors | `pip install --upgrade pydantic pydantic-settings` |

---

**Need help?** See full troubleshooting in [REPRODUCTION_GUIDE.md](REPRODUCTION_GUIDE.md)
