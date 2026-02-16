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


def _looks_masked(value: str) -> bool:
    text = (value or "").strip()
    return bool(text) and "*" in text


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
                "client_id": row.client_id or "",
                "client_id_prefix": (row.client_id or "")[:8],
                "auth_mode": row.auth_mode or "DAILY_TOKEN",
                "has_token": bool(row.auth_token),
                "last_updated": row.last_updated.isoformat() if row.last_updated else None,
            }
        }
    finally:
        db.close()


from app.storage.settings_manager import save_settings

@router.post("/credentials/save")
def save_credentials(c: CredSaveIn):
    db = SessionLocal()
    try:
        mode = _normalize_mode(c.auth_mode)
        # ... (rest of logic)
        
        row = _get_credential_by_mode(db, mode)
        if not row:
            row = DhanCredential(auth_mode=mode)
            db.add(row)

        incoming_client_id = (c.client_id or "").strip()
        incoming_access_token = (c.access_token or "").strip()
        incoming_daily_token = (c.daily_token or "").strip()
        incoming_api_key = (c.api_key or "").strip()
        incoming_api_secret = (c.secret_api or "").strip()

        # Preserve previously saved values if frontend sends masked placeholders.
        if _looks_masked(incoming_client_id) and row.client_id:
            resolved_client_id = row.client_id
        else:
            resolved_client_id = incoming_client_id

        row.client_id = resolved_client_id

        if mode == "DAILY_TOKEN":
            resolved_token = incoming_access_token or incoming_daily_token

            # If frontend sends masked placeholder or empty value, keep existing valid token.
            if (_looks_masked(resolved_token) or not resolved_token) and (row.daily_token or row.auth_token):
                resolved_token = (row.daily_token or row.auth_token or "").strip()

            row.auth_token = resolved_token
            row.daily_token = resolved_token
            row.api_key = ""
            row.api_secret = ""
        else:
            row.api_key = incoming_api_key
            row.api_secret = incoming_api_secret
            # STATIC_IP mode still relies on existing token-based WS flow in current implementation.
            # Keep prior token values unless explicitly provided (and not masked).
            if incoming_access_token and not _looks_masked(incoming_access_token):
                row.auth_token = incoming_access_token
            if incoming_daily_token and not _looks_masked(incoming_daily_token):
                row.daily_token = incoming_daily_token

        row.last_updated = datetime.utcnow()

        # Set active mode
        db.query(DhanCredential).update({DhanCredential.is_default: False})
        row.is_default = True

        db.commit()

        # Persist to disk for auto-restore
        save_settings(force=True)

        # Start market data streams immediately after credentials are saved
        try:
            from app.dhan.live_feed import reset_cooldown
            reset_cooldown()
        except Exception:
            pass
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

        # On mode switch, clear any connection cooldown and restart streams.
        try:
            from app.dhan.live_feed import reset_cooldown
            reset_cooldown()
        except Exception:
            pass
        get_orchestrator().start_streams_sync()

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
        return {"success": True, "data": {"client_id_prefix": (row.client_id or "")[:8]}}
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
            "client_id_prefix": (row.client_id or "")[:8],
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
