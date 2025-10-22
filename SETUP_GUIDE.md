# 🚀 KYNORA Backend - Quick Setup Guide

## Current Status

✅ **Backend is running** - Your FastAPI server is up
✅ **Firebase connected** - Using production Firestore
✅ **Database has data** - Products, users, orders, categories all present

---

## 🔧 Component Status

| Component | Status | Notes |
|-----------|--------|-------|
| Python 3.11 | ✅ Installed | - |
| FastAPI & Dependencies | ✅ Installed | - |
| Firebase Admin SDK | ✅ Installed | - |
| Service Account Key | ✅ Present | - |
| Production Firestore | ✅ Connected | - |
| Database Collections | ✅ Populated | Users, products, orders, categories |
| Firestore Indexes | ⚠️ Unknown | Deploy if needed: `python scripts/deploy_indexes.py` |

---

## 🎯 Recommended Next Steps

```bash
# 1. Deploy Firestore indexes (one-time setup)
npm install -g firebase-tools  # If not installed
firebase login                  # If not logged in
python scripts/deploy_indexes.py

# 2. Test your API
# Open: http://localhost:8000/docs
# Try: GET /products/featured
# Try: POST /auth/login with your credentials

# 3. Check database status anytime
python check_database.py
```

---

## 🐛 Common Issues & Solutions

### Issue: "No module named 'dotenv'"
**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Firestore query failed, using sample data"
**Reason:** No data in Firestore or network issue
**Solution:** 
- Check database: `python check_database.py`
- Add more data: `python scripts/setup_firestore.py --seed=true`
- Verify network connection to Firebase

---

## 📊 Database Status Check

To check if your Firestore has data:

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select project: `kynora-ecommerce`
3. Click "Firestore Database"
4. Check for collections:
   - `users`
   - `products`
   - `categories`
   - `orders`
   - `carts`

If empty, run:
```bash
python scripts/setup_firestore.py --seed=true
```

---

## 🚀 Quick Start Commands

```bash
# Option 1: Using batch file
start.bat

# Option 2: Using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# Option 3: With auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📝 Configuration Summary

**Database:** Production Firestore (kynora-ecommerce)
**Backend Port:** 8000
**API Docs:** http://localhost:8000/docs
**Health Check:** http://localhost:8000/health

---

## ✅ Verification Steps

Test if everything works:

1. **Health Check:**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Get Featured Products:**
   ```bash
   curl http://localhost:8000/products/featured
   ```

3. **Login:**
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -H "Content-Type: application/json" \
     -d "{\"email\":\"sandy@gmail.com\",\"password\":\"Sandy@1\"}"
   ```

4. **Check Swagger UI:**
   - Open: http://localhost:8000/docs
   - Try: "GET /products/featured"

---

## 🎓 Additional Resources

- **Firebase Console:** https://console.firebase.google.com
- **Firebase Emulator Docs:** https://firebase.google.com/docs/emulator-suite
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Project README:** See `README.md` for full documentation

---

**Questions?** Check the logs in `kynora.log` or the terminal output for errors.
