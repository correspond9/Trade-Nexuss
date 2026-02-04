"""
Credentials Model
Handles DhanHQ credential storage and management
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.sql import func
from app.models.base import Base


class DhanCredential(Base):
    """DhanHQ credential storage model"""
    __tablename__ = "dhan_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Authentication mode
    auth_mode = Column(String(20), nullable=False, default="DAILY_TOKEN")  # DAILY_TOKEN or STATIC_IP
    
    # Daily Token Mode credentials
    client_id = Column(String(50), nullable=True)
    access_token = Column(Text, nullable=True)  # JWT token - stored as text for flexibility
    
    # Static IP Mode credentials  
    api_key = Column(String(100), nullable=True)
    client_secret = Column(String(100), nullable=True)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default credentials for the user
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<DhanCredential(id={self.id}, user_id={self.user_id}, auth_mode={self.auth_mode})>"


class CredentialLog(Base):
    """Credential usage and error logging"""
    __tablename__ = "credential_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    credential_id = Column(Integer, nullable=False, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    
    # Log details
    action = Column(String(50), nullable=False)  # CONNECT, DISCONNECT, ERROR, etc.
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED, ERROR
    message = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<CredentialLog(id={self.id}, action={self.action}, status={self.status})>"
