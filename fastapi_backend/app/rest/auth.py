from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.storage.db import SessionLocal
from app.storage.models import UserAccount
from app.users.passwords import verify_password, hash_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    mobile: Optional[str] = None
    user_id: Optional[str] = None
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def _serialize_user(user: UserAccount) -> dict:
    return {
        "id": user.id,
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "mobile": user.mobile,
        "role": user.role,
        "status": user.status,
        "wallet_balance": user.wallet_balance,
        "brokerage_plan_id": user.brokerage_plan_id,
        "margin_multiplier": user.margin_multiplier,
        "require_password_reset": bool(user.require_password_reset),
        "permissions": {},
    }


def _get_db() -> Session:
    return SessionLocal()


@router.post("/auth/login", response_model=LoginResponse)
async def login(request: Request, payload: LoginRequest):
    # Defensive guard: reject requests that include Dhan/admin credential fields
    try:
        raw = await request.json()
    except Exception:
        raw = {}

    forbidden_keys = {
        "client_id",
        "api_key",
        "api_secret",
        "auth_token",
        "daily_token",
        "dhan_token",
        "access_token",
    }
    if isinstance(raw, dict) and forbidden_keys.intersection(set(k.lower() for k in raw.keys())):
        raise HTTPException(status_code=400, detail="Invalid fields in login payload")

    db = _get_db()
    try:
        login_value = (payload.mobile or payload.user_id or payload.username or payload.email or "").strip()
        if not login_value or not payload.password:
            raise HTTPException(status_code=400, detail="Missing credentials")

        user = None
        if payload.mobile:
            user = (
                db.query(UserAccount)
                .filter(func.lower(UserAccount.mobile) == login_value.lower())
                .first()
            )
        if not user:
            user = (
                db.query(UserAccount)
                .filter(
                    (func.lower(UserAccount.user_id) == login_value.lower())
                    | (func.lower(UserAccount.username) == login_value.lower())
                )
                .first()
            )
        if not user and payload.email:
            user = (
                db.query(UserAccount)
                .filter(func.lower(UserAccount.email) == payload.email.lower())
                .first()
            )

        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        if user.status != "ACTIVE":
            raise HTTPException(status_code=403, detail="User not active")

        if not verify_password(payload.password, user.password_salt or "", user.password_hash or ""):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = secrets.token_hex(24)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": _serialize_user(user),
        }
    finally:
        db.close()


@router.post("/auth/logout")
def logout():
    return {"status": "ok"}


class ChangePasswordRequest(BaseModel):
    user_id: int
    current_password: str
    new_password: str


def _is_strong_password(pw: str) -> bool:
    if not pw or len(pw) < 8:
        return False
    has_upper = any(c.isupper() for c in pw)
    has_lower = any(c.islower() for c in pw)
    has_digit = any(c.isdigit() for c in pw)
    specials = set("!@#$%^&*()-_=+[]{};:'\",.<>/?\\|`~")
    has_special = any(c in specials for c in pw)
    return has_upper and has_lower and has_digit and has_special


@router.post("/auth/change-password")
def change_password(req: ChangePasswordRequest):
    db = _get_db()
    try:
        user = db.query(UserAccount).filter(UserAccount.id == req.user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        if not verify_password(req.current_password, user.password_salt or "", user.password_hash or ""):
            raise HTTPException(status_code=401, detail="Current password is incorrect")
        if not _is_strong_password(req.new_password):
            raise HTTPException(status_code=400, detail="Password does not meet complexity requirements")
        salt, digest = hash_password(req.new_password)
        user.password_salt = salt
        user.password_hash = digest
        user.require_password_reset = False
        db.commit()
        return {"success": True}
    finally:
        db.close()
