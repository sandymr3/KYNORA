"""
Utility functions for KYNORA backend
"""
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import hashlib
import json
import re

def generate_id(prefix: str = "") -> str:
    """Generate unique ID with optional prefix"""
    return f"{prefix}{uuid.uuid4().hex[:8]}"

def generate_order_number() -> str:
    """Generate human-readable order number"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:4].upper()
    return f"ORD-{timestamp}-{random_suffix}"

def create_success_response(data: Any = None, message: str = "Success", **kwargs) -> Dict:
    """Create standardized success response"""
    response = {"success": True, "message": message}
    if data is not None:
        response["data"] = data
    # Add any additional fields
    response.update(kwargs)
    return response

def create_error_response(message: str, error_code: str = "ERROR", details: Any = None) -> Dict:
    """Create standardized error response"""
    response = {
        "success": False,
        "message": message,
        "error_code": error_code
    }
    if details:
        response["details"] = details
    return response

def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not text:
        return text
    
    # Remove HTML tags
    text = re.sub(r'<[^>]*>', '', text)
    
    # Escape special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')
    
    return text.strip()

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    # Remove non-digit characters
    digits = re.sub(r'\D', '', phone)
    # Check if it's a valid phone number length (10-15 digits)
    return 10 <= len(digits) <= 15

def calculate_order_total(items: List[Dict], shipping: float = 0, tax_rate: float = 0) -> Dict:
    """Calculate order total with tax and shipping"""
    subtotal = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
    tax = subtotal * tax_rate
    total = subtotal + tax + shipping
    
    return {
        'subtotal': round(subtotal, 2),
        'tax': round(tax, 2),
        'shipping': round(shipping, 2),
        'total': round(total, 2)
    }

def paginate_query(query, page: int = 1, page_size: int = 20, last_doc_id: str = None):
    """Apply pagination to Firestore query"""
    if last_doc_id:
        # Use cursor-based pagination
        last_doc = query._parent.document(last_doc_id).get()
        if last_doc.exists:
            query = query.start_after(last_doc)
    else:
        # Use offset-based pagination
        offset = (page - 1) * page_size
        if offset > 0:
            query = query.offset(offset)
    
    return query.limit(page_size)

def generate_slug(text: str) -> str:
    """Generate URL-friendly slug from text"""
    # Convert to lowercase
    slug = text.lower()
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove special characters
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_cache_key(endpoint: str, params: Dict) -> str:
    """Generate cache key from endpoint and parameters"""
    sorted_params = json.dumps(params, sort_keys=True, default=str)
    key_string = f"{endpoint}:{sorted_params}"
    return hashlib.md5(key_string.encode()).hexdigest()
