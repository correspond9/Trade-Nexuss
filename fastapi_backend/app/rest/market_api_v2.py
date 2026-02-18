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
from app.services.dhan_sdk_bridge import sdk_quote_data

router = APIRouter()
logger = logging.getLogger(__name__)
_stream_recovery_lock = threading.Lock()
_last_stream_recovery_attempt = 0.0


def _commodities_enabled() -> bool:
    return (os.getenv("ENABLE_COMMODITIES") or "").strip().lower() in ("1", "true", "yes", "on")


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


def _extract_segment_payload(quote_data: object, exchange_segment: str):
    if not isinstance(quote_data, dict):
        return None

    segment_data = quote_data.get(exchange_segment)
    if isinstance(segment_data, dict):
        return segment_data

    nested = quote_data.get("data")
    if isinstance(nested, dict):
        nested_segment = nested.get(exchange_segment)
        if isinstance(nested_segment, dict):
            return nested_segment

    return None


def _extract_ltp_from_quote_payload(sec_payload: object) -> Optional[float]:
    if isinstance(sec_payload, list):
        sec_payload = sec_payload[0] if sec_payload else None

    if not isinstance(sec_payload, dict):
        return None

    ltp = sec_payload.get("ltp") or sec_payload.get("LTP")
    if ltp is None:
        ohlc = sec_payload.get("ohlc") or sec_payload.get("OHLC")
        if isinstance(ohlc, dict):
            ltp = (
                ohlc.get("close")
                or ohlc.get("ltp")
                or ohlc.get("last_price")
                or ohlc.get("prev_close")
            )

    if ltp is None:
        ltp = (
            sec_payload.get("close")
            or sec_payload.get("last_price")
            or sec_payload.get("prev_close")
        )

    try:
        value = float(ltp)
        if value > 0:
            return value
    except Exception:
        return None
    return None


def _extract_ltp_from_sdk_quote_result(sdk_result: dict, exchange_segment: str, security_id: object) -> Optional[float]:
    if not isinstance(sdk_result, dict) or not sdk_result.get("ok"):
        return None

    body = sdk_result.get("data") or {}
    segment_data = _extract_segment_payload(body, exchange_segment)
    if not isinstance(segment_data, dict):
        return None

    sec_key = str(security_id)
    sec_payload = segment_data.get(sec_key)
    if sec_payload is None:
        try:
            sec_payload = segment_data.get(int(sec_key))
        except Exception:
            sec_payload = None

    return _extract_ltp_from_quote_payload(sec_payload)


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
        try:
            if price is not None and float(price) <= 0:
                price = None
        except Exception:
            price = None

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
                    if inst_type not in {"ES", "ETF", "EQUITY", "EQ"}:
                        continue
                    security_id = row.get("SECURITY_ID") or row.get("SecurityId")
                    exch = (row.get("EXCH_ID") or "NSE").strip().upper()
                    exchange_segment = "BSE_EQ" if exch == "BSE" else "NSE_EQ"
                    if security_id:
                        break
            except Exception:
                security_id = None
                exchange_segment = None

            # Secondary fallback: resolve from broader registry pools (handles symbols missing in NSE equity slice).
            if not (security_id and exchange_segment):
                try:
                    candidate_rows = []
                    candidate_rows.extend(REGISTRY.get_by_symbol(sym) or [])
                    candidate_rows.extend(REGISTRY.by_underlying.get(sym, []) or [])

                    for row in candidate_rows:
                        sec = row.get("SECURITY_ID") or row.get("SecurityId")
                        if not sec:
                            continue
                        exch = (row.get("EXCH_ID") or "").strip().upper()
                        segment = (row.get("SEGMENT") or "").strip().upper()
                        inst_type = (row.get("INSTRUMENT_TYPE") or "").strip().upper()

                        mapped = None
                        if exch == "NSE":
                            mapped = "NSE_EQ" if segment == "E" or inst_type in {"EQUITY", "ES", "ETF", "EQ"} else "NSE_FNO"
                        elif exch == "BSE":
                            mapped = "BSE_EQ" if segment == "E" or inst_type in {"EQUITY", "ES", "ETF", "EQ"} else "BSE_FNO"
                        elif exch == "MCX":
                            mapped = "MCX_COMM"

                        if mapped:
                            security_id = sec
                            exchange_segment = mapped
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
                    segment_candidates = [exchange_segment]
                    if exchange_segment == "NSE_EQ":
                        segment_candidates.append("BSE_EQ")
                    elif exchange_segment == "BSE_EQ":
                        segment_candidates.append("NSE_EQ")

                    for segment_candidate in segment_candidates:
                        payload = {segment_candidate: [int(str(security_id))]}
                        try:
                            sdk_result = sdk_quote_data(
                                creds={"client_id": client_id, "access_token": access_token},
                                securities=payload,
                            )
                            ltp_value = _extract_ltp_from_sdk_quote_result(
                                sdk_result=sdk_result,
                                exchange_segment=segment_candidate,
                                security_id=security_id,
                            )
                            if ltp_value is not None:
                                price = float(ltp_value)
                                update_price(sym, price)
                                break
                        except Exception:
                            continue

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
                            payload = {"IDX_I": [int(str(index_sec))]}
                            sdk_result = sdk_quote_data(
                                creds={"client_id": client_id, "access_token": access_token},
                                securities=payload,
                            )
                            ltp_value = _extract_ltp_from_sdk_quote_result(
                                sdk_result=sdk_result,
                                exchange_segment="IDX_I",
                                security_id=index_sec,
                            )
                            if ltp_value is not None:
                                price = float(ltp_value)
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

        if _commodities_enabled():
            try:
                from app.commodity_engine.commodity_ws_manager import commodity_ws_manager
                mcx_ws = commodity_ws_manager.get_status()
            except Exception:
                mcx_ws = {"connected_connections": 0, "total_subscriptions": 0}
        else:
            mcx_ws = {"connected_connections": 0, "total_subscriptions": 0, "status": "disabled"}

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
            message = "Tier-B ETF feed disabled"
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


@router.get("/market/depth/{symbol}")
def market_depth(symbol: str):
    """Return best-known top-5 depth for non-option instruments (equity/index/futures)."""
    try:
        _maybe_recover_streams()
        sym = (symbol or "").strip().upper()
        if not sym:
            raise HTTPException(status_code=400, detail="symbol is required")

        try:
            from app.market.market_state import state
            cached = (state.get("depth") or {}).get(sym)
            if isinstance(cached, dict):
                bids = cached.get("bids") if isinstance(cached.get("bids"), list) else []
                asks = cached.get("asks") if isinstance(cached.get("asks"), list) else []
                if bids or asks:
                    return {
                        "status": "success",
                        "data": {
                            "bids": bids[:5],
                            "asks": asks[:5],
                        },
                    }
        except Exception:
            pass

        from app.market.instrument_master.registry import REGISTRY
        from app.storage.db import SessionLocal
        from app.storage.models import DhanCredential
        from app.market.security_ids import get_default_index_security

        if not REGISTRY.loaded:
            REGISTRY.load()

        exchange_segment = None
        security_id = None

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

        if not security_id:
            try:
                index_meta = get_default_index_security(sym) or {}
                index_sec = index_meta.get("security_id")
                if index_sec:
                    security_id = index_sec
                    exchange_segment = "IDX_I"
            except Exception:
                security_id = None
                exchange_segment = None

        if not security_id or not exchange_segment:
            return {"status": "success", "data": {"bids": [], "asks": []}}

        db = SessionLocal()
        try:
            creds = db.query(DhanCredential).first()
            access_token = (getattr(creds, "daily_token", None) or getattr(creds, "auth_token", None)) if creds else None
            client_id = getattr(creds, "client_id", None) if creds else None
        finally:
            db.close()

        if not access_token or not client_id:
            return {"status": "success", "data": {"bids": [], "asks": []}}

        payload = {exchange_segment: [int(str(security_id))]}
        sdk_result = sdk_quote_data(
            creds={"client_id": client_id, "access_token": access_token},
            securities=payload,
        )
        if not sdk_result.get("ok"):
            return {"status": "success", "data": {"bids": [], "asks": []}}

        body = sdk_result.get("data") or {}
        seg_data = (body.get("data") or {}).get(exchange_segment) or {}
        sec_key = str(security_id)
        sec_payload = seg_data.get(sec_key) or seg_data.get(int(security_id))
        if isinstance(sec_payload, list) and sec_payload:
            sec_payload = sec_payload[0]

        if not isinstance(sec_payload, dict):
            return {"status": "success", "data": {"bids": [], "asks": []}}

        raw_depth = sec_payload.get("depth") or sec_payload.get("market_depth") or {}
        bids = raw_depth.get("buy") or raw_depth.get("bids") or []
        asks = raw_depth.get("sell") or raw_depth.get("asks") or []

        def _norm(levels):
            out = []
            if not isinstance(levels, list):
                return out
            for level in levels[:5]:
                if isinstance(level, dict):
                    price = level.get("price") or level.get("rate") or level.get("p")
                    qty = level.get("quantity") or level.get("qty") or level.get("q")
                elif isinstance(level, (list, tuple)) and len(level) >= 2:
                    price, qty = level[0], level[1]
                else:
                    continue
                try:
                    price_val = float(price)
                except Exception:
                    continue
                try:
                    qty_val = float(qty) if qty is not None else 0.0
                except Exception:
                    qty_val = 0.0
                out.append({"price": price_val, "qty": qty_val})
            return out

        return {
            "status": "success",
            "data": {
                "bids": _norm(bids),
                "asks": _norm(asks),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to fetch market depth: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
