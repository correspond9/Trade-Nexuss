"""
Settings Manager: Save and restore working configurations
Prevents daily reconfiguration of the backend.
Only daily_token needs to be refreshed every 24 hours.
"""
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from app.storage.db import SessionLocal
from app.storage.models import DhanCredential

SETTINGS_DIR = Path(__file__).parent.parent.parent / "config"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
SETTINGS_BACKUP_FILE = SETTINGS_DIR / "settings.backup.json"
SETTINGS_LOCK_FILE = SETTINGS_DIR / ".settings_locked"

# Create config directory if it doesn't exist
SETTINGS_DIR.mkdir(exist_ok=True)


def _ensure_backup():
    """Create a backup of current settings"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                current = json.load(f)
            with open(SETTINGS_BACKUP_FILE, 'w') as f:
                json.dump(current, f, indent=2, default=str)
        except Exception as e:
            print(f"[SETTINGS] Warning: Could not create backup: {e}")


def save_settings(force: bool = False) -> bool:
    """
    Save current working settings to JSON file.
    
    Args:
        force: If True, save even if not explicitly locked
    
    Returns:
        True if settings were saved
    """
    try:
        db = SessionLocal()
        try:
            # Get active credentials (but NOT the daily_token/auth_token)
            cred = db.query(DhanCredential).filter(
                DhanCredential.is_default == True
            ).first()
            
            if not cred:
                return False
            
            settings = {
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0",
                "client_id": cred.client_id,
                "auth_mode": cred.auth_mode or "DAILY_TOKEN",
                "api_key": cred.api_key or "",
                "api_secret": cred.api_secret or "",
                # Save token as well if configured (useful for production)
                "daily_token": cred.daily_token or cred.auth_token or "",
                "notes": "This backup now includes the token for auto-restore in production.",
                "locked": SETTINGS_LOCK_FILE.exists() or force,
            }
            
            # Create backup first
            _ensure_backup()
            
            # Save new settings
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
            
            if force:
                SETTINGS_LOCK_FILE.touch()
            
            print(f"[SETTINGS] ✓ Settings saved to {SETTINGS_FILE}")
            return True
        finally:
            db.close()
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to save settings: {e}")
        return False


def load_settings() -> Optional[Dict[str, Any]]:
    """
    Load saved settings from JSON file.
    
    Returns:
        Settings dict or None if not found
    """
    try:
        if not SETTINGS_FILE.exists():
            return None
        
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
        
        print(f"[SETTINGS] ✓ Loaded settings from {SETTINGS_FILE}")
        return settings
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to load settings: {e}")
        return None


def restore_settings_to_database() -> bool:
    """
    Restore saved settings to the database on startup.
    (Does NOT restore the daily token - that must be entered fresh)
    
    Returns:
        True if settings were restored
    """
    try:
        settings = load_settings()
        if not settings:
            print("[SETTINGS] No saved settings found. Skipping auto-restore.")
            return False
        
        db = SessionLocal()
        try:
            # Check if we should restore
            is_locked = SETTINGS_LOCK_FILE.exists()
            if not is_locked and "locked" not in settings:
                print("[SETTINGS] Settings not locked. Not auto-restoring (use /api/v2/settings/lock to lock)")
                return False
            
            # Get or create default credential record
            cred = db.query(DhanCredential).filter(
                DhanCredential.is_default == True
            ).first()
            
            if not cred:
                cred = DhanCredential(is_default=True)
                db.add(cred)
            
            # Restore settings (except tokens)
            cred.client_id = settings.get("client_id", cred.client_id or "")
            cred.auth_mode = settings.get("auth_mode", "DAILY_TOKEN")
            cred.api_key = settings.get("api_key", "")
            cred.api_secret = settings.get("api_secret", "")
            # Restore tokens as well
            saved_token = settings.get("daily_token") or settings.get("auth_token") or ""
            if saved_token:
                cred.daily_token = saved_token
                cred.auth_token = saved_token
                print(f"[SETTINGS] ✓ Auto-restored saved token (len={len(saved_token)})")
            
            db.commit()
            
            print(f"[SETTINGS] ✓ Restored settings for client_id: {cred.client_id[:8]}...")
            print(f"[SETTINGS] ✓ Auth mode: {cred.auth_mode}")
            print(f"[SETTINGS] ℹ️  Daily token must still be entered (will be requested on first access)")
            return True
            
        finally:
            db.close()
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to restore settings: {e}")
        return False


def lock_settings() -> bool:
    """
    Lock the current settings so they auto-restore on every startup.
    """
    try:
        # First ensure current state is saved
        if not save_settings(force=True):
            print("[SETTINGS] ✗ Could not save settings before locking")
            return False
        
        SETTINGS_LOCK_FILE.touch()
        print("[SETTINGS] ✓ Settings LOCKED. They will auto-restore on startup.")
        print("[SETTINGS] ℹ️  Daily token must still be entered fresh each day.")
        return True
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to lock settings: {e}")
        return False


def unlock_settings() -> bool:
    """
    Unlock settings so they won't auto-restore.
    """
    try:
        if SETTINGS_LOCK_FILE.exists():
            SETTINGS_LOCK_FILE.unlink()
            print("[SETTINGS] ✓ Settings UNLOCKED. They won't auto-restore on startup.")
        return True
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to unlock settings: {e}")
        return False


def clear_settings() -> bool:
    """
    Delete saved settings completely.
    """
    try:
        if SETTINGS_FILE.exists():
            SETTINGS_FILE.unlink()
        if SETTINGS_LOCK_FILE.exists():
            SETTINGS_LOCK_FILE.unlink()
        print("[SETTINGS] ✓ All saved settings cleared.")
        return True
    except Exception as e:
        print(f"[SETTINGS] ✗ Failed to clear settings: {e}")
        return False


def get_settings_status() -> Dict[str, Any]:
    """Get the current settings status"""
    return {
        "settings_file_exists": SETTINGS_FILE.exists(),
        "settings_locked": SETTINGS_LOCK_FILE.exists(),
        "settings_path": str(SETTINGS_FILE),
        "backup_path": str(SETTINGS_BACKUP_FILE),
        "backup_exists": SETTINGS_BACKUP_FILE.exists(),
        "settings": load_settings() if SETTINGS_FILE.exists() else None,
    }
