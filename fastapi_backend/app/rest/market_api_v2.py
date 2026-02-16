# ==============================
# MARKET API V2 ROUTER (STABLE BUILD)
# Compatible with Python 3.9+
# ==============================

from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import Optional
import logging
from app.market_orchestrator import get_orchestrator

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

        equity_ws = {}
        mcx_ws = {}
        live_feed = {}
        try:
            from app.market.ws_manager import get_ws_manager
            equity_ws = get_ws_manager().get_status()
        except Exception:
            equity_ws = {"connected_connections": 0, "total_subscriptions": 0}

        try:
            from app.commodity_engine.commodity_ws_manager import commodity_ws_manager
            mcx_ws = commodity_ws_manager.get_status()
        except Exception:
            mcx_ws = {"connected_connections": 0, "total_subscriptions": 0}

        try:
            from app.dhan.live_feed import get_live_feed_status
            live_feed = get_live_feed_status()
        except Exception:
            live_feed = {}

        try:
            from app.ems.exchange_clock import is_market_open
            market_open = {
                "NSE": bool(is_market_open("NSE")),
                "BSE": bool(is_market_open("BSE")),
                "MCX": bool(is_market_open("MCX")),
            }
        except Exception:
            market_open = {}

        return {
            "status": "success",
            "data": {
                "orchestrator": status,
                "equity_ws": equity_ws,
                "mcx_ws": mcx_ws,
                "live_feed": live_feed,
                "market_open": market_open,
            },
        }
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
