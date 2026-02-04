"""
Settings Management API endpoints
Allows locking, unlocking, and managing persisted settings
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.storage.settings_manager import (
    save_settings, load_settings, lock_settings, unlock_settings,
    clear_settings, get_settings_status, restore_settings_to_database
)

router = APIRouter()


class SettingsLockRequest(BaseModel):
    action: str  # "lock", "unlock", "save", "restore", "clear"


@router.post("/settings/lock")
def lock_current_settings():
    """
    Lock current settings so they auto-restore on every startup.
    Only the daily token needs to be re-entered.
    """
    if lock_settings():
        return {
            "success": True,
            "message": "Settings locked successfully",
            "note": "Settings will auto-restore on startup. Only daily token needs to be entered.",
        }
    raise HTTPException(status_code=500, detail="Failed to lock settings")


@router.post("/settings/unlock")
def unlock_current_settings():
    """
    Unlock settings so they won't auto-restore on startup.
    """
    if unlock_settings():
        return {
            "success": True,
            "message": "Settings unlocked successfully",
        }
    raise HTTPException(status_code=500, detail="Failed to unlock settings")


@router.post("/settings/save")
def save_current_settings():
    """
    Manually save the current working settings.
    """
    if save_settings():
        return {
            "success": True,
            "message": "Settings saved successfully",
        }
    raise HTTPException(status_code=500, detail="Failed to save settings")


@router.post("/settings/restore")
def restore_saved_settings():
    """
    Manually restore saved settings from disk.
    """
    if restore_settings_to_database():
        return {
            "success": True,
            "message": "Settings restored successfully",
        }
    else:
        raise HTTPException(status_code=404, detail="No saved settings found or settings not locked")


@router.post("/settings/clear")
def clear_all_settings():
    """
    Permanently delete all saved settings.
    WARNING: This cannot be undone.
    """
    if clear_settings():
        return {
            "success": True,
            "message": "All saved settings have been cleared",
            "warning": "This action cannot be undone",
        }
    raise HTTPException(status_code=500, detail="Failed to clear settings")


@router.get("/settings/status")
def get_current_settings_status():
    """
    Get the current status of settings persistence.
    """
    status = get_settings_status()
    return {
        "success": True,
        "data": status,
    }


@router.get("/settings/instructions")
def get_settings_instructions():
    """
    Get instructions on how to use the settings system.
    """
    return {
        "success": True,
        "instructions": {
            "overview": "Settings persistence system to avoid daily reconfiguration",
            "daily_workflow": [
                "1. Enter your daily token via /api/v2/credentials/save",
                "2. Backend will auto-connect to live feed",
                "3. Your client_id, auth_mode, and API keys are remembered",
            ],
            "first_time_setup": [
                "1. Enter credentials (client_id, api_key, etc.) via /api/v2/credentials/save",
                "2. Verify backend connects and live feed starts",
                "3. Lock settings: POST /api/v2/settings/lock",
                "4. Done! Next day, only enter the daily token",
            ],
            "endpoints": {
                "POST /api/v2/settings/lock": "Lock current settings for auto-restore",
                "POST /api/v2/settings/unlock": "Unlock settings (disable auto-restore)",
                "POST /api/v2/settings/save": "Manually save current working settings",
                "POST /api/v2/settings/restore": "Manually restore saved settings",
                "POST /api/v2/settings/clear": "Delete all saved settings permanently",
                "GET /api/v2/settings/status": "Check if settings are locked and saved",
                "GET /api/v2/settings/instructions": "Show this help message",
            },
            "notes": [
                "- Daily token is NOT saved (security best practice)",
                "- Only client_id, auth_mode, and API keys are persisted",
                "- Settings auto-restore on startup if locked",
                "- Backup of previous settings kept at config/settings.backup.json",
            ],
        }
    }
