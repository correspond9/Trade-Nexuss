"""
Authentication Service
Handles user authentication and authorization logic
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional

from app.config import settings
from app.models.auth import User, UserCreate, UserInDB

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """Authentication service"""
    
    def __init__(self):
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[UserInDB]:
        """Get user by email"""
        # TODO: Implement database query
        # For now, return mock user
        return UserInDB(
            id=1,
            email=email,
            username="testuser",
            full_name="Test User",
            hashed_password=self.get_password_hash("password"),
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with email and password"""
        user = await self.get_user_by_email(db, email)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> UserInDB:
        """Create new user"""
        hashed_password = self.get_password_hash(user_data.password)
        
        # TODO: Implement database user creation
        # For now, return mock user
        return UserInDB(
            id=1,
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

# Global auth service instance
auth_service = AuthService()
