"""
Authentication Router
Handles user authentication and authorization endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from jose import JWTError, jwt

from app.database import get_db
from app.config import settings
from app.models.auth import User, UserCreate, Token, LoginRequest
from app.dependencies import get_current_active_user

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

@router.post("/register", response_model=User)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register a new user"""
    # TODO: Implement user registration logic
    # For now, return a mock user
    return User(
        id=1,
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user and return access token"""
    # TODO: Implement user authentication logic
    # For now, return a mock token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )

@router.post("/login-json")
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with JSON payload"""
    
    # Mock user database (matching frontend credentials)
    mock_users = {
        "admin@example.com": {
            "id": 1,
            "email": "admin@example.com",
            "password": "admin123",
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
            "password": "password123",
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
            "password": "password123",
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
            "password": "password123",
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
            "password": "password123",
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
    
    # Validate credentials
    user = mock_users.get(login_data.email)
    if not user or user["password"] != login_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}, expires_delta=access_token_expires
    )
    
    # Return user data along with token
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.access_token_expire_minutes * 60,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "firstName": user["firstName"],
            "lastName": user["lastName"],
            "role": user["role"],
            "clientID": user["clientID"],
            "permissions": user["permissions"]
        }
    }

@router.get("/me", response_model=User)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information"""
    return current_user

@router.put("/me", response_model=User)
async def update_current_user(
    user_update: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user information"""
    # TODO: Implement user update logic
    return current_user

@router.post("/change-password")
async def change_password(
    old_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    # TODO: Implement password change logic
    return {"message": "Password changed successfully"}

@router.post("/api-keys")
async def create_api_key(
    description: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new API key for external access"""
    # TODO: Implement API key creation logic
    return {
        "api_key": "mock_api_key_" + str(current_user.id),
        "description": description,
        "created_at": datetime.now()
    }

@router.get("/api-keys")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List user API keys"""
    # TODO: Implement API key listing logic
    return []

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt
