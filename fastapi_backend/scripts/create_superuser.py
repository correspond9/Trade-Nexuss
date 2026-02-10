#!/usr/bin/env python3
"""Create or update a SUPER_ADMIN user in the local SQLite DB.

Usage:
  python create_superuser.py --username admin --email admin@example.com --password Secret123!

If the user exists (by username or email) it will update the password and role.
"""
import argparse
import sys
from app.storage.db import SessionLocal
from app.storage.models import UserAccount
from app.users.passwords import hash_password
from sqlalchemy import func
import secrets


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--username", required=True)
    p.add_argument("--email", required=False)
    p.add_argument("--password", required=True)
    args = p.parse_args()

    db = SessionLocal()
    try:
        user = None
        if args.email:
            user = db.query(UserAccount).filter(func.lower(UserAccount.email) == args.email.lower()).first()
        if not user:
            user = db.query(UserAccount).filter(func.lower(UserAccount.username) == args.username.lower()).first()

        salt, digest = hash_password(args.password)

        if user:
            user.password_salt = salt
            user.password_hash = digest
            user.role = "SUPER_ADMIN"
            user.status = "ACTIVE"
            user.require_password_reset = False
            db.commit()
            print(f"Updated user '{user.username}' (id={user.id}) with new SUPER_ADMIN credentials.")
            return

        # create new user
        user_id = f"super_{secrets.token_hex(6)}"
        new_user = UserAccount(
            username=args.username,
            email=args.email,
            user_id=user_id,
            password_salt=salt,
            password_hash=digest,
            role="SUPER_ADMIN",
            status="ACTIVE",
            require_password_reset=False,
        )
        db.add(new_user)
        db.commit()
        print(f"Created SUPER_ADMIN user '{args.username}' with id={new_user.id} and user_id={user_id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
