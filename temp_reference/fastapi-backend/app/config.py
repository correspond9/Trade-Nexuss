"""
Application Configuration Settings
Manages all configuration for the Trading Terminal FastAPI application
"""

from pydantic_settings import BaseSettings
from pydantic import validator
from typing import List
import os

class Settings(BaseSettings):
    """Application settings using Pydantic BaseSettings"""
    
    # Application
    app_name: str = "Trading Terminal API"
    app_version: str = "2.0.0"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./databases/trading_terminal.db"
    
    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ]
    
    @validator('cors_origins', pre=True)
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    # Trusted hosts
    trusted_hosts: List[str] = ["localhost", "127.0.0.1", "*"]
    
    # Rate limiting
    rate_limit_per_minute: int = 100
    rate_limit_per_hour: int = 1000
    
    # Dhan API
    dhan_api_base_url: str = "https://api.dhan.co"
    dhan_ws_url: str = "wss://api-feed.dhan.co"
    
    # WebSocket
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 1000
    
    # File paths
    instruments_file: str = "./data/instruments.csv"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Create settings instance
settings = Settings()
