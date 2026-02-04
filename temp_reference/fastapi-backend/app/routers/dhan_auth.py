"""
Dhan Auth Router
Handles authentication mode switching for DhanHQ
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict
import json
import os
from datetime import datetime

router = APIRouter()

CREDENTIALS_FILE = "dhan_credentials.json"

class SwitchRequest(BaseModel):
    reason: str

def load_credentials() -> Dict:
    """Load credentials from file"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

def save_credentials(credentials: Dict) -> bool:
    """Save credentials to file"""
    try:
        with open(CREDENTIALS_FILE, 'w') as f:
            json.dump(credentials, f, indent=2)
        return True
    except Exception:
        return False

@router.post("/switch/static-ip")
async def switch_to_static_ip(request: SwitchRequest):
    """Switch to Static IP authentication mode"""
    try:
        credentials = load_credentials()
        
        if "STATIC_IP" not in credentials:
            return {
                "status": "error",
                "message": "No Static IP credentials found. Please save Static IP credentials first."
            }
        
        credentials["active_mode"] = "STATIC_IP"
        credentials["switch_reason"] = request.reason
        credentials["last_switch"] = datetime.now().isoformat()
        
        if save_credentials(credentials):
            return {
                "status": "success",
                "message": "Successfully switched to Static IP mode",
                "active_mode": "STATIC_IP"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to switch mode"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error switching mode: {str(e)}"
        }

@router.post("/switch/daily-token")
async def switch_to_daily_token(request: SwitchRequest):
    """Switch to Daily Token authentication mode"""
    try:
        credentials = load_credentials()
        
        if "DAILY_TOKEN" not in credentials:
            return {
                "status": "error",
                "message": "No Daily Token credentials found. Please save Daily Token credentials first."
            }
        
        credentials["active_mode"] = "DAILY_TOKEN"
        credentials["switch_reason"] = request.reason
        credentials["last_switch"] = datetime.now().isoformat()
        
        if save_credentials(credentials):
            return {
                "status": "success",
                "message": "Successfully switched to Daily Token mode",
                "active_mode": "DAILY_TOKEN"
            }
        else:
            return {
                "status": "error",
                "message": "Failed to switch mode"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error switching mode: {str(e)}"
        }

@router.get("/mode")
async def get_current_mode():
    """Get current authentication mode"""
    try:
        credentials = load_credentials()
        active_mode = credentials.get("active_mode", "DAILY_TOKEN")
        
        return {
            "status": "success",
            "active_mode": active_mode,
            "last_switch": credentials.get("last_switch", ""),
            "switch_reason": credentials.get("switch_reason", "")
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error getting mode: {str(e)}"
        }
