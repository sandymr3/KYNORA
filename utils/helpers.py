"""Common helper functions"""

import uuid
import string
import random
from datetime import datetime
from typing import Dict, Any, List, Optional
from slugify import slugify


class Helpers:
    """Common helper utilities"""
    
    @staticmethod
    def generate_id(prefix: str = "") -> str:
        """Generate unique ID with optional prefix"""
        unique_id = str(uuid.uuid4())
        if prefix:
            return f"{prefix}_{unique_id}"
        return unique_id
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate human-readable order number"""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{timestamp}-{random_suffix}"
    
    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-friendly slug from title"""
        return slugify(title)
    
    @staticmethod
    def calculate_pagination(total: int, page: int, limit: int) -> Dict[str, Any]:
        """
        Calculate pagination metadata
        
        Args:
            total: Total number of items
            page: Current page number
            limit: Items per page
            
        Returns:
            dict: Pagination metadata
        """
        pages = (total + limit - 1) // limit  # Ceiling division
        has_next = page < pages
        has_prev = page > 1
        
        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
            "has_next": has_next,
            "has_prev": has_prev
        }
    
    @staticmethod
    def format_price(price: float, currency: str = "USD") -> str:
        """Format price with currency"""
        currency_symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "INR": "₹"
        }
        symbol = currency_symbols.get(currency, "$")
        return f"{symbol}{price:,.2f}"
    
    @staticmethod
    def calculate_discount(original: float, discounted: float) -> float:
        """Calculate discount percentage"""
        if original <= 0:
            return 0.0
        discount = ((original - discounted) / original) * 100
        return round(discount, 2)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove special characters
        valid_chars = f"-_.() {string.ascii_letters}{string.digits}"
        sanitized = ''.join(c for c in filename if c in valid_chars)
        sanitized = sanitized.replace(' ', '_')
        return sanitized
    
    @staticmethod
    def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = Helpers.merge_dicts(result[key], value)
            else:
                result[key] = value
        return result
    
    @staticmethod
    def filter_none_values(data: Dict) -> Dict:
        """Remove None values from dictionary"""
        return {k: v for k, v in data.items() if v is not None}
    
    @staticmethod
    def batch_list(items: List, batch_size: int) -> List[List]:
        """Split list into batches"""
        return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
    
    @staticmethod
    def format_datetime(dt: datetime, format: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string"""
        return dt.strftime(format)
    
    @staticmethod
    def calculate_reading_time(text: str, words_per_minute: int = 200) -> int:
        """Calculate reading time in minutes"""
        word_count = len(text.split())
        minutes = word_count / words_per_minute
        return max(1, round(minutes))
