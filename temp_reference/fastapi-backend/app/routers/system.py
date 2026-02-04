"""
System Router
Handles system endpoints
"""

from fastapi import APIRouter, Depends
from datetime import datetime
import psutil
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.dependencies import get_current_active_user

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "service": "Trading Terminal API"
    }

@router.get("/status")
async def get_system_status(
    db: AsyncSession = Depends(get_db)
):
    """Comprehensive system status monitoring - temporarily no auth for testing"""
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get database status
        db_status = await _check_database_status(db)
        
        # Get WebSocket status (mock for now)
        ws_status = await _check_websocket_status()
        
        # Get Dhan API status (mock for now)
        dhan_status = await _check_dhan_status()
        
        # Get authentication status
        auth_status = await _check_auth_status()
        
        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": {
                    "status": db_status["status"],
                    "response_time": f"{db_status['response_time']:.2f}ms"
                },
                "authentication": {
                    "status": auth_status["status"],
                    "response_time": f"{auth_status['response_time']:.2f}ms"
                },
                "websocket": {
                    "status": ws_status["status"],
                    "connections": ws_status["connections"],
                    "message": ws_status["message"]
                },
                "dhan_api": {
                    "status": dhan_status["status"],
                    "message": dhan_status["message"],
                    "error": dhan_status.get("error")
                }
            },
            "system_metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "memory_used_gb": memory.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024.0**3),
                "disk_used_gb": disk.used / (1024.0**3),
                "uptime": _get_uptime()
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

async def _check_database_status(db: AsyncSession) -> dict:
    """Check database connection status"""
    try:
        start_time = datetime.now()
        await db.execute(text("SELECT 1"))
        end_time = datetime.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        
        return {
            "status": "healthy",
            "response_time": response_time
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time": 0,
            "error": str(e)
        }

async def _check_websocket_status() -> dict:
    """Check WebSocket server status"""
    try:
        # Mock WebSocket status - in real implementation, check actual WebSocket server
        return {
            "status": "running",
            "connections": 0,
            "message": "WebSocket server running"
        }
    except Exception as e:
        return {
            "status": "error",
            "connections": 0,
            "message": f"WebSocket error: {str(e)}"
        }

async def _check_dhan_status() -> dict:
    """Check Dhan API connection status"""
    try:
        # Mock Dhan API status - in real implementation, check actual Dhan API
        return {
            "status": "healthy",
            "message": "Dhan API connection stable"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Dhan API error: {str(e)}",
            "error": str(e)
        }

async def _check_auth_status() -> dict:
    """Check authentication system status"""
    try:
        # Mock auth status - in real implementation, check JWT system
        return {
            "status": "healthy",
            "response_time": 25.5
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time": 0,
            "error": str(e)
        }

def _get_uptime() -> str:
    """Get system uptime"""
    try:
        uptime_seconds = psutil.boot_time()
        current_time = datetime.now().timestamp()
        uptime_total = current_time - uptime_seconds
        
        days = int(uptime_total // 86400)
        hours = int((uptime_total % 86400) // 3600)
        minutes = int((uptime_total % 3600) // 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "Unknown"

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Terminal FastAPI API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "status": "/api/v1/status",
            "auth": "/api/v1/auth",
            "trading": "/api/v1/trading",
            "market": "/api/v1/market",
            "portfolio": "/api/v1/portfolio",
            "admin": "/api/v1/admin"
        }
    }
