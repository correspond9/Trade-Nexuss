
import os
import sqlite3
from sqlalchemy import text, inspect
from .db import engine, Base, DB_PATH
from .db import SessionLocal
from . import models
from app.users.passwords import hash_password

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


def _ensure_bootstrap_admin_user():
    """Create/repair an admin login user from env vars (for fresh Postgres deployments)."""
    mobile = (os.getenv("BOOTSTRAP_ADMIN_MOBILE") or "").strip()
    password = (os.getenv("BOOTSTRAP_ADMIN_PASSWORD") or "").strip()
    username = (os.getenv("BOOTSTRAP_ADMIN_USERNAME") or mobile or "").strip()
    role = (os.getenv("BOOTSTRAP_ADMIN_ROLE") or "SUPER_ADMIN").strip().upper()

    if not mobile or not password:
        print("[DB] Bootstrap admin skipped (BOOTSTRAP_ADMIN_MOBILE/PASSWORD not set)")
        return

    db = SessionLocal()
    try:
        user = (
            db.query(models.UserAccount)
            .filter(
                (models.UserAccount.mobile == mobile)
                | (models.UserAccount.user_id == mobile)
                | (models.UserAccount.username == username)
            )
            .first()
        )

        salt, digest = hash_password(password)

        if user:
            updated = False
            if not (user.password_salt or "").strip() or not (user.password_hash or "").strip():
                user.password_salt = salt
                user.password_hash = digest
                updated = True
            if not (user.mobile or "").strip():
                user.mobile = mobile
                updated = True
            if not (user.user_id or "").strip():
                user.user_id = mobile
                updated = True
            if user.status != "ACTIVE":
                user.status = "ACTIVE"
                updated = True
            if not (user.role or "").strip():
                user.role = role
                updated = True

            if updated:
                db.commit()
                print(f"[DB] ✓ Bootstrap admin repaired: username={user.username}, mobile={user.mobile}")
            else:
                print(f"[DB] ✓ Bootstrap admin exists: username={user.username}, mobile={user.mobile}")
            return

        new_user = models.UserAccount(
            username=username,
            email=None,
            mobile=mobile,
            user_id=mobile,
            password_salt=salt,
            password_hash=digest,
            require_password_reset=False,
            role=role,
            status="ACTIVE",
            allowed_segments="NSE,NFO,BSE,MCX",
            wallet_balance=0.0,
            margin_multiplier=5.0,
        )
        db.add(new_user)
        db.commit()
        print(f"[DB] ✓ Bootstrap admin created: username={username}, mobile={mobile}")
    except Exception as exc:
        db.rollback()
        print(f"[DB] ✗ Bootstrap admin setup failed: {exc}")
        raise
    finally:
        db.close()


def _restore_users_from_sqlite_if_configured():
    """Optionally restore users from a SQLite backup file into current DB.

    Controlled by env vars:
      - SQLITE_USERS_RESTORE_ON_START=true
      - SQLITE_USERS_RESTORE_PATH=/absolute/path/to/sqlite.db
    """
    enabled = (os.getenv("SQLITE_USERS_RESTORE_ON_START") or "").strip().lower() in ("1", "true", "yes", "on")
    if not enabled:
        return

    sqlite_path = (os.getenv("SQLITE_USERS_RESTORE_PATH") or "").strip()
    if not sqlite_path:
        print("[DB] SQLite restore skipped (SQLITE_USERS_RESTORE_PATH not set)")
        return

    if not os.path.exists(sqlite_path):
        print(f"[DB] SQLite restore skipped (file not found): {sqlite_path}")
        return

    print(f"[DB] Restoring users from SQLite: {sqlite_path}")

    src = sqlite3.connect(sqlite_path)
    src.row_factory = sqlite3.Row
    src_cur = src.cursor()

    dst = SessionLocal()
    try:
        src_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_accounts'")
        if not src_cur.fetchone():
            print("[DB] SQLite restore skipped (user_accounts table missing)")
            return

        src_cur.execute("SELECT * FROM user_accounts")
        rows = src_cur.fetchall()
        if not rows:
            print("[DB] SQLite restore skipped (no user rows)")
            return

        restored = 0
        repaired = 0

        for row in rows:
            row = dict(row)
            mobile = (row.get("mobile") or "").strip() or None
            user_id = (row.get("user_id") or "").strip() or None
            username = (row.get("username") or "").strip() or None
            email = (row.get("email") or "").strip() or None

            target = None
            if mobile:
                target = dst.query(models.UserAccount).filter(models.UserAccount.mobile == mobile).first()
            if not target and user_id:
                target = dst.query(models.UserAccount).filter(models.UserAccount.user_id == user_id).first()
            if not target and username:
                target = dst.query(models.UserAccount).filter(models.UserAccount.username == username).first()
            if not target and email:
                target = dst.query(models.UserAccount).filter(models.UserAccount.email == email).first()

            if not target:
                target = models.UserAccount()
                dst.add(target)
                restored += 1
            else:
                repaired += 1

            for col in [
                "username", "email", "mobile", "user_id", "password_salt", "password_hash",
                "require_password_reset", "role", "status", "allowed_segments", "wallet_balance",
                "margin_multiplier", "brokerage_plan_id"
            ]:
                if col in row:
                    setattr(target, col, row.get(col))

            if not (target.status or "").strip():
                target.status = "ACTIVE"
            if not (target.role or "").strip():
                target.role = "USER"

        dst.commit()
        print(f"[DB] ✓ SQLite user restore complete. inserted={restored}, updated={repaired}")
    except Exception as exc:
        dst.rollback()
        print(f"[DB] ✗ SQLite user restore failed: {exc}")
        raise
    finally:
        try:
            src.close()
        except Exception:
            pass
        dst.close()


def init_db():
    """Initialize database tables and ensure schema is up to date."""
    print(f"[DB] Initializing database at: {DB_PATH}")
    print(f"[DB] Database file exists: {DB_PATH.exists()}")
    
    try:
        Base.metadata.create_all(bind=engine)
        print("[DB] ✓ All tables created/verified")
        
        _ensure_dhan_credentials_columns()
        _ensure_user_accounts_columns()
        _restore_users_from_sqlite_if_configured()
        _ensure_bootstrap_admin_user()
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
