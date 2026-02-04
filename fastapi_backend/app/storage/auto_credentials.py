"""
Auto-load DhanHQ credentials from environment variables
This ensures credentials are loaded automatically on startup without manual UI input
Perfect for VPS/cloud deployments where env vars are set via deployment config
"""
import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text
from app.storage.db import SessionLocal
from app.storage.models import DhanCredential

# Fix encoding for Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Load .env file from parent directories
def _find_env_file():
    """Search for .env file in parent directories"""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(5):  # Search up to 5 levels
        parent = os.path.dirname(current)
        env_path = os.path.join(parent, '.env')
        if os.path.exists(env_path):
            return env_path
        current = parent
    return None

# Load environment variables
env_file = _find_env_file()
if env_file:
    load_dotenv(env_file)
    print(f"[STARTUP] Loaded .env from: {env_file}")


def _upsert_credential(db, record, **fields):
    if record is None:
        record = DhanCredential(is_default=True)
        db.add(record)
    for key, value in fields.items():
        setattr(record, key, value)
    record.is_default = True
    db.commit()
    return record


def _has_valid_credentials(record: DhanCredential) -> bool:
    if not record:
        return False
    if record.auth_mode == "STATIC_IP":
        return all([record.client_id, record.api_key, record.api_secret])
    if record.auth_mode == "DAILY_TOKEN":
        return all([record.client_id, record.auth_token])
    return False


def auto_load_credentials():
    """
    Auto-load credentials from environment variables on startup.
    
    Env priority:
    1. Mode B (STATIC_IP): DHAN_CLIENT_ID, DHAN_API_KEY, DHAN_API_SECRET
    2. Mode A (DAILY_TOKEN): DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN
    
    If env vars are missing, fall back to whatever is already persisted.
    """
    db = SessionLocal()
    try:
        # Verify database connection
        try:
            db.execute(text("SELECT 1"))
            print("[STARTUP] ✓ Database connection verified")
        except Exception as db_err:
            print(f"[ERROR] Database connection failed: {db_err}")
            print(f"[ERROR] Check database path in app/storage/db.py")
            return False
        
        existing = (
            db.query(DhanCredential)
            .filter(DhanCredential.is_default == True)
            .order_by(DhanCredential.id.asc())
            .first()
        ) or db.query(DhanCredential).first()

        client_id = os.getenv('DHAN_CLIENT_ID', '').strip()
        api_key = os.getenv('DHAN_API_KEY', '').strip()
        api_secret = os.getenv('DHAN_API_SECRET', '').strip()
        access_token = os.getenv('DHAN_ACCESS_TOKEN', '').strip()

        if client_id and api_key and api_secret:
            print("[STARTUP] Loading Mode B (STATIC_IP) credentials from environment")
            _upsert_credential(
                db,
                existing,
                client_id=client_id,
                api_key=api_key,
                api_secret=api_secret,
                auth_token="",
                daily_token="",
                auth_mode="STATIC_IP",
            )
            print("[STARTUP] ✓ Mode B credentials saved to database")
            return True

        if client_id and access_token:
            print("[STARTUP] Loading Mode A (DAILY_TOKEN) credentials from environment")
            _upsert_credential(
                db,
                existing,
                client_id=client_id,
                api_key="",
                api_secret="",
                auth_token=access_token,
                daily_token=access_token,
                auth_mode="DAILY_TOKEN",
            )
            print("[STARTUP] ✓ Mode A credentials saved to database")
            return True

        if _has_valid_credentials(existing):
            print(f"[STARTUP] ✓ Using saved credentials from database (Mode: {existing.auth_mode})")
            print(f"[STARTUP]   Client ID: {existing.client_id[:8]}...")
            return True

        print("[STARTUP] ⚠ No DhanHQ credentials available. Set env vars or add via admin UI.")
        print("[STARTUP]   Mode B: DHAN_CLIENT_ID, DHAN_API_KEY, DHAN_API_SECRET")
        print("[STARTUP]   Mode A: DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN")
        return False

    except Exception as e:
        print(f"[ERROR] Failed to auto-load credentials: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()
