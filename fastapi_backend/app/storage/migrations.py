
from sqlalchemy import text, inspect
from .db import engine, Base, DB_PATH
from . import models

def _get_existing_columns(table_name: str) -> set:
    """Get existing columns for a table using database-agnostic introspection."""
    inspector = inspect(engine)
    try:
        columns = inspector.get_columns(table_name)
        return {col['name'] for col in columns}
    except Exception:
        return set()

def _ensure_dhan_credentials_columns():
    """Add missing columns to dhan_credentials table if needed."""
    existing = _get_existing_columns('dhan_credentials')
    
    if not existing:
        return

    additions = []
    if "daily_token" not in existing:
        additions.append("ALTER TABLE dhan_credentials ADD COLUMN daily_token VARCHAR")
    if "auth_mode" not in existing:
        additions.append("ALTER TABLE dhan_credentials ADD COLUMN auth_mode VARCHAR")
    if "is_default" not in existing:
        additions.append("ALTER TABLE dhan_credentials ADD COLUMN is_default BOOLEAN DEFAULT FALSE")
    if "last_updated" not in existing:
        additions.append("ALTER TABLE dhan_credentials ADD COLUMN last_updated TIMESTAMP")

    if additions:
        with engine.connect() as conn:
            for stmt in additions:
                conn.execute(text(stmt))
            conn.commit()


def _ensure_user_accounts_columns():
    """Add missing columns to user_accounts table if needed."""
    existing = _get_existing_columns('user_accounts')
    
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
        additions.append("ALTER TABLE user_accounts ADD COLUMN require_password_reset BOOLEAN DEFAULT FALSE")
    if "margin_multiplier" not in existing:
        additions.append("ALTER TABLE user_accounts ADD COLUMN margin_multiplier FLOAT DEFAULT 1.0")
        ensure_margin_multiplier = True

    if additions or ensure_margin_multiplier:
        with engine.connect() as conn:
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
