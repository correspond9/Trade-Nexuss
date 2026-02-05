
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
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
    user = db.query(UserAccount).filter(UserAccount.username == x_user).first()
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=403, detail="Invalid or inactive user")
    return user
