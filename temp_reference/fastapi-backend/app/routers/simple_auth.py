"""
Simple Authentication Router
Clean, working authentication without circular imports
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import timedelta
from app.services.simple_auth import auth_service

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: dict

class UserInfo(BaseModel):
    id: int
    email: str
    username: str
    firstName: str
    lastName: str
    role: str
    clientID: str
    permissions: dict

@router.post("/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    """Simple login endpoint that just works"""
    
    # Authenticate user
    user = auth_service.authenticate_user(login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = auth_service.create_access_token(user, access_token_expires)
    
    # Return user data
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 1800,  # 30 minutes in seconds
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

@router.get("/me", response_model=UserInfo)
async def get_current_user(token: str):
    """Get current user info from token"""
    
    # Verify token
    payload = auth_service.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user = auth_service.get_user_by_email(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "id": user["id"],
        "email": user["email"],
        "username": user["username"],
        "firstName": user["firstName"],
        "lastName": user["lastName"],
        "role": user["role"],
        "clientID": user["clientID"],
        "permissions": user["permissions"]
    }

@router.get("/users")
async def get_all_users():
    """Get all users (admin only - for now returns all)"""
    users = auth_service.get_all_users()
    return {"users": users}

@router.post("/register")
async def register_user(user_data: dict):
    """Register a new user"""
    success = auth_service.add_user(user_data)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists"
        )
    return {"message": "User created successfully"}
