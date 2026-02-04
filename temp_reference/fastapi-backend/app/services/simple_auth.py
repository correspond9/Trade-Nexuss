"""
Simple Authentication Service
Clean, working authentication without circular imports
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import jwt
from app.config import settings

# Simple user database (can be moved to real database later)
USERS_DB = {
    "admin@example.com": {
        "id": 1,
        "email": "admin@example.com",
        "password_hash": hashlib.sha256("admin123".encode()).hexdigest(),
        "username": "admin",
        "firstName": "Super",
        "lastName": "Admin",
        "role": "SUPER_ADMIN",
        "clientID": "U0000",
        "permissions": {
            "read": True,
            "write": True,
            "admin": True,
            "access_nse_equity": True,
            "access_bse_equity": True,
            "access_nse_derivatives": True,
            "access_bse_derivatives": True,
            "access_mcx_commodities": True
        }
    },
    "ck.nanaiah@example.com": {
        "id": 2,
        "email": "ck.nanaiah@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "username": "ck.nanaiah",
        "firstName": "C.K.",
        "lastName": "Nanaiah",
        "role": "ADMIN",
        "clientID": "U1001",
        "permissions": {
            "read": True,
            "write": True,
            "admin": False,
            "access_nse_equity": True,
            "access_bse_equity": True,
            "access_nse_derivatives": True,
            "access_bse_derivatives": True,
            "access_mcx_commodities": True
        }
    },
    "dhruv@example.com": {
        "id": 3,
        "email": "dhruv@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "username": "dhruv",
        "firstName": "Dhruv",
        "lastName": "Gohil",
        "role": "USER_EQUITY",
        "clientID": "U1002",
        "permissions": {
            "read": True,
            "write": False,
            "admin": False,
            "access_nse_equity": True,
            "access_bse_equity": True,
            "access_nse_derivatives": False,
            "access_bse_derivatives": False,
            "access_mcx_commodities": False
        }
    },
    "equity_derivatives@example.com": {
        "id": 4,
        "email": "equity_derivatives@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "username": "equity_derivatives",
        "firstName": "Rajesh",
        "lastName": "Kumar",
        "role": "USER_EQUITY_DERIVATIVES",
        "clientID": "U1003",
        "permissions": {
            "read": True,
            "write": False,
            "admin": False,
            "access_nse_equity": True,
            "access_bse_equity": True,
            "access_nse_derivatives": True,
            "access_bse_derivatives": True,
            "access_mcx_commodities": False
        }
    },
    "commodity@example.com": {
        "id": 5,
        "email": "commodity@example.com",
        "password_hash": hashlib.sha256("password123".encode()).hexdigest(),
        "username": "commodity",
        "firstName": "Amit",
        "lastName": "Patel",
        "role": "USER_COMMODITY",
        "clientID": "U1004",
        "permissions": {
            "read": True,
            "write": False,
            "admin": False,
            "access_nse_equity": False,
            "access_bse_equity": False,
            "access_nse_derivatives": False,
            "access_bse_derivatives": False,
            "access_mcx_commodities": True
        }
    }
}

class SimpleAuthService:
    """Simple, clean authentication service"""
    
    def __init__(self):
        self.secret_key = settings.secret_key if hasattr(settings, 'secret_key') else "your-secret-key-here"
        self.algorithm = "HS256"
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with email and password"""
        user = USERS_DB.get(email)
        if not user:
            return None
        
        # Verify password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            return None
        
        return user
    
    def create_access_token(self, user_data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = {
            "sub": user_data["email"],
            "role": user_data["role"],
            "user_id": user_data["id"],
            "exp": datetime.utcnow() + (expires_delta or timedelta(minutes=30))
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        return USERS_DB.get(email)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (for admin purposes)"""
        return list(USERS_DB.values())
    
    def add_user(self, user_data: Dict) -> bool:
        """Add a new user (for admin purposes)"""
        email = user_data.get("email")
        if email in USERS_DB:
            return False
        
        user_data["password_hash"] = hashlib.sha256(user_data["password"].encode()).hexdigest()
        user_data["id"] = max([u["id"] for u in USERS_DB.values()]) + 1
        del user_data["password"]  # Remove plain password
        
        USERS_DB[email] = user_data
        return True

# Global instance
auth_service = SimpleAuthService()
