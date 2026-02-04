"""
Simple Credentials Router
Clean credential management using file storage (temporary)
"""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Dict, Optional, List
import json
import os
from datetime import datetime

router = APIRouter()

# File-based credential storage (temporary)
CREDENTIALS_FILE = "dhan_credentials.json"

class DhanCredential(BaseModel):
    client_id: str
    access_token: str
    api_key: str
    secret_api: str
    daily_token: str
    auth_mode: str  # "DAILY_TOKEN" or "STATIC_IP"

class CredentialResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

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

# Original endpoints
@router.get("/active", response_model=CredentialResponse)
async def get_active_credentials():
    """Get currently active credentials"""
    try:
        credentials = load_credentials()
        active_mode = credentials.get("active_mode", "DAILY_TOKEN")
        
        if active_mode in credentials:
            cred_data = credentials[active_mode]
            return CredentialResponse(
                success=True,
                message=f"Active credentials for {active_mode}",
                data={
                    "client_id": cred_data.get("client_id", ""),
                    "auth_mode": active_mode,
                    "has_token": bool(cred_data.get("access_token") or cred_data.get("daily_token")),
                    "last_updated": cred_data.get("last_updated", "")
                }
            )
        else:
            return CredentialResponse(
                success=False,
                message="No active credentials found"
            )
    except Exception as e:
        return CredentialResponse(
            success=False,
            message=f"Error loading credentials: {str(e)}"
        )

@router.post("/save", response_model=CredentialResponse)
async def save_credential(credential: DhanCredential):
    """Save credential for specific mode"""
    try:
        credentials = load_credentials()
        
        # Save credential data
        cred_data = {
            "client_id": credential.client_id,
            "access_token": credential.access_token,
            "api_key": credential.api_key,
            "secret_api": credential.secret_api,
            "daily_token": credential.daily_token,
            "auth_mode": credential.auth_mode,
            "last_updated": datetime.now().isoformat()
        }
        
        credentials[credential.auth_mode] = cred_data
        credentials["active_mode"] = credential.auth_mode
        
        if save_credentials(credentials):
            return CredentialResponse(
                success=True,
                message=f"Credentials saved successfully for {credential.auth_mode}",
                data={"auth_mode": credential.auth_mode}
            )
        else:
            return CredentialResponse(
                success=False,
                message="Failed to save credentials"
            )
    except Exception as e:
        return CredentialResponse(
            success=False,
            message=f"Error saving credentials: {str(e)}"
        )

# Frontend-compatible endpoints
@router.get("/dhan/static-ip")
async def get_static_ip_credentials():
    """Get static IP credentials (frontend compatible)"""
    try:
        credentials = load_credentials()
        static_creds = credentials.get("STATIC_IP", {})
        
        return {
            "success": True,
            "data": {
                "client_id": static_creds.get("client_id", ""),
                "api_key": static_creds.get("api_key", ""),
                "last_updated": static_creds.get("last_updated", "")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@router.get("/dhan/daily-token")
async def get_daily_token_credentials():
    """Get daily token credentials (frontend compatible)"""
    try:
        credentials = load_credentials()
        daily_creds = credentials.get("DAILY_TOKEN", {})
        
        return {
            "success": True,
            "data": {
                "client_id": daily_creds.get("client_id", ""),
                "daily_token": daily_creds.get("daily_token", ""),
                "expiry_time": daily_creds.get("last_updated", ""),
                "last_updated": daily_creds.get("last_updated", "")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

# Query parameter endpoints for useAuthSettings.js compatibility
@router.get("/")
async def get_credentials_by_mode(auth_mode: str):
    """Get credentials by auth_mode query parameter (useAuthSettings.js compatible)"""
    try:
        credentials = load_credentials()
        
        if auth_mode == "DAILY_TOKEN":
            daily_creds = credentials.get("DAILY_TOKEN", {})
            if daily_creds:
                return [{
                    "client_id": daily_creds.get("client_id", ""),
                    "access_token": daily_creds.get("access_token", ""),
                    "daily_token": daily_creds.get("daily_token", ""),
                    "auth_mode": "DAILY_TOKEN",
                    "last_updated": daily_creds.get("last_updated", "")
                }]
        elif auth_mode == "STATIC_IP":
            static_creds = credentials.get("STATIC_IP", {})
            if static_creds:
                return [{
                    "client_id": static_creds.get("client_id", ""),
                    "api_key": static_creds.get("api_key", ""),
                    "secret_api": static_creds.get("secret_api", ""),
                    "auth_mode": "STATIC_IP", 
                    "last_updated": static_creds.get("last_updated", "")
                }]
        
        return []
    except Exception as e:
        return []

@router.post("/")
async def save_credentials_root(request: Dict):
    """Save credentials via POST to root path (frontend compatible)"""
    try:
        credentials = load_credentials()
        
        # Determine auth mode from request data
        auth_mode = request.get("auth_mode", "DAILY_TOKEN")
        
        if auth_mode == "DAILY_TOKEN":
            daily_creds = {
                "client_id": request.get("client_id", ""),
                "access_token": request.get("access_token", ""),
                "daily_token": request.get("daily_token", ""),
                "auth_mode": "DAILY_TOKEN",
                "last_updated": datetime.now().isoformat()
            }
            credentials["DAILY_TOKEN"] = daily_creds
        elif auth_mode == "STATIC_IP":
            static_creds = {
                "client_id": request.get("client_id", ""),
                "api_key": request.get("api_key", ""),
                "secret_api": request.get("secret_api", ""),
                "auth_mode": "STATIC_IP",
                "last_updated": datetime.now().isoformat()
            }
            credentials["STATIC_IP"] = static_creds
        
        credentials["active_mode"] = auth_mode
        
        if save_credentials(credentials):
            return {
                "success": True,
                "message": f"{auth_mode} credentials saved successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save credentials"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@router.post("/dhan/static-ip")
async def save_static_ip_credentials(request: Dict):
    """Save static IP credentials (frontend compatible)"""
    try:
        credentials = load_credentials()

        static_creds = {
            "client_id": request.get("client_id", ""),
            "api_key": request.get("api_key", ""),
            "api_secret": request.get("api_secret", ""),
            "auth_mode": "STATIC_IP",
            "last_updated": datetime.now().isoformat()
        }

        credentials["STATIC_IP"] = static_creds
        credentials["active_mode"] = "STATIC_IP"

        if save_credentials(credentials):
            return {
                "success": True,
                "message": "Static IP credentials saved successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save static IP credentials"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@router.post("/dhan/daily-token")
async def save_daily_token_credentials(request: Dict):
    """Save daily token credentials (frontend compatible)"""
    try:
        credentials = load_credentials()

        daily_creds = {
            "client_id": request.get("client_id", ""),
            "authorization_token": request.get("authorization_token", ""),
            "daily_token": request.get("authorization_token", ""),
            "expiry_time": request.get("expiry_time", ""),
            "auth_mode": "DAILY_TOKEN",
            "last_updated": datetime.now().isoformat()
        }

        credentials["DAILY_TOKEN"] = daily_creds
        credentials["active_mode"] = "DAILY_TOKEN"

        if save_credentials(credentials):
            return {
                "success": True,
                "message": "Daily token credentials saved successfully"
            }
        else:
            return {
                "success": False,
                "message": "Failed to save daily token credentials"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@router.post("/switch-mode", response_model=CredentialResponse)
async def switch_auth_mode(mode: str):
    """Switch active authentication mode"""
    try:
        if mode not in ["DAILY_TOKEN", "STATIC_IP"]:
            return CredentialResponse(
                success=False,
                message="Invalid mode. Use DAILY_TOKEN or STATIC_IP"
            )
        
        credentials = load_credentials()
        
        if mode not in credentials:
            return CredentialResponse(
                success=False,
                message=f"No credentials found for {mode}"
            )
        
        credentials["active_mode"] = mode
        
        if save_credentials(credentials):
            return CredentialResponse(
                success=True,
                message=f"Switched to {mode} mode",
                data={"active_mode": mode}
            )
        else:
            return CredentialResponse(
                success=False,
                message="Failed to switch mode"
            )
    except Exception as e:
        return CredentialResponse(
            success=False,
            message=f"Error switching mode: {str(e)}"
        )

@router.get("/modes", response_model=CredentialResponse)
async def get_available_modes():
    """Get available credential modes"""
    try:
        credentials = load_credentials()
        available_modes = []
        
        for mode in ["DAILY_TOKEN", "STATIC_IP"]:
            if mode in credentials:
                available_modes.append({
                    "mode": mode,
                    "has_credentials": True,
                    "client_id": credentials[mode].get("client_id", ""),
                    "last_updated": credentials[mode].get("last_updated", "")
                })
            else:
                available_modes.append({
                    "mode": mode,
                    "has_credentials": False,
                    "client_id": "",
                    "last_updated": ""
                })
        
        return CredentialResponse(
            success=True,
            message="Available modes retrieved",
            data={
                "available_modes": available_modes,
                "active_mode": credentials.get("active_mode", "")
            }
        )
    except Exception as e:
        return CredentialResponse(
            success=False,
            message=f"Error retrieving modes: {str(e)}"
        )

@router.delete("/clear", response_model=CredentialResponse)
async def clear_credentials():
    """Clear all credentials"""
    try:
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
        return CredentialResponse(
            success=True,
            message="All credentials cleared successfully"
        )
    except Exception as e:
        return CredentialResponse(
            success=False,
            message=f"Error clearing credentials: {str(e)}"
        )
