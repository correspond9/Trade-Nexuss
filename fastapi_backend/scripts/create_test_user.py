from __future__ import annotations

from app.storage.db import DB_PATH, SessionLocal
from app.storage.models import UserAccount
from app.users.passwords import hash_password
from sqlalchemy.exc import IntegrityError
import sys


def create_or_update_user(username: str, email: str, password: str):
    print(f"[INFO] DB_PATH: {DB_PATH}")
    db = SessionLocal()
    try:
        user = db.query(UserAccount).filter(
            (UserAccount.username == username) | (UserAccount.email == email)
        ).first()
        salt, digest = hash_password(password)
        if user:
            print(f"[INFO] Updating existing user id={user.id} username={user.username}")
            user.username = username
            user.email = email
            user.password_salt = salt
            user.password_hash = digest
            user.role = "SUPER_ADMIN"
            user.status = "ACTIVE"
            user.require_password_reset = False
        else:
            print("[INFO] Creating new SUPER_ADMIN user")
            user = UserAccount(
                username=username,
                email=email,
                user_id="admin",
                password_salt=salt,
                password_hash=digest,
                role="SUPER_ADMIN",
                status="ACTIVE",
                wallet_balance=100000.0,
            )
            db.add(user)
        db.commit()
        print("[OK] User created/updated successfully")
    except IntegrityError as ex:
        db.rollback()
        print("[ERROR] IntegrityError:", ex)
        sys.exit(2)
    except Exception as ex:
        db.rollback()
        print("[ERROR]", ex)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    # Defaults that match the Playwright tests
    USERNAME = "admin@example.com"
    EMAIL = "admin@example.com"
    PASSWORD = "admin123"
    create_or_update_user(USERNAME, EMAIL, PASSWORD)
