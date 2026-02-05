from __future__ import annotations

import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.storage.db import SessionLocal
from app.storage.models import UserAccount
from app.users.passwords import verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


def _serialize_user(user: UserAccount) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "wallet_balance": user.wallet_balance,
        "permissions": {},
    }


def _get_db() -> Session:
    return SessionLocal()


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    db = _get_db()
    try:
        login_value = (payload.username or payload.email or "").strip()
        if not login_value or not payload.password:
            raise HTTPException(status_code=400, detail="Missing credentials")

        user = (
            db.query(UserAccount)
            .filter(func.lower(UserAccount.username) == login_value.lower())
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
