"""
Market API V2
Clean production-safe version for deployment
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, List
from datetime import datetime, date

# ==========================================================
# ROUTER
# ==========================================================

router = APIRouter(prefix="/api/v2", tags=["market-v2"])


# ==========================================================
# SECTION 1 — UTILS
# ==========================================================

def _normalize_expiry(expiry: Optional[str]) -> Optional[date]:
    """
    Safely convert expiry string to date.
    Compatible with all Python 3.10+ runtimes.
    """
    if not expiry:
        return None

    try:
        return datetime.strptime(expiry, "%Y-%m-%d").date()
    except Exception:
        return None


# ==========================================================
# SECTION 2 — HEALTH CHECK
# ==========================================================

@router.get("/health")
async def health():
    return {"status": "ok", "service": "market-api-v2"}


# ==========================================================
# SECTION 3 — SAMPLE ROUTE (SAFE STARTUP)
# ==========================================================

@router.get("/ping")
async def ping():
    return {"message": "Market API v2 running"}


# ==========================================================
# SECTION 4 — PLACEHOLDER ROUTES
# (We enable these AFTER server stabilizes)
# ==========================================================

@router.get("/subscriptions/status")
async def get_subscription_status():
    """
    Temporary stub to avoid startup crash.
    """
    return {
        "subscriptions": [],
        "websocket": "inactive"
    }


# ==========================================================
# SECTION 5 — DEBUG STARTUP LOG
# ==========================================================

print("[OK] Market API v2 router loaded")
