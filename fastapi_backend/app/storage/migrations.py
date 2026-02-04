
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


def init_db():
    """Initialize database tables and ensure schema is up to date."""
    print(f"[DB] Initializing database at: {DB_PATH}")
    print(f"[DB] Database file exists: {DB_PATH.exists()}")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] ✓ All tables created/verified")
        
        _ensure_dhan_credentials_columns()
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
