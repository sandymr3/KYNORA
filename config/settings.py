"""Application Settings Configuration using Pydantic"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    app_name: str = Field(default="Kynora E-Commerce", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    api_base_url: str = Field(default="http://localhost:8000", env="API_BASE_URL")
    frontend_url: str = Field(default="http://localhost:3000", env="FRONTEND_URL")
    
    # Firebase
    firebase_project_id: str = Field(..., env="FIREBASE_PROJECT_ID")
    firebase_private_key_id: str = Field(..., env="FIREBASE_PRIVATE_KEY_ID")
    firebase_private_key: str = Field(..., env="FIREBASE_PRIVATE_KEY")
    firebase_client_email: str = Field(..., env="FIREBASE_CLIENT_EMAIL")
    firebase_client_id: str = Field(..., env="FIREBASE_CLIENT_ID")
    firebase_auth_uri: str = Field(
        default="https://accounts.google.com/o/oauth2/auth", 
        env="FIREBASE_AUTH_URI"
    )
    firebase_token_uri: str = Field(
        default="https://oauth2.googleapis.com/token", 
        env="FIREBASE_TOKEN_URI"
    )
    firebase_auth_provider_cert_url: str = Field(
        default="https://www.googleapis.com/oauth2/v1/certs",
        env="FIREBASE_AUTH_PROVIDER_CERT_URL"
    )
    firebase_client_cert_url: Optional[str] = Field(default=None, env="FIREBASE_CLIENT_CERT_URL")
    firestore_collection_prefix: str = Field(default="kynora_", env="FIRESTORE_COLLECTION_PREFIX")
    firestore_emulator_host: Optional[str] = Field(default=None, env="FIRESTORE_EMULATOR_HOST")
    
    # Cloudinary
    cloudinary_cloud_name: str = Field(..., env="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(..., env="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(..., env="CLOUDINARY_API_SECRET")
    
    # JWT & Security
    jwt_secret_key: str = Field(..., env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    # Admin
    admin_email: str = Field(default="admin@kynora.com", env="ADMIN_EMAIL")
    admin_password: str = Field(default="Admin@123456", env="ADMIN_PASSWORD")
    
    # Redis Cache
    enable_redis_cache: bool = Field(default=False, env="ENABLE_REDIS_CACHE")
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Feature Flags
    enable_payments: bool = Field(default=False, env="ENABLE_PAYMENTS")
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_reviews: bool = Field(default=True, env="ENABLE_REVIEWS")
    enable_wishlist: bool = Field(default=True, env="ENABLE_WISHLIST")
    
    # Email Configuration
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    email_from: str = Field(default="noreply@kynora.com", env="EMAIL_FROM")
    email_from_name: str = Field(default="Kynora", env="EMAIL_FROM_NAME")
    
    # Pagination
    default_page_size: int = Field(default=20, env="DEFAULT_PAGE_SIZE")
    max_page_size: int = Field(default=100, env="MAX_PAGE_SIZE")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="kynora.log", env="LOG_FILE")
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @validator("firebase_private_key", pre=True)
    def format_firebase_private_key(cls, v):
        """Format Firebase private key properly"""
        if v:
            return v.replace("\\n", "\n")
        return v
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string if needed"""
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return [v]
        return v
    
    def get_firebase_credentials(self) -> dict:
        """Get Firebase credentials as dictionary"""
        return {
            "type": "service_account",
            "project_id": self.firebase_project_id,
            "private_key_id": self.firebase_private_key_id,
            "private_key": self.firebase_private_key,
            "client_email": self.firebase_client_email,
            "client_id": self.firebase_client_id,
            "auth_uri": self.firebase_auth_uri,
            "token_uri": self.firebase_token_uri,
            "auth_provider_x509_cert_url": self.firebase_auth_provider_cert_url,
            "client_x509_cert_url": self.firebase_client_cert_url
        }
    
    def get_cloudinary_config(self) -> dict:
        """Get Cloudinary configuration"""
        return {
            "cloud_name": self.cloudinary_cloud_name,
            "api_key": self.cloudinary_api_key,
            "api_secret": self.cloudinary_api_secret
        }
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment.lower() == "production"
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment.lower() in ["development", "dev"]
    
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return self.environment.lower() in ["test", "testing"]


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Returns:
        Settings: Application settings
    """
    return Settings()


# Create a global settings instance
settings = get_settings()
