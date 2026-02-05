"""Shared helpers for the commodity engine."""
from __future__ import annotations

from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


async def fetch_dhan_credentials() -> Optional[Dict[str, str]]:
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import DhanCredential

        db = SessionLocal()
        try:
            record = db.query(DhanCredential).filter(DhanCredential.is_default == True).first()
            if not record:
                record = db.query(DhanCredential).first()
            if not record:
                logger.error("❌ No DhanHQ credentials found for commodity engine")
                return None
            token = record.daily_token or record.auth_token
            if not record.client_id or not token:
                logger.error("❌ Invalid DhanHQ credentials for commodity engine")
                return None
            return {"client_id": record.client_id, "access_token": token}
        finally:
            db.close()
    except Exception as exc:
        logger.error(f"❌ Failed to load DhanHQ credentials: {exc}")
        return None
