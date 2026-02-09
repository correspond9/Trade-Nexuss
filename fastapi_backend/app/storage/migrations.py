
from sqlalchemy import text
from .db import engine, Base, DB_PATH
from . import models

def _ensure_dhan_credentials_columns():
    """Add missing columns to dhan_credentials table if needed."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(dhan_credentials)"))
            existing = {row[1] for row in result.fetchall()}
        except Exception:
            existing = set()

        if not existing:
            return

        additions = []
        if "daily_token" not in existing:
            additions.append("ALTER TABLE dhan_credentials ADD COLUMN daily_token VARCHAR")
        if "auth_mode" not in existing:
            additions.append("ALTER TABLE dhan_credentials ADD COLUMN auth_mode VARCHAR")
        if "is_default" not in existing:
            additions.append("ALTER TABLE dhan_credentials ADD COLUMN is_default BOOLEAN DEFAULT 0")
        if "last_updated" not in existing:
            additions.append("ALTER TABLE dhan_credentials ADD COLUMN last_updated DATETIME")

        for stmt in additions:
            conn.execute(text(stmt))
        if additions:
            conn.commit()


def _ensure_user_accounts_columns():
    """Add missing columns to user_accounts table if needed."""
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(user_accounts)"))
            existing = {row[1] for row in result.fetchall()}
        except Exception:
            existing = set()

        if not existing:
            return

        additions = []
        ensure_margin_multiplier = False
        if "password_salt" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN password_salt VARCHAR")
        if "password_hash" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN password_hash VARCHAR")
        if "mobile" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN mobile VARCHAR")
        if "user_id" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN user_id VARCHAR")
        if "require_password_reset" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN require_password_reset BOOLEAN DEFAULT 0")
        if "margin_multiplier" not in existing:
            additions.append("ALTER TABLE user_accounts ADD COLUMN margin_multiplier FLOAT DEFAULT 1.0")
            ensure_margin_multiplier = True

        for stmt in additions:
            conn.execute(text(stmt))
        if additions:
            conn.commit()
        if "margin_multiplier" in existing or ensure_margin_multiplier:
            conn.execute(text("UPDATE user_accounts SET margin_multiplier = 1.0 WHERE margin_multiplier IS NULL"))
            conn.commit()


def init_db():
    """Initialize database tables and ensure schema is up to date."""
    print(f"[DB] Initializing database at: {DB_PATH}")
    print(f"[DB] Database file exists: {DB_PATH.exists()}")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] ✓ All tables created/verified")
        
        _ensure_dhan_credentials_columns()
        _ensure_user_accounts_columns()
        print("[DB] ✓ Schema migrations complete")
        
        # Verify we can query the credentials table
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM dhan_credentials"))
            count = result.scalar()
            print(f"[DB] ✓ Credentials table accessible ({count} records)")
            
    except Exception as e:
        print(f"[DB] ✗ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise
