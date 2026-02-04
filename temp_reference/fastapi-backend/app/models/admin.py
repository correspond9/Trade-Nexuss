"""
Admin Models
Pydantic models for admin operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class UserBase(BaseModel):
    """Base user model for admin"""
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    """User creation model for admin"""
    password: str = Field(..., min_length=8)

class UserUpdate(BaseModel):
    """User update model for admin"""
    email: Optional[str] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None

class User(UserBase):
    """User response model"""
    id: int
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

class SystemStats(BaseModel):
    """System statistics model"""
    total_users: int
    active_users: int
    total_orders: int
    total_trades: int
    total_volume: float
    server_uptime: str
    memory_usage: float
    cpu_usage: float

class HealthCheck(BaseModel):
    """Health check model"""
    status: str
    timestamp: datetime
    database_status: str
    websocket_status: str
    external_apis: List[dict]

class AdminLog(BaseModel):
    """Admin log model"""
    id: int
    admin_id: int
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: str
    user_agent: str
    created_at: datetime
