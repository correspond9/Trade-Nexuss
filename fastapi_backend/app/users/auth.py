
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.storage.db import SessionLocal
from app.storage.models import UserAccount

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(x_user: str = Header(None), db: Session = Depends(get_db)):
    if not x_user:
        raise HTTPException(status_code=401, detail="Missing X-USER header")
    identity = (x_user or "").strip()
    if not identity:
        raise HTTPException(status_code=401, detail="Missing X-USER header")

    lowered = identity.lower()
    user = (
        db.query(UserAccount)
        .filter(
            (func.lower(UserAccount.username) == lowered)
            | (func.lower(UserAccount.user_id) == lowered)
            | (func.lower(UserAccount.mobile) == lowered)
            | (func.lower(UserAccount.email) == lowered)
        )
        .first()
    )
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Invalid or inactive user")
    return user
