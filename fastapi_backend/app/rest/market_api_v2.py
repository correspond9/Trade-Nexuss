# ==============================
# MARKET API V2 ROUTER (STABLE BUILD)
# Compatible with Python 3.9+
# ==============================

from fastapi import APIRouter, HTTPException
from datetime import datetime, date
from typing import Optional
import logging
import requests
import os
import threading
import time
from app.market_orchestrator import get_orchestrator

router = APIRouter()
logger = logging.getLogger(__name__)
_stream_recovery_lock = threading.Lock()
_last_stream_recovery_attempt = 0.0


def _maybe_recover_streams() -> None:
    """Best-effort auto-recovery when market feed is unexpectedly not started."""
    global _last_stream_recovery_attempt

    try:
        flag = (os.getenv("DISABLE_DHAN_WS") or os.getenv("BACKEND_OFFLINE") or os.getenv("DISABLE_MARKET_STREAMS") or "").strip().lower()
        if flag in ("1", "true", "yes", "on"):
            return

        ws_connected = False
        try:
            from app.market.ws_manager import get_ws_manager
            ws_connected = (get_ws_manager().get_status().get("connected_connections") or 0) > 0
        except Exception:
            ws_connected = False

        feed_started = False
        cooldown_active = False
        try:
            from app.dhan.live_feed import get_live_feed_status
            feed = get_live_feed_status() or {}
            feed_started = bool(feed.get("started"))
            cooldown_active = bool(feed.get("cooldown_active"))
        except Exception:
            feed_started = False
            cooldown_active = False

        if ws_connected or cooldown_active:
            return

        now = time.time()
        if (now - _last_stream_recovery_attempt) < 30:
            return

        with _stream_recovery_lock:
            now_locked = time.time()
            if (now_locked - _last_stream_recovery_attempt) < 30:
                return
            _last_stream_recovery_attempt = now_locked

            def _runner():
                try:
                    logger.info("[MARKET] Auto-recovering market streams (feed_started=%s)", feed_started)
                    get_orchestrator().start_streams_sync()
                    try:
                        from app.dhan.live_feed import sync_subscriptions_with_watchlist
                        sync_subscriptions_with_watchlist()
                    except Exception:
                        pass
                except Exception as stream_err:
                    logger.warning("[MARKET] Auto stream recovery failed: %s", stream_err)

            threading.Thread(target=_runner, name="market-auto-recover", daemon=True).start()
    except Exception:
        return

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
        _maybe_recover_streams()
        from app.market.live_prices import get_price, update_price
        sym = (underlying or "").upper()
        price = get_price(sym)

        if price is None:
            # Fallback: on-demand Dhan quote snapshot for NSE/BSE equities and ETFs.
            from app.market.instrument_master.registry import REGISTRY
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential

            if not REGISTRY.loaded:
                REGISTRY.load()

            security_id = None
            exchange_segment = None
            try:
                for row in REGISTRY.get_equity_stocks_nse(limit=12000):
                    row_symbol = (row.get("UNDERLYING_SYMBOL") or row.get("SYMBOL") or row.get("SYMBOL_NAME") or "").strip().upper()
                    if row_symbol != sym:
                        continue
                    inst_type = (row.get("INSTRUMENT_TYPE") or "").strip().upper()
                    if inst_type not in {"ES", "ETF"}:
                        continue
                    security_id = row.get("SECURITY_ID") or row.get("SecurityId")
                    exch = (row.get("EXCH_ID") or "NSE").strip().upper()
                    exchange_segment = "BSE_EQ" if exch == "BSE" else "NSE_EQ"
                    if security_id:
                        break
            except Exception:
                security_id = None
                exchange_segment = None

            if security_id and exchange_segment:
                db = SessionLocal()
                try:
                    creds = db.query(DhanCredential).first()
                    access_token = (getattr(creds, "daily_token", None) or getattr(creds, "auth_token", None)) if creds else None
                    client_id = getattr(creds, "client_id", None) if creds else None
                finally:
                    db.close()

                if access_token and client_id:
                    headers = {
                        "access-token": access_token,
                        "client-id": client_id,
                        "Content-Type": "application/json",
                    }
                    payload = {exchange_segment: [int(str(security_id))]}
                    try:
                        response = requests.post("https://api.dhan.co/v2/marketfeed/quote", json=payload, headers=headers, timeout=8)
                        if response.status_code == 200:
                            body = response.json() or {}
                            seg_data = (body.get("data") or {}).get(exchange_segment) or {}
                            sec_key = str(security_id)
                            sec_payload = seg_data.get(sec_key) or seg_data.get(int(security_id))
                            if isinstance(sec_payload, list) and sec_payload:
                                sec_payload = sec_payload[0]

                            if isinstance(sec_payload, dict):
                                ltp = sec_payload.get("ltp") or sec_payload.get("LTP")
                                if ltp is None:
                                    ohlc = sec_payload.get("ohlc") or sec_payload.get("OHLC")
                                    if isinstance(ohlc, dict):
                                        ltp = ohlc.get("close") or ohlc.get("prev_close")
                                if ltp is not None:
                                    price = float(ltp)
                                    update_price(sym, price)
                    except Exception:
                        pass

            # Index fallback (NIFTY/BANKNIFTY/SENSEX) via static security map.
            if price is None:
                try:
                    from app.market.security_ids import get_default_index_security

                    index_meta = get_default_index_security(sym)
                    index_sec = index_meta.get("security_id") if index_meta else None
                    if index_sec:
                        db = SessionLocal()
                        try:
                            creds = db.query(DhanCredential).first()
                            access_token = (getattr(creds, "daily_token", None) or getattr(creds, "auth_token", None)) if creds else None
                            client_id = getattr(creds, "client_id", None) if creds else None
                        finally:
                            db.close()

                        if access_token and client_id:
                            headers = {
                                "access-token": access_token,
                                "client-id": client_id,
                                "Content-Type": "application/json",
                            }
                            payload = {"IDX_I": [int(str(index_sec))]}
                            response = requests.post("https://api.dhan.co/v2/marketfeed/quote", json=payload, headers=headers, timeout=8)
                            if response.status_code == 200:
                                body = response.json() or {}
                                sec_payload = ((body.get("data") or {}).get("IDX_I") or {}).get(str(index_sec))
                                if isinstance(sec_payload, list) and sec_payload:
                                    sec_payload = sec_payload[0]
                                if isinstance(sec_payload, dict):
                                    ltp = sec_payload.get("ltp") or sec_payload.get("LTP")
                                    if ltp is None:
                                        ohlc = sec_payload.get("ohlc") or sec_payload.get("OHLC")
                                        if isinstance(ohlc, dict):
                                            ltp = ohlc.get("close") or ohlc.get("prev_close")
                                    if ltp is not None:
                                        price = float(ltp)
                                        update_price(sym, price)
                except Exception:
                    pass

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
        database_status = {"status": "unknown", "message": "Not checked"}
        dhan_api_status = {"status": "unknown", "message": "Not checked"}
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
            from app.storage.db import SessionLocal
            from sqlalchemy import text

            db = SessionLocal()
            try:
                db.execute(text("SELECT 1"))
                database_status = {"status": "healthy", "message": "Connection OK"}
            finally:
                db.close()
        except Exception as db_err:
            database_status = {"status": "error", "message": f"{db_err}"}

        try:
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential

            db = SessionLocal()
            try:
                creds = db.query(DhanCredential).first()
                has_client = bool(getattr(creds, "client_id", None)) if creds else False
                has_token = bool(
                    (getattr(creds, "daily_token", None) or getattr(creds, "auth_token", None))
                ) if creds else False
            finally:
                db.close()

            ws_connected = (equity_ws.get("connected_connections") or 0) > 0 or (mcx_ws.get("connected_connections") or 0) > 0
            cooldown_active = bool(live_feed.get("cooldown_active"))

            if not (has_client and has_token):
                dhan_api_status = {
                    "status": "offline",
                    "message": "Missing Dhan credentials",
                }
            elif cooldown_active:
                dhan_api_status = {
                    "status": "warning",
                    "message": "Cooldown active (auto-retry in progress)",
                }
            elif ws_connected:
                dhan_api_status = {
                    "status": "healthy",
                    "message": "Credentials loaded and WebSocket connected",
                }
            elif live_feed.get("started"):
                dhan_api_status = {
                    "status": "warning",
                    "message": "Feed started, awaiting active WebSocket connections",
                }
            else:
                dhan_api_status = {
                    "status": "warning",
                    "message": "Credentials loaded, feed not started",
                }
        except Exception as dhan_err:
            dhan_api_status = {"status": "error", "message": f"{dhan_err}"}

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
                "database": database_status,
                "dhan_api": dhan_api_status,
                "market_open": market_open,
            },
        }
    except Exception as e:
        logging.exception("Failed to fetch market stream status: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market/etf-tierb-status")
def etf_tier_b_status():
    """Return Tier-B ETF coverage status for admin dashboard indicators."""
    try:
        from app.market.instrument_master.tier_b_etf_symbols import get_tier_b_etf_symbols
        from app.market.subscription_manager import get_subscription_manager

        expected = set(get_tier_b_etf_symbols())
        sub_mgr = get_subscription_manager()
        active_tier_b = sub_mgr.list_active_subscriptions(tier="TIER_B")

        subscribed_symbols = {
            str(row.get("symbol") or "").strip().upper()
            for row in active_tier_b
            if row.get("symbol")
        }
        subscribed_etfs = expected.intersection(subscribed_symbols)
        missing = sorted(expected - subscribed_etfs)

        if not expected:
            status = "disabled"
            message = "Tier-B equity feed disabled (equities are Tier-A watchlist-only)"
        elif not subscribed_etfs:
            status = "offline"
            message = "No Tier-B ETF subscriptions active"
        elif missing:
            status = "warning"
            message = f"{len(missing)} ETF symbols missing from Tier-B"
        else:
            status = "healthy"
            message = "All ETF symbols are subscribed in Tier-B"

        return {
            "status": "success",
            "data": {
                "service_status": status,
                "message": message,
                "expected_count": len(expected),
                "subscribed_count": len(subscribed_etfs),
                "missing_count": len(missing),
                "missing_symbols": missing[:100],
            },
        }
    except Exception as e:
        logger.exception("Failed to build ETF Tier-B status: %s", e)
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
