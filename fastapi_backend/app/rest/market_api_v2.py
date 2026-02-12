# ==============================
# MARKET API V2 ROUTER (STABLE BUILD)
# Compatible with Python 3.9+
# ==============================

from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import Optional
import logging
from app.market_orchestrator import get_orchestrator
import os

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


@router.get("/market/underlying-ltp/{underlying}")
def underlying_ltp(underlying: str):
    """Return LTP for an underlying symbol from live prices cache."""
    try:
        from app.market.live_prices import get_price
        sym = (underlying or "").upper()
        price = get_price(sym)
        if price is None:
            raise HTTPException(status_code=404, detail=f"LTP not available for {sym}")
        return {"status": "success", "underlying": sym, "ltp": price}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch underlying LTP: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/diagnostics/env")
def env_status():
    def g(k: str) -> str:
        return (os.getenv(k) or "").strip()
    return {
        "status": "success",
        "data": {
            "ENVIRONMENT": g("ENVIRONMENT"),
            "DISABLE_DHAN_WS": g("DISABLE_DHAN_WS"),
            "BACKEND_OFFLINE": g("BACKEND_OFFLINE"),
            "DISABLE_MARKET_STREAMS": g("DISABLE_MARKET_STREAMS"),
            "DISABLE_V1_COMPAT": g("DISABLE_V1_COMPAT"),
        }
    }

@router.get("/diagnostics/credentials")
def credentials_status():
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import DhanCredential
        db = SessionLocal()
        try:
            row = db.query(DhanCredential).filter(DhanCredential.is_default == True).first() or db.query(DhanCredential).first()
            if not row:
                return {"status": "success", "data": {"has_credentials": False}}
            tok = (row.daily_token or row.auth_token or "").strip()
            return {
                "status": "success",
                "data": {
                    "has_credentials": True,
                    "client_id_prefix": (row.client_id or "")[:8],
                    "auth_mode": row.auth_mode or "",
                    "has_token": bool(tok),
                    "last_updated": row.last_updated.isoformat() if row.last_updated else "",
                }
            }
        finally:
            db.close()
    except Exception as e:
        logger.exception("Failed to fetch credentials status: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/diagnostics/dhanhq")
def dhanhq_status():
    try:
        ok = False
        feed_names = []
        try:
            import importlib
            m = importlib.import_module("dhanhq.marketfeed")
            for name in ("DhanFeed", "MarketFeed", "MarketFeedV2", "DhanMarketFeed", "MarketFeedWS"):
                if hasattr(m, name):
                    feed_names.append(name)
            ok = True
        except Exception:
            ok = False
        return {"status": "success", "data": {"import_ok": ok, "feed_classes": feed_names}}
    except Exception as e:
        logger.exception("Failed to inspect dhanhq module: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/market/live-feed-status")
def live_feed_status():
    """Return equity live feed internal status (connection attempts, cooldown)."""
    try:
        from app.dhan.live_feed import get_live_feed_status
        return {"status": "success", "data": get_live_feed_status()}
    except Exception as e:
        logger.exception("Failed to fetch live feed status: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/commodities/ws-status")
def commodities_ws_status():
    """Return MCX WebSocket manager status."""
    try:
        from app.commodity_engine.commodity_ws_manager import commodity_ws_manager
        return {"status": "success", "data": commodity_ws_manager.get_status()}
    except Exception as e:
        logger.exception("Failed to fetch commodities ws status: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/dhan/reset-cooldown")
def admin_reset_cooldown():
    try:
        from app.dhan.live_feed import reset_cooldown, get_live_feed_status
        reset_cooldown()
        return {"status": "success", "data": get_live_feed_status()}
    except Exception as e:
        logger.exception("Failed to reset cooldown: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/dhan/restart-streams")
def admin_restart_streams():
    try:
        orch = get_orchestrator()
        try:
            orch.start_streams_sync()
        except Exception:
            pass
        return {"status": "success", "data": orch.get_status()}
    except Exception as e:
        logger.exception("Failed to restart streams: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/admin/dhan/test-quote")
def admin_test_quote():
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import DhanCredential
        from dhanhq import dhanhq as DhanHQClient
        db = SessionLocal()
        try:
            row = db.query(DhanCredential).filter(DhanCredential.is_default == True).first() or db.query(DhanCredential).first()
            if not row:
                raise HTTPException(status_code=400, detail="No credentials")
            token = (row.auth_token or row.daily_token or "").strip()
            if not row.client_id or not token:
                raise HTTPException(status_code=400, detail="Invalid credentials")
            client = None
            try:
                client = DhanHQClient(row.client_id, token)
            except TypeError:
                try:
                    client = DhanHQClient(row.client_id)
                except TypeError:
                    client = DhanHQClient(token)
            payload = {"IDX_I": [13]}
            data = client.quote_data(payload)
            ok = bool(data)
            return {"status": "success", "data": {"ok": ok, "payload": payload, "keys": list((data or {}).keys())}}
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Test quote failed: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/stream-status")
def market_stream_status():
    """Return current market orchestrator / feed status for diagnostics."""
    try:
        orch = get_orchestrator()
        try:
            status = orch.get_status()
        except Exception:
            # If orchestrator exists but method fails, still return minimal info
            status = {"ok": False, "error": "failed to fetch orchestrator status"}
        return {"status": "success", "data": status}
    except Exception as e:
        logging.exception("Failed to fetch market stream status: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# Lightweight compatibility endpoint for option depth
@router.get("/market/option-depth")
def option_depth(underlying: str, expiry: str, strike: float, option_type: str):
    """Return best-known order depth for an option from authoritative cache if available."""
    try:
        from app.services.authoritative_option_chain_service import authoritative_option_chain_service

        oc = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
        if not oc:
            raise HTTPException(status_code=404, detail="Option chain not found")

        strikes = oc.get("strikes", {})
        key = str(int(strike)) if float(strike).is_integer() else str(strike)
        s_data = strikes.get(key)
        if not s_data:
            raise HTTPException(status_code=404, detail="Strike not found")

        opt = s_data.get(option_type.upper()) or {}
        depth = opt.get("depth")
        if not depth:
            # No depth available; return empty structure instead of 404 so UI can handle gracefully
            return {"status": "success", "data": {"bids": [], "asks": []}}

        return {"status": "success", "data": depth}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch option depth: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
