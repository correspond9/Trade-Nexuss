# ==============================
# MARKET API V2 ROUTER (STABLE BUILD)
# Compatible with Python 3.9+
# ==============================

from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# =====================================
# SECTION 1 — SAFE DATE NORMALIZER
# =====================================

def normalize_expiry(expiry: Optional[str]) -> Optional[date]:
    """
    Converts expiry string into date safely.
    Prevents startup crashes.
    """
    if expiry is None:
        return None
    
    try:
        return datetime.strptime(expiry, "%Y-%m-%d").date()
    except Exception:
        return None


# =====================================
# SECTION 2 — HEALTH CHECK ROUTE
# =====================================

@router.get("/health")
def health():
    return {"status": "ok"}


# =====================================
# SECTION 3 — TEST ROUTE
# =====================================

@router.get("/test")
def test():
    return {"message": "Market API running"}
