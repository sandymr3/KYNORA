"""
Configuration settings for KYNORA backend
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Firebase settings
FIREBASE_CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", "serviceAccountKey.json")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "kynora-ecommerce")

# API settings
API_TITLE = "KYNORA E-Commerce API"
API_VERSION = "2.0.0"
API_DESCRIPTION = "Full-featured e-commerce backend with Firebase integration"

# CORS settings
CORS_ORIGINS = ["http://localhost:3000", "http://localhost:3001"]

# Security settings
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Cache settings
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_MAX_SIZE = 1000

# Rate limiting
RATE_LIMIT_REQUESTS = 100
RATE_LIMIT_WINDOW = 60  # seconds
