from datetime import datetime
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel
from app.storage.db import SessionLocal
from app.storage.models import DhanCredential
from app.market_orchestrator import get_orchestrator

router = APIRouter()

class CredSaveIn(BaseModel):
    client_id: str
    access_token: str
    api_key: str | None = ""
    secret_api: str | None = ""
    daily_token: str | None = ""
    auth_mode: str


class SwitchModeIn(BaseModel):
    auth_mode: str


def _get_active_credential(db: SessionLocal) -> DhanCredential | None:
    row = db.query(DhanCredential).filter(DhanCredential.is_default == True).first()
    if row:
        return row
    return db.query(DhanCredential).first()


def _get_credential_by_mode(db: SessionLocal, mode: str) -> DhanCredential | None:
    return db.query(DhanCredential).filter(DhanCredential.auth_mode == mode).first()


def _normalize_mode(mode: str) -> str:
    mode = (mode or "").strip().upper()
    if mode not in {"DAILY_TOKEN", "STATIC_IP"}:
        raise HTTPException(status_code=400, detail="Invalid auth_mode")
    return mode


@router.get("/credentials/active")
def get_active_credentials():
    db = SessionLocal()
    try:
        row = _get_active_credential(db)
        if not row:
            return {"success": True, "message": "No credentials saved", "data": {"has_token": False}}

        return {
            "success": True,
            "message": f"Active credentials for {row.auth_mode or 'DAILY_TOKEN'}",
            "data": {
                "client_id": row.client_id,
                "auth_mode": row.auth_mode or "DAILY_TOKEN",
                "has_token": bool(row.auth_token),
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
                "access_token": row.auth_token,
                "api_key": row.api_key,
                "secret_api": row.api_secret,
                "daily_token": row.daily_token,
            }
        }
    finally:
        db.close()


@router.post("/credentials/save")
def save_credentials(c: CredSaveIn):
    db = SessionLocal()
    try:
        mode = _normalize_mode(c.auth_mode)

        row = _get_credential_by_mode(db, mode)
        if not row:
            row = DhanCredential(auth_mode=mode)
            db.add(row)

        row.client_id = c.client_id.strip()
        row.auth_token = (c.access_token or "").strip()
        row.api_key = (c.api_key or "").strip()
        row.api_secret = (c.secret_api or "").strip()
        row.daily_token = (c.daily_token or "").strip()
        row.last_updated = datetime.utcnow()

        # Set active mode
        db.query(DhanCredential).update({DhanCredential.is_default: False})
        row.is_default = True

        db.commit()

        # Start market data streams immediately after credentials are saved
        get_orchestrator().start_streams_sync()

        return {
            "success": True,
            "message": f"Credentials saved successfully for {mode}",
            "data": {"auth_mode": mode}
        }
    finally:
        db.close()


@router.post("/credentials/switch-mode")
def switch_mode(payload: SwitchModeIn | str = Body(...)):
    db = SessionLocal()
    try:
        if isinstance(payload, str):
            mode = _normalize_mode(payload)
        else:
            mode = _normalize_mode(payload.auth_mode)

        target = _get_credential_by_mode(db, mode)
        if not target:
            raise HTTPException(status_code=404, detail="Credentials not found for mode")

        db.query(DhanCredential).update({DhanCredential.is_default: False})
        target.is_default = True
        db.commit()

        return {
            "success": True,
            "message": f"Switched to {mode} mode",
            "data": {"active_mode": mode}
        }
    finally:
        db.close()


@router.get("/credentials/modes")
def get_modes():
    db = SessionLocal()
    try:
        rows = db.query(DhanCredential).all()
        active = _get_active_credential(db)

        def _mode_info(mode: str):
            row = next((r for r in rows if r.auth_mode == mode), None)
            return {
                "mode": mode,
                "has_credentials": bool(row),
                "client_id": row.client_id if row else "",
                "last_updated": row.last_updated.isoformat() if row and row.last_updated else ""
            }

        return {
            "success": True,
            "message": "Available modes retrieved",
            "data": {
                "available_modes": [_mode_info("DAILY_TOKEN"), _mode_info("STATIC_IP")],
                "active_mode": (active.auth_mode if active else "")
            }
        }
    finally:
        db.close()

@router.get("/credentials/dhan/static-ip")
def get_static_ip_credentials():
    db = SessionLocal()
    try:
        row = _get_credential_by_mode(db, "STATIC_IP") or _get_active_credential(db)
        if not row:
            return {"success": True, "data": None}
        return {"success": True, "data": {"client_id": row.client_id or ""}}
    finally:
        db.close()

@router.get("/credentials/dhan/daily-token")
def get_daily_token_credentials():
    db = SessionLocal()
    try:
        row = _get_credential_by_mode(db, "DAILY_TOKEN") or _get_active_credential(db)
        if not row:
            return {"success": True, "data": None}
        expiry = row.last_updated.isoformat() if row.last_updated else ""
        return {"success": True, "data": {"expiry_time": expiry}}
    finally:
        db.close()


@router.delete("/credentials/clear")
def clear_credentials():
    db = SessionLocal()
    try:
        db.query(DhanCredential).delete()
        db.commit()
        return {"success": True, "message": "All credentials cleared successfully"}
    finally:
        db.close()


# Legacy test endpoints (kept for compatibility)
class CredIn(BaseModel):
    client_id: str
    api_key: str | None = ""
    api_secret: str | None = ""
    auth_token: str


@router.get("/test/credentials")
def get_creds():
    db = SessionLocal()
    try:
        row = _get_active_credential(db)
        if not row:
            return {}
        return {
            "client_id": row.client_id,
            "auth_token": row.auth_token,
            "token_len": len(row.auth_token or ""),
        }
    finally:
        db.close()


@router.post("/test/credentials")
def save_creds(c: CredIn):
    db = SessionLocal()
    try:
        # ALWAYS overwrite (single-row table)
        db.query(DhanCredential).delete()

        row = DhanCredential(
            client_id=c.client_id.strip(),
            api_key=c.api_key.strip(),
            api_secret=c.api_secret.strip(),
            auth_token=c.auth_token.strip(),
            auth_mode="DAILY_TOKEN",
            is_default=True,
            last_updated=datetime.utcnow()
        )
        db.add(row)
        db.commit()

        # Start market data streams immediately after credentials are saved
        get_orchestrator().start_streams_sync()

        return {"status": "saved"}
    finally:
        db.close()
