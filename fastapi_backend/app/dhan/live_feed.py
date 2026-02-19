"""
Official DhanHQ WebSocket feed implementation using dhanhq library

Phase 4 Enhancement: Dynamic subscription based on watchlist + Tier B always-on
- Tier A: User watchlist items (dynamic)
- Tier B: Always-on indices/MCX (NIFTY, BANKNIFTY, SENSEX, etc. - pre-loaded at startup)

RATE LIMITING & CONNECTION PROTECTION:
- Exponential backoff: 5s → 10s → 20s → 40s (max)
- Max retry attempts: 10 before cooldown
- Connection attempt tracking to prevent IP banning
- Graceful degradation if unable to connect
"""
import threading
import time
import asyncio
import importlib
import inspect
import socket
import os
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Optional
from dhanhq import dhanhq as DhanHQClient

try:
    from dhanhq.marketfeed import DhanFeed as _DhanFeed
except Exception:
    _DhanFeed = None

from app.market.live_prices import update_price, get_price
from app.market.subscription_manager import SUBSCRIPTION_MGR, _resolve_security_metadata
from app.market_orchestrator import get_orchestrator
from app.market.security_ids import (
    EXCHANGE_CODE_BSE,
    EXCHANGE_CODE_IDX,
    EXCHANGE_CODE_MCX,
    EXCHANGE_CODE_NSE,
    iter_default_index_targets,
    get_mcx_fallback,
    mcx_watch_symbols,
)
from app.storage.db import SessionLocal
from app.storage.models import DhanCredential, Watchlist

_started_lock = threading.Lock()
_started = False
_market_feed = None
_feed_lock_socket = None
_subscribed_securities: Dict[str, Dict[str, int]] = {}  # security_id -> {exchange, mode}
_subscription_lock = threading.RLock()
_security_id_symbol_map: Dict[str, str] = {}
_security_id_subscription_map: Dict[str, Dict[str, object]] = {}
_MCX_WATCH = mcx_watch_symbols()
_EXPIRY_FORMATS = ("%d%b%Y", "%d%B%Y", "%d%b%y", "%Y-%m-%d")
FEED_MODE_TICKER = 15
FEED_MODE_QUOTE = 17
_REST_CLIENT_LOCK = threading.Lock()
_REST_CLIENT: Optional[DhanHQClient] = None
_LAST_CLOSE_CACHE: Dict[str, Dict[str, object]] = {}
_LAST_TICK_CACHE: Dict[str, str] = {}
_LAST_DEPTH_CACHE: Dict[str, str] = {}
_LAST_ALERT_EMITTED: Dict[str, datetime] = {}
_ALERT_LOCK = threading.Lock()
_CRITICAL_INDEX_SYMBOLS = {"NIFTY", "BANKNIFTY", "SENSEX", "BANKEX", "FINNIFTY", "MIDCPNIFTY"}
logger = logging.getLogger("trading_nexus.dhan.live_feed")


def _exchange_name_from_code(exchange_code: Optional[int], segment: Optional[str] = None) -> str:
    if segment:
        segment_upper = str(segment).upper()
        if "MCX" in segment_upper:
            return "MCX"
        if "BSE" in segment_upper:
            return "BSE"
        if "NSE" in segment_upper or "NFO" in segment_upper:
            return "NSE"
    if exchange_code == EXCHANGE_CODE_MCX:
        return "MCX"
    if exchange_code == EXCHANGE_CODE_BSE:
        return "BSE"
    return "NSE"


def _resolve_feed_mode(meta: Optional[Dict[str, object]]) -> int:
    if not meta:
        return FEED_MODE_TICKER
    mode = meta.get("mode")
    if isinstance(mode, int):
        return mode
    if meta.get("option_type") in ("CE", "PE"):
        return FEED_MODE_QUOTE
    if meta.get("expiry") and meta.get("strike") is not None:
        return FEED_MODE_QUOTE
    return FEED_MODE_TICKER


def _emit_admin_alert(message: str, level: str = "WARN", key: Optional[str] = None, min_interval_seconds: int = 300) -> None:
    """Persist important live-feed events to Admin Alerts with basic throttling."""
    alert_key = str(key or message)
    now = datetime.now()

    with _ALERT_LOCK:
        last = _LAST_ALERT_EMITTED.get(alert_key)
        if last and (now - last).total_seconds() < max(1, int(min_interval_seconds)):
            return
        _LAST_ALERT_EMITTED[alert_key] = now

    db = None
    try:
        from app.notifications.notifier import notify

        db = SessionLocal()
        notify(db, message=message, level=level)
    except Exception as exc:
        logger.warning("Failed to emit admin alert '%s': %s", message, exc)
    finally:
        try:
            if db:
                db.close()
        except Exception:
            pass


def _apply_feed_target_limit(
    targets: Dict[str, Dict[str, object]],
    critical_ids: Optional[set] = None,
) -> Dict[str, Dict[str, object]]:
    """Hard-cap feed targets to reduce Dhan 429 risk while preserving critical symbols."""
    try:
        max_targets = int(os.getenv("LIVE_FEED_MAX_TARGETS", "300"))
    except Exception:
        max_targets = 300

    max_targets = max(50, max_targets)
    if len(targets) <= max_targets:
        return targets

    critical_ids = critical_ids or set()
    priority = []
    regular = []

    for sec_id, meta in targets.items():
        symbol = str(meta.get("symbol") or "").upper().strip()
        if sec_id in critical_ids or symbol in _CRITICAL_INDEX_SYMBOLS:
            priority.append((sec_id, meta))
        else:
            regular.append((sec_id, meta))

    kept_items = []
    for item in priority:
        if len(kept_items) >= max_targets:
            break
        kept_items.append(item)

    if len(kept_items) < max_targets:
        for item in regular:
            if len(kept_items) >= max_targets:
                break
            kept_items.append(item)

    trimmed_count = len(targets) - len(kept_items)
    trimmed_targets = {sec_id: meta for sec_id, meta in kept_items}

    logger.warning(
        "[LIVE_FEED] Target limit applied: requested=%s kept=%s trimmed=%s max=%s",
        len(targets),
        len(trimmed_targets),
        trimmed_count,
        max_targets,
    )
    _emit_admin_alert(
        message=f"Live feed target cap applied: kept {len(trimmed_targets)} of {len(targets)} targets (trimmed {trimmed_count}).",
        level="WARN",
        key="livefeed:target_cap",
        min_interval_seconds=600,
    )

    return trimmed_targets
def _ensure_rest_client(creds) -> Optional[DhanHQClient]:
    """Create/reuse a DhanHQ REST client for quote/close lookups."""
    global _REST_CLIENT
    if _REST_CLIENT:
        return _REST_CLIENT
    token = getattr(creds, "auth_token", None) or getattr(creds, "daily_token", None)
    if not creds or not creds.client_id or not token:
        return None
    with _REST_CLIENT_LOCK:
        if _REST_CLIENT:
            return _REST_CLIENT
        # Handle dhanhq client signature differences across versions
        try:
            _REST_CLIENT = DhanHQClient(creds.client_id, token)
        except TypeError:
            try:
                _REST_CLIENT = DhanHQClient(creds.client_id)
            except TypeError:
                _REST_CLIENT = DhanHQClient(token)
        return _REST_CLIENT

_LAST_CLOSE_CACHE_LOCK = threading.Lock()
_LAST_CLOSE_TTL = timedelta(hours=6)


def _resolve_dhan_feed_class():
    if _DhanFeed is not None:
        return _DhanFeed
    try:
        marketfeed = importlib.import_module("dhanhq.marketfeed")
    except Exception as exc:
        raise ImportError("dhanhq.marketfeed not available") from exc

    for name in (
        "DhanFeed",
        "MarketFeed",
        "MarketFeedV2",
        "DhanMarketFeed",
        "MarketFeedWS",
    ):
        cls = getattr(marketfeed, name, None)
        if cls is not None:
            return cls
    raise ImportError("No compatible Dhan feed class found in dhanhq.marketfeed")


def _create_dhan_feed(client_id: str, token: str, instruments):
    feed_cls = _resolve_dhan_feed_class()
    try:
        source = inspect.getsource(feed_cls)
    except Exception:
        source = ""

    wants_creds = "get_client_id" in source or "get_access_token" in source
    if wants_creds:
        class _Creds:
            def __init__(self, cid: str, tok: str):
                self._cid = cid
                self._tok = tok

            def get_client_id(self):
                return self._cid

            def get_access_token(self):
                return self._tok

        creds_obj = _Creds(client_id, token)
        try:
            return feed_cls(creds_obj, instruments)
        except TypeError:
            return feed_cls(creds_obj, token, instruments)

    try:
        return feed_cls(client_id, token, instruments, version="v2")
    except TypeError:
        return feed_cls(client_id, token, instruments)

# ==================== RATE LIMITING & CONNECTION PROTECTION ====================
# Exponential backoff to avoid IP banning from DhanHQ API
_connection_attempts = 0
_last_connection_attempt = None
_backoff_delay = 5  # Start with 5 seconds
_max_backoff_delay = 120  # Cap at 2 minutes
_consecutive_failures = 0
_max_consecutive_failures = 10
_cooldown_period = int(os.getenv("LIVE_FEED_COOLDOWN_SECONDS", "660"))  # default 11 minutes
_last_cooldown_start = None


def _trigger_cooldown(reason: str) -> None:
    global _last_cooldown_start, _consecutive_failures, _backoff_delay
    _last_cooldown_start = datetime.now()
    _consecutive_failures = _max_consecutive_failures
    _backoff_delay = _max_backoff_delay
    print(f"[COOLDOWN] Triggered due to {reason}. Cooling down for {_cooldown_period}s")
    _emit_admin_alert(
        message=f"Market data cooldown triggered ({reason}). Retry after {_cooldown_period}s.",
        level="ERROR",
        key=f"cooldown:{reason}",
        min_interval_seconds=max(300, _cooldown_period // 2),
    )


def reset_cooldown() -> None:
    global _last_cooldown_start, _consecutive_failures, _backoff_delay
    _last_cooldown_start = None
    _consecutive_failures = 0
    _backoff_delay = 5
    _emit_admin_alert(
        message="Market data cooldown cleared. Reconnect attempts resumed.",
        level="INFO",
        key="cooldown:reset",
        min_interval_seconds=120,
    )


def get_live_feed_status() -> Dict[str, object]:
    return {
        "started": _started,
        "connection_attempts": _connection_attempts,
        "consecutive_failures": _consecutive_failures,
        "last_connection_attempt": _last_connection_attempt.isoformat() if _last_connection_attempt else None,
        "cooldown_until": (
            (_last_cooldown_start + timedelta(seconds=_cooldown_period)).isoformat()
            if _last_cooldown_start
            else None
        ),
        "cooldown_active": bool(
            _last_cooldown_start and (datetime.now() - _last_cooldown_start).total_seconds() < _cooldown_period
        ),
    }


def get_live_feed_debug_snapshot(symbols: Optional[list[str]] = None, limit: int = 120) -> Dict[str, object]:
    symbol_filter = {
        str(s).strip().upper()
        for s in (symbols or [])
        if str(s).strip()
    }

    try:
        desired_targets = _get_security_ids_from_watchlist()
    except Exception:
        desired_targets = {}

    try:
        desired_by_symbol: Dict[str, list] = {}
        for sec_id, meta in desired_targets.items():
            sym = str(meta.get("symbol") or "").upper().strip()
            if not sym:
                continue
            desired_by_symbol.setdefault(sym, []).append(str(sec_id))
    except Exception:
        desired_by_symbol = {}

    with _subscription_lock:
        subscribed_map = dict(_subscribed_securities)
        sec_to_symbol = dict(_security_id_symbol_map)
        sec_to_option = dict(_security_id_subscription_map)
        tick_map = dict(_LAST_TICK_CACHE)
        depth_map = dict(_LAST_DEPTH_CACHE)

    sub_mgr_items = []
    try:
        with SUBSCRIPTION_MGR.lock:
            sub_mgr_items = list(SUBSCRIPTION_MGR.subscriptions.items())
    except Exception:
        sub_mgr_items = []

    active_by_symbol: Dict[str, list] = {}
    for sec_id, sym in sec_to_symbol.items():
        symbol_upper = str(sym or "").upper().strip()
        if not symbol_upper:
            continue
        payload = {
            "security_id": str(sec_id),
            "exchange": subscribed_map.get(str(sec_id), {}).get("exchange"),
            "mode": subscribed_map.get(str(sec_id), {}).get("mode"),
            "option_meta": sec_to_option.get(str(sec_id)),
        }
        active_by_symbol.setdefault(symbol_upper, []).append(payload)

    tier_by_symbol: Dict[str, Dict[str, int]] = {}
    for _token, sub_info in sub_mgr_items:
        sym = str(sub_info.get("symbol_canonical") or sub_info.get("symbol") or "").upper().strip()
        if not sym:
            continue
        tier = str(sub_info.get("tier") or "UNKNOWN").upper()
        if sym not in tier_by_symbol:
            tier_by_symbol[sym] = {}
        tier_by_symbol[sym][tier] = int(tier_by_symbol[sym].get(tier, 0)) + 1

    all_symbols = set(desired_by_symbol.keys()) | set(active_by_symbol.keys()) | set(tick_map.keys()) | set(depth_map.keys())
    if symbol_filter:
        all_symbols = {s for s in all_symbols if s in symbol_filter}

    rows = []
    for sym in sorted(all_symbols)[:max(1, int(limit))]:
        rows.append({
            "symbol": sym,
            "ltp_cache": get_price(sym),
            "last_tick_at": tick_map.get(sym),
            "last_depth_at": depth_map.get(sym),
            "desired_security_ids": desired_by_symbol.get(sym, []),
            "active_security_ids": [item.get("security_id") for item in active_by_symbol.get(sym, [])],
            "active_details": active_by_symbol.get(sym, [])[:8],
            "tier_breakdown": tier_by_symbol.get(sym, {}),
        })

    return {
        "feed_status": get_live_feed_status(),
        "desired_target_count": len(desired_targets),
        "active_security_count": len(subscribed_map),
        "symbol_map_count": len(sec_to_symbol),
        "option_map_count": len(sec_to_option),
        "rows": rows,
    }


def _acquire_feed_lock() -> bool:
    global _feed_lock_socket
    if _feed_lock_socket:
        return True
    port = int(os.getenv("LIVE_FEED_LOCK_PORT", "8765"))
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
        _feed_lock_socket = sock
        return True
    except OSError:
        print("[LOCK] Live feed lock already held; skipping duplicate feed start")
        return False

def _should_attempt_connection():
    """Check if we're allowed to attempt a connection (rate limiting)"""
    global _last_connection_attempt, _backoff_delay, _consecutive_failures, _last_cooldown_start
    
    # If in cooldown period, don't attempt
    if _last_cooldown_start:
        cooldown_elapsed = (datetime.now() - _last_cooldown_start).total_seconds()
        if cooldown_elapsed < _cooldown_period:
            remaining = _cooldown_period - cooldown_elapsed
            print(f"[COOLDOWN] IP protection active. Resuming in {int(remaining)}s...")
            return False
        else:
            _last_cooldown_start = None
            _consecutive_failures = 0
            _backoff_delay = 5
            print("[COOLDOWN] Cooldown period expired, resuming connection attempts...")
    
    # Check if we've exceeded max consecutive failures
    if _consecutive_failures >= _max_consecutive_failures:
        print(f"[BLOCK] Max connection failures reached ({_max_consecutive_failures}). Starting IP protection cooldown...")
        _last_cooldown_start = datetime.now()
        return False
    
    # Check backoff delay
    if _last_connection_attempt:
        elapsed = (datetime.now() - _last_connection_attempt).total_seconds()
        if elapsed < _backoff_delay:
            print(f"[WAIT] Connection backoff active. Retrying in {int(_backoff_delay - elapsed)}s...")
            return False
    
    return True

def _record_connection_attempt(success=False):
    """Track connection attempts for rate limiting"""
    global _last_connection_attempt, _backoff_delay, _consecutive_failures, _connection_attempts
    
    _last_connection_attempt = datetime.now()
    _connection_attempts += 1
    
    if success:
        _consecutive_failures = 0
        _backoff_delay = 5  # Reset backoff on success
        print(f"[OK] Connection successful! (attempt #{_connection_attempts})")
    else:
        _consecutive_failures += 1
        # Exponential backoff: 5s, 10s, 20s, 40s, 80s, 120s (max)
        _backoff_delay = min(_backoff_delay * 2, _max_backoff_delay)
        print(f"[RETRY] Connection failed. Attempt #{_connection_attempts}, "
              f"failures: {_consecutive_failures}/{_max_consecutive_failures}, "
              f"next retry in {_backoff_delay}s")


def _load_credentials():
    db = SessionLocal()
    try:
        row = db.query(DhanCredential).filter(DhanCredential.is_default == True).first()
        if row:
            return row
        return db.query(DhanCredential).first()
    finally:
        db.close()


def _exchange_segment_from_code(exchange_code: int) -> Optional[str]:
    """Map Dhan exchange codes to DhanHQ REST exchange segments."""
    if exchange_code == EXCHANGE_CODE_IDX:
        return "IDX_I"
    if exchange_code == EXCHANGE_CODE_NSE:
        return "NSE_EQ"
    if exchange_code == EXCHANGE_CODE_BSE:
        return "BSE_EQ"
    if exchange_code == EXCHANGE_CODE_MCX:
        return "MCX_COMM"
    return None


def _parse_last_close(response: Dict[str, object], exchange_segment: str, security_id: str) -> Optional[float]:
    """Parse last close from DhanHQ /marketfeed/quote response."""
    if not isinstance(response, dict):
        return None
    if response.get("status") != "success":
        return None

    data = response.get("data") or {}
    segment_data = None

    if isinstance(data, dict):
        segment_data = data.get(exchange_segment)
        if segment_data is None and "data" in data and isinstance(data.get("data"), dict):
            segment_data = data["data"].get(exchange_segment)

    if not isinstance(segment_data, dict):
        return None

    sec_payload = segment_data.get(str(security_id)) or segment_data.get(int(security_id))
    if isinstance(sec_payload, list) and sec_payload:
        sec_payload = sec_payload[0]

    if not isinstance(sec_payload, dict):
        return None

    ohlc = sec_payload.get("ohlc") or sec_payload.get("OHLC") or sec_payload.get("ohlc_data")
    if isinstance(ohlc, dict):
        close = (
            ohlc.get("close")
            or ohlc.get("closePrice")
            or ohlc.get("close_price")
            or ohlc.get("prev_close")
            or ohlc.get("previous_close")
        )
        if close is not None:
            return float(close)

    close = (
        sec_payload.get("close")
        or sec_payload.get("prev_close")
        or sec_payload.get("previous_close")
        or sec_payload.get("close_price")
    )
    if close is not None:
        return float(close)

    return None


def _get_last_close_price(security_id: str, exchange_code: Optional[int]) -> Optional[float]:
    """Fetch and cache last closing price using DhanHQ quote API."""
    if exchange_code is None:
        return None

    cache_key = f"{exchange_code}:{security_id}"
    now = datetime.now()

    with _LAST_CLOSE_CACHE_LOCK:
        cached = _LAST_CLOSE_CACHE.get(cache_key)
        if cached:
            fetched_at = cached.get("fetched_at")
            if isinstance(fetched_at, datetime) and now - fetched_at < _LAST_CLOSE_TTL:
                return cached.get("price")

    exchange_segment = _exchange_segment_from_code(exchange_code)
    if not exchange_segment:
        return None

    creds = _load_credentials()
    client = _ensure_rest_client(creds)
    if not client:
        return None

    try:
        response = client.quote_data({exchange_segment: [int(security_id)]})
        last_close = _parse_last_close(response, exchange_segment, security_id)

        if last_close is None:
            return None
        with _LAST_CLOSE_CACHE_LOCK:
            _LAST_CLOSE_CACHE[cache_key] = {
                "price": last_close,
                "fetched_at": now,
            }
        return last_close
    except Exception as exc:
        print(f"[WARN] Failed to fetch last close for {security_id}: {exc}")
        return None


def _normalize_expiry_value(expiry: Optional[object]) -> Optional[datetime]:
    if not expiry:
        return None
    if isinstance(expiry, datetime):
        return expiry
    if isinstance(expiry, date):
        return datetime.combine(expiry, datetime.min.time())
    text = str(expiry).strip().upper()
    for fmt in _EXPIRY_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _expiry_to_iso(expiry: Optional[object]) -> Optional[str]:
    if not expiry:
        return None
    if isinstance(expiry, datetime):
        return expiry.date().isoformat()
    if isinstance(expiry, date):
        return expiry.isoformat()
    parsed = _normalize_expiry_value(expiry)
    if parsed:
        return parsed.date().isoformat()
    text = str(expiry).strip()
    return text or None


def _build_default_index_targets() -> Dict[str, Dict[str, object]]:
    targets: Dict[str, Dict[str, object]] = {}
    for sec_id, meta in iter_default_index_targets().items():
        targets[str(sec_id)] = {
            "exchange": meta.get("exchange"),
            "symbol": meta.get("symbol"),
            "mode": FEED_MODE_TICKER,
        }
    return targets


def _resolve_mcx_feed_targets() -> Dict[str, Dict[str, object]]:
    targets: Dict[str, Dict[str, object]] = {}
    candidates: Dict[str, list] = {}

    try:
        for token, sub_info in SUBSCRIPTION_MGR.subscriptions.items():
            symbol = (sub_info.get("symbol_canonical") or sub_info.get("symbol") or "").upper()
            if symbol not in _MCX_WATCH:
                continue
            if sub_info.get("option_type"):
                continue  # only futures drive the always-on MCX feed
            sec_id = sub_info.get("security_id")
            exchange = sub_info.get("exchange")
            if not sec_id:
                continue
            expiry_dt = _normalize_expiry_value(sub_info.get("expiry"))
            candidates.setdefault(symbol, []).append((expiry_dt, str(sec_id), exchange))
    except Exception as exc:
        pass

    for symbol in _MCX_WATCH.keys():
        symbol_candidates = candidates.get(symbol, [])
        if symbol_candidates:
            symbol_candidates.sort(key=lambda item: (item[0] is None, item[0]))
            _, sec_id, exchange = symbol_candidates[0]
            targets[sec_id] = {
                "exchange": exchange or _MCX_WATCH[symbol]["exchange"],
                "symbol": symbol,
                "mode": FEED_MODE_TICKER,
            }
        else:
            fallback = get_mcx_fallback(symbol)
            if fallback:
                print(f"[MCX-RESOLVE] {symbol}: using fallback security_id={fallback['security_id']}")
                targets[str(fallback["security_id"])] = {
                    "exchange": fallback.get("exchange"),
                    "symbol": symbol,
                    "mode": FEED_MODE_TICKER,
                }

    return targets


def _refresh_symbol_map(targets: Dict[str, Dict[str, object]]):
    global _security_id_symbol_map
    _security_id_symbol_map = {
        str(sec_id): data.get("symbol", "") for sec_id, data in targets.items() if data.get("symbol")
    }


def _refresh_subscription_map(subscriptions: Dict[str, Dict[str, object]]):
    global _security_id_subscription_map
    _security_id_subscription_map = subscriptions


# Cache for expensive operations to avoid repeated calls
_last_db_load_time = 0
_last_db_load_ttl = 30  # seconds between DB loads
_mapper_initialized = False

def _get_security_ids_from_watchlist() -> Dict[str, Dict[str, object]]:
    """Return desired security targets keyed by security ID."""
    security_targets = {}
    subscription_map = {}

    def _ensure_mapper_loaded() -> None:
        global _mapper_initialized
        if _mapper_initialized:
            return
            
        try:
            from app.services.dhan_security_id_mapper import dhan_security_mapper
            if dhan_security_mapper.security_id_cache:
                _mapper_initialized = True
                return

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = None

            if loop is None:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Avoid blocking a running loop; skip and rely on later sync.
                return

            loop.run_until_complete(dhan_security_mapper.load_security_ids())
            _mapper_initialized = True
        except Exception:
            pass
    
    # Include active Tier A + Tier B subscriptions from subscription manager
    try:
        # ✨ CRITICAL: Load subscriptions from database first (with caching)
        global _last_db_load_time
        current_time = time.time()
        if current_time - _last_db_load_time < _last_db_load_ttl:
            # Use cached subscriptions - avoid expensive DB load
            pass
        else:
            SUBSCRIPTION_MGR._load_from_database()
            _last_db_load_time = current_time
        from app.services.dhan_security_id_mapper import dhan_security_mapper
        _ensure_mapper_loaded()
        
        synced_count = 0
        for token, sub_info in SUBSCRIPTION_MGR.subscriptions.items():
            symbol = (sub_info.get("symbol_canonical") or sub_info.get("symbol") or "").upper()
            tier = sub_info.get("tier", "").upper()
            if tier not in {"TIER_A", "TIER_B"}:
                continue
                
            # Resolve missing security metadata (DB-loaded subscriptions do not persist exchange/security_id)
            sec_id = sub_info.get("security_id")
            exchange = sub_info.get("exchange")
            if not sec_id or exchange is None:
                resolved = _resolve_security_metadata(
                    symbol=symbol,
                    expiry=sub_info.get("expiry"),
                    strike=sub_info.get("strike"),
                    option_type=sub_info.get("option_type"),
                )
                sec_id = resolved.get("security_id") or sec_id
                exchange = resolved.get("exchange") if resolved.get("exchange") is not None else exchange

            # Prefer real numeric security IDs for options from Dhan CSV mapper
            opt_type = (sub_info.get("option_type") or "").upper()
            if exchange == EXCHANGE_CODE_MCX:
                continue

            if opt_type in ("CE", "PE"):
                token_key = None
                if isinstance(sec_id, str) and sec_id.startswith(("CE_", "PE_")):
                    token_key = sec_id
                elif isinstance(token, str) and token.startswith(("CE_", "PE_")):
                    token_key = token
                else:
                    expiry_key = _expiry_to_iso(sub_info.get("expiry"))
                    strike_key = sub_info.get("strike")
                    if symbol and expiry_key and strike_key is not None:
                        token_key = f"{opt_type}_{symbol}_{float(strike_key)}_{expiry_key}"

                if token_key:
                    mapped_id = dhan_security_mapper.get_security_id(token_key)
                    option_data = dhan_security_mapper.get_option_data(token_key) if mapped_id else None
                    if mapped_id:
                        sec_id = str(mapped_id)
                        if option_data and exchange is None:
                            segment = (option_data.get("segment") or "").upper()
                            if "BSE" in segment and "FNO" in segment:
                                exchange = 8
                            else:
                                exchange = 2

            # Fallbacks (keep feed alive even if resolution fails)
            if not sec_id:
                sec_id = token
            # Fallback exchange for options when metadata is missing or defaulted to index
            if opt_type in ("CE", "PE") and (exchange is None or exchange == 0):
                exchange = 8 if symbol in {"SENSEX", "BANKEX"} else 2
            elif exchange is None:
                exchange = 0
            
            # Skip non-numeric option tokens when mapper can't resolve
            if opt_type in ("CE", "PE"):
                try:
                    int(str(sec_id))
                except (TypeError, ValueError):
                    continue

            if not sec_id:
                continue
            
            sec_id_str = str(sec_id)
            security_targets[sec_id_str] = {
                "exchange": exchange,
                "symbol": symbol,
                # Equities require QUOTE mode for reliable LTP updates in production.
                "mode": (
                    FEED_MODE_QUOTE
                    if opt_type in ("CE", "PE") or (not opt_type and not sub_info.get("expiry") and sub_info.get("strike") is None)
                    else FEED_MODE_TICKER
                ),
            }
            
            # Build subscription map for option chains
            expiry = _expiry_to_iso(sub_info.get("expiry"))
            strike = sub_info.get("strike")
            option_type = sub_info.get("option_type")
            
            if expiry and (strike is not None) and option_type:
                subscription_map[sec_id_str] = {
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": strike,
                    "option_type": option_type,
                }
            
            synced_count += 1
        
        print(f"[SYNC] Found {synced_count} active subscriptions to sync (Tier A + Tier B)")
        
    except Exception as e:
        print(f"[ERROR] Failed to load Tier B subscriptions: {e}")
        # Fallback to hardcoded defaults
        security_targets = _build_default_index_targets()
        security_targets.update(_resolve_mcx_feed_targets())

    # Include option instruments for NIFTY/BANKNIFTY/SENSEX (ATM-based strike windows)
    option_symbols = {"NIFTY", "BANKNIFTY", "SENSEX"}
    try:
        from app.services.dhan_security_id_mapper import dhan_security_mapper
        for token, sub_info in SUBSCRIPTION_MGR.subscriptions.items():
            symbol = (sub_info.get("symbol_canonical") or sub_info.get("symbol") or "").upper()
            option_type = (sub_info.get("option_type") or "").upper()
            if symbol not in option_symbols:
                continue
            if option_type not in ("CE", "PE"):
                continue

            sec_id = sub_info.get("security_id")
            exchange = sub_info.get("exchange")
            if not sec_id or exchange is None:
                resolved = _resolve_security_metadata(
                    symbol=symbol,
                    expiry=sub_info.get("expiry"),
                    strike=sub_info.get("strike"),
                    option_type=option_type,
                )
                sec_id = resolved.get("security_id") or sec_id
                exchange = resolved.get("exchange") if resolved.get("exchange") is not None else exchange

            token_key = None
            if isinstance(sec_id, str) and sec_id.startswith(("CE_", "PE_")):
                token_key = sec_id
            elif isinstance(token, str) and token.startswith(("CE_", "PE_")):
                token_key = token
            else:
                expiry_key = _expiry_to_iso(sub_info.get("expiry"))
                strike_key = sub_info.get("strike")
                if symbol and expiry_key and strike_key is not None:
                    token_key = f"{option_type}_{symbol}_{float(strike_key)}_{expiry_key}"

            if token_key:
                mapped_id = dhan_security_mapper.get_security_id(token_key)
                option_data = dhan_security_mapper.get_option_data(token_key) if mapped_id else None
                if mapped_id:
                    sec_id = str(mapped_id)
                    if option_data and exchange is None:
                        segment = (option_data.get("segment") or "").upper()
                        if "BSE" in segment and "FNO" in segment:
                            exchange = 8
                        else:
                            exchange = 2
            if option_type in ("CE", "PE") and (exchange is None or exchange == 0):
                exchange = 8 if symbol in {"SENSEX", "BANKEX"} else 2

            if option_type in ("CE", "PE"):
                try:
                    int(str(sec_id))
                except (TypeError, ValueError):
                    continue

            if not sec_id or exchange is None:
                continue

            sec_id_str = str(sec_id)
            security_targets[sec_id_str] = {
                "exchange": exchange,
                "symbol": symbol,
                "mode": FEED_MODE_QUOTE,
            }
            subscription_map[sec_id_str] = {
                "symbol": symbol,
                "expiry": _expiry_to_iso(sub_info.get("expiry")),
                "strike": sub_info.get("strike"),
                "option_type": option_type,
            }
    except Exception as e:
        print(f"[ERROR] Failed to load option subscriptions: {e}")

    # Always include underlying index targets for live ATM/LTP updates
    try:
        default_index_targets = _build_default_index_targets()
        security_targets.update(default_index_targets)
    except Exception as e:
        print(f"[ERROR] Failed to add default index targets: {e}")

    watchlist_equity_ids = set()

    # Ensure persisted watchlist equities are always included even if subscription state was not rebuilt.
    # This prevents empty equity feed targets after restarts/redeploys and keeps LTPs live for watchlist rows.
    try:
        db = SessionLocal()
        try:
            equity_rows = (
                db.query(Watchlist)
                .filter(Watchlist.instrument_type == "EQUITY")
                .all()
            )
        finally:
            db.close()

        for row in equity_rows:
            symbol = (getattr(row, "symbol", None) or "").strip().upper()
            if not symbol:
                continue

            resolved = _resolve_security_metadata(
                symbol=symbol,
                expiry=None,
                strike=None,
                option_type=None,
            )
            security_id = resolved.get("security_id")
            exchange = resolved.get("exchange")
            if not security_id:
                continue
            if exchange is None:
                exchange = EXCHANGE_CODE_NSE

            security_targets[str(security_id)] = {
                "exchange": exchange,
                "symbol": symbol,
                "mode": FEED_MODE_QUOTE,
            }
            watchlist_equity_ids.add(str(security_id))
    except Exception as e:
        print(f"[WARN] Failed to include watchlist equities in feed targets: {e}")

    security_targets = _apply_feed_target_limit(
        security_targets,
        critical_ids=watchlist_equity_ids,
    )

    if not security_targets:
        # Absolute fallback to ensure feed never starves
        security_targets = {
            "13": {"exchange": 0, "symbol": "NIFTY", "mode": FEED_MODE_TICKER},
            "51": {"exchange": 0, "symbol": "SENSEX", "mode": FEED_MODE_TICKER},
        }

    _refresh_symbol_map(security_targets)
    _refresh_subscription_map(subscription_map)
    return security_targets


def on_message_callback(feed, message):
    """Callback when market data is received"""
    if not message:
        return

    def _extract_security_id(payload: object) -> Optional[str]:
        if isinstance(payload, dict):
            for key in ("security_id", "securityId", "SecurityId", "sec_id", "token", "scrip_id", "scripId"):
                value = payload.get(key)
                if value is not None and str(value).strip() != "":
                    return str(value).strip()

            nested = payload.get("data")
            if nested is not None:
                nested_id = _extract_security_id(nested)
                if nested_id:
                    return nested_id

        if isinstance(payload, list):
            for item in payload:
                nested_id = _extract_security_id(item)
                if nested_id:
                    return nested_id
        return None

    def _extract_ltp(payload: Dict[str, object]) -> Optional[float]:
        if isinstance(payload, list):
            for item in payload:
                val = _extract_ltp(item)
                if val is not None:
                    return val
            return None

        if not isinstance(payload, dict):
            return None

        for key in (
            "LTP",
            "ltp",
            "Ltp",
            "last_traded_price",
            "lastTradedPrice",
            "last_price",
            "lastPrice",
            "last",
            "traded_price",
            "trade_price",
            "close",
            "Close",
            "price",
        ):
            if key in payload and payload[key] is not None:
                value = payload.get(key)
                if isinstance(value, str):
                    try:
                        value = float(value)
                    except ValueError:
                        continue
                if isinstance(value, (int, float)):
                    return float(value)

        for key in ("ltpc", "ohlc", "OHLC", "data", "payload", "tick", "quote", "response", "message"):
            nested = payload.get(key)
            if nested is not None:
                val = _extract_ltp(nested)
                if val is not None:
                    return val

        # Last-resort recursive scan through nested dict/list values.
        for nested in payload.values():
            if isinstance(nested, (dict, list)):
                val = _extract_ltp(nested)
                if val is not None:
                    return val
        return None

    def _extract_bid_ask(payload: Dict[str, object]) -> tuple[Optional[float], Optional[float]]:
        if not isinstance(payload, dict):
            return (None, None)

        def _extract(keys: tuple[str, ...]) -> Optional[float]:
            for key in keys:
                if key in payload and payload[key] is not None:
                    value = payload.get(key)
                    if isinstance(value, str):
                        try:
                            value = float(value)
                        except ValueError:
                            continue
                    if isinstance(value, (int, float)):
                        return float(value)
            return None

        bid = _extract(("BID", "bid", "best_bid", "best_bid_price", "bid_price", "bidPrice", "bp1"))
        ask = _extract(("ASK", "ask", "best_ask", "best_ask_price", "ask_price", "askPrice", "ap1"))

        if bid is None or ask is None:
            data = payload.get("data")
            if isinstance(data, dict):
                bid = bid if bid is not None else _extract_bid_ask(data)[0]
                ask = ask if ask is not None else _extract_bid_ask(data)[1]
        return (bid, ask)

    def _extract_depth(payload: Dict[str, object]) -> Optional[Dict[str, list]]:
        if not isinstance(payload, dict):
            return None

        depth = payload.get("depth") or payload.get("market_depth") or payload.get("depth_data")
        if isinstance(depth, dict):
            bids = depth.get("bids") or depth.get("bid") or depth.get("buy") or []
            asks = depth.get("asks") or depth.get("ask") or depth.get("sell") or []
        else:
            bids = payload.get("bids") or payload.get("bid") or payload.get("buy") or []
            asks = payload.get("asks") or payload.get("ask") or payload.get("sell") or []

        def _normalize_levels(levels: object) -> list:
            if not isinstance(levels, list):
                return []
            normalized = []
            for level in levels[:5]:
                if isinstance(level, dict):
                    price = level.get("price") or level.get("rate") or level.get("p")
                    qty = level.get("qty") or level.get("quantity") or level.get("q")
                elif isinstance(level, (list, tuple)) and len(level) >= 2:
                    price, qty = level[0], level[1]
                else:
                    continue

                try:
                    price_val = float(price)
                except (TypeError, ValueError):
                    continue
                try:
                    qty_val = float(qty) if qty is not None else 0.0
                except (TypeError, ValueError):
                    qty_val = 0.0

                normalized.append({"price": price_val, "qty": qty_val})
            return normalized

        norm_bids = _normalize_levels(bids)
        norm_asks = _normalize_levels(asks)
        if not norm_bids and not norm_asks:
            data = payload.get("data")
            if isinstance(data, dict):
                return _extract_depth(data)
        if not norm_bids and not norm_asks:
            return None
        return {"bids": norm_bids, "asks": norm_asks}
    
    try:
        # Extract security_id from message
        sec_id = _extract_security_id(message)
        if not sec_id:
            return
        
        # Convert to string for mapping
        sec_id_str = str(sec_id)
        
        symbol = _security_id_symbol_map.get(sec_id_str)
        if not symbol:
            return

        # If this security_id is an option instrument, update option LTP in cache
        option_meta = _security_id_subscription_map.get(sec_id_str)
        if option_meta:
            ltp = _extract_ltp(message)
            bid, ask = _extract_bid_ask(message)
            if (ltp is None or ltp == 0) and (bid is not None or ask is not None):
                if bid is not None and ask is not None and bid > 0 and ask > 0:
                    ltp = (bid + ask) / 2.0
                elif bid is not None and bid > 0:
                    ltp = bid
                elif ask is not None and ask > 0:
                    ltp = ask

            if ltp is None or ltp == 0:
                return

            _LAST_TICK_CACHE[symbol] = datetime.utcnow().isoformat()

            depth = _extract_depth(message)
            
            # ✨ CRITICAL: Update market state with depth data for square-off functionality
            try:
                from app.market.market_state import state
                if depth and (depth.get("bids") or depth.get("asks")):
                    state["depth"][symbol] = depth
                    _LAST_DEPTH_CACHE[symbol] = datetime.utcnow().isoformat()
            except Exception as state_e:
                print(f"[WARN] Failed to update market state depth: {state_e}")
            
            try:
                from app.services.authoritative_option_chain_service import authoritative_option_chain_service
                authoritative_option_chain_service.update_option_tick_from_websocket(
                    symbol=option_meta.get("symbol"),
                    expiry=option_meta.get("expiry"),
                    strike=option_meta.get("strike"),
                    option_type=option_meta.get("option_type"),
                    ltp=ltp,
                    bid=bid,
                    ask=ask,
                    depth=depth,
                )
            except Exception as cache_e:
                print(f"[WARN] Failed to update option cache for {sec_id_str}: {cache_e}")

            try:
                orchestrator = get_orchestrator()
                exchange_name = _exchange_name_from_code(option_meta.get("exchange"), option_meta.get("segment"))
                segment_name = (option_meta.get("segment") or exchange_name).upper()
                orchestrator.on_tick({
                    "exchange": exchange_name,
                    "segment": segment_name,
                    "symbol": option_meta.get("symbol"),
                    "expiry": option_meta.get("expiry"),
                    "strike": option_meta.get("strike"),
                    "option_type": option_meta.get("option_type"),
                    "ltp": ltp,
                    "bid": bid,
                    "ask": ask,
                    "depth": depth,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            except Exception:
                pass
            return
        
        # Extract LTP (Last Traded Price) for underlying
        ltp = _extract_ltp(message)
        bid, ask = _extract_bid_ask(message)
        if (ltp is None or ltp <= 0) and (bid is not None or ask is not None):
            if bid is not None and ask is not None and bid > 0 and ask > 0:
                ltp = (bid + ask) / 2.0
            elif bid is not None and bid > 0:
                ltp = bid
            elif ask is not None and ask > 0:
                ltp = ask

        if ltp is None or ltp <= 0:
            existing_price = get_price(symbol)
            if existing_price and existing_price > 0:
                return
            try:
                from app.ems.exchange_clock import is_market_open
                exchange_code = _subscribed_securities.get(sec_id_str, {}).get("exchange")
                exchange_name = _exchange_name_from_code(exchange_code)
                if exchange_name and is_market_open(exchange_name):
                    # During market hours, don't overwrite with stale previous close.
                    return
            except Exception:
                pass
            exchange_code = _subscribed_securities.get(sec_id_str, {}).get("exchange")
            last_close = _get_last_close_price(sec_id_str, exchange_code)
            if last_close is not None:
                update_price(symbol, last_close)
                logger.debug("[PRICE] %s = %s (last close)", symbol, last_close)
            return

        update_price(symbol, ltp)
        _LAST_TICK_CACHE[symbol] = datetime.utcnow().isoformat()
        logger.debug("[PRICE] %s = %s", symbol, ltp)

        # ✨ CRITICAL: Update market state with depth data for non-option instruments
        try:
            from app.market.market_state import state
            depth = _extract_depth(message)
            if depth and (depth.get("bids") or depth.get("asks")):
                state["depth"][symbol] = depth
                _LAST_DEPTH_CACHE[symbol] = datetime.utcnow().isoformat()
        except Exception as state_e:
            print(f"[WARN] Failed to update market state depth for {symbol}: {state_e}")

        try:
            orchestrator = get_orchestrator()
            is_index = symbol in ("NIFTY", "BANKNIFTY", "SENSEX", "BANKEX")
            exchange_code = _subscribed_securities.get(sec_id_str, {}).get("exchange")
            exchange_name = _exchange_name_from_code(exchange_code)
            if is_index and symbol in ("SENSEX", "BANKEX"):
                exchange_name = "BSE"
            segment_name = _exchange_segment_from_code(exchange_code) or exchange_name
            orchestrator.on_tick({
                "exchange": exchange_name,
                "segment": segment_name,
                "symbol": symbol,
                "ltp": ltp,
                "is_index": is_index,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass
        
        # ✨ NEW: Update the option chain cache with new underlying price
        # This ensures option strikes are re-estimated when underlying price changes
        try:
            from app.services.authoritative_option_chain_service import authoritative_option_chain_service
            updated_strikes = authoritative_option_chain_service.update_option_price_from_websocket(
                symbol=symbol,
                ltp=ltp
            )
            if updated_strikes > 0:
                # Cache was updated with new LTP - option chains now have estimated premiums
                pass
        except Exception as cache_e:
            # Don't fail price update if cache update fails
            print(f"[WARN] Failed to update option cache for {symbol}: {cache_e}")
        
    except Exception as e:
        print(f"[ERROR] Price update failed: {e}")


def sync_subscriptions_with_watchlist():
    """
    Phase 4: Synchronize DhanHQ subscriptions with current watchlist + Tier B.
    
    Call this periodically to subscribe to new watchlist items and
    maintain Tier B subscriptions.
    """
    global _subscribed_securities
    
    with _subscription_lock:
        try:
            desired_targets = _get_security_ids_from_watchlist()
            desired_ids = set(desired_targets.keys())
            current_ids = set(_subscribed_securities.keys())
            
            # Only sync if there are actual changes
            to_subscribe = desired_ids - current_ids
            to_unsubscribe = current_ids - desired_ids
            
            if not to_subscribe and not to_unsubscribe:
                return  # No changes - skip expensive operations
            
            # Subscribe to new securities only when feed is available
            if to_subscribe and _market_feed:
                for sec_id in to_subscribe:
                    meta = desired_targets.get(sec_id)
                    exchange = meta.get("exchange") if meta else None
                    if exchange is None:
                        continue
                    try:
                        mode = _resolve_feed_mode(meta)
                        _market_feed.subscribe_symbols([(exchange, sec_id, mode)])
                        _subscribed_securities[sec_id] = {"exchange": exchange, "mode": mode}
                        try:
                            orchestrator = get_orchestrator()
                            exchange_name = _exchange_name_from_code(exchange, meta.get("segment") if meta else None)
                            segment_name = (meta.get("segment") or exchange_name).upper() if meta else exchange_name
                            orchestrator.subscribe(
                                token=str(sec_id),
                                exchange=exchange_name,
                                segment=segment_name,
                                symbol=meta.get("symbol") if meta else str(sec_id),
                                expiry=meta.get("expiry") if meta else None,
                                meta=meta or {},
                            )
                        except Exception:
                            pass
                        print(f"[SUBSCRIBE] Security {sec_id} subscribed")
                    except Exception as e:
                        print(f"[WARN] Failed to subscribe {sec_id}: {e}")
            
            # Unsubscribe anything that's no longer desired
            if to_unsubscribe and _market_feed:
                for sec_id in to_unsubscribe:
                    sub_meta = _subscribed_securities.get(sec_id) or {}
                    exchange = sub_meta.get("exchange")
                    mode = sub_meta.get("mode") or FEED_MODE_TICKER
                    if exchange is None:
                        continue
                    try:
                        _market_feed.unsubscribe_symbols([(exchange, sec_id, mode)])
                        _subscribed_securities.pop(sec_id, None)
                        try:
                            orchestrator = get_orchestrator()
                            orchestrator.unsubscribe(str(sec_id))
                        except Exception:
                            pass
                        print(f"[UNSUBSCRIBE] Security {sec_id} unsubscribed")
                    except Exception as e:
                        print(f"[WARN] Failed to unsubscribe {sec_id}: {e}")
        
        except Exception as e:
            print(f"[ERROR] Sync subscriptions failed: {e}")

def start_live_feed():
    """
    Start official DhanHQ WebSocket feed with Phase 4 dynamic subscriptions.
    
    Subscribes to:
    - Tier B: Always-on (NIFTY, BANKNIFTY, SENSEX, etc. - pre-loaded at startup)
    - Tier A: User watchlist items (dynamic - changes as users add/remove)
    """
    global _started, _market_feed

    # Hard safety switch: never attempt outbound Dhan connections when streams are disabled.
    flag = (os.getenv("DISABLE_DHAN_WS") or os.getenv("BACKEND_OFFLINE") or os.getenv("DISABLE_MARKET_STREAMS") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        print("[INFO] Live feed start skipped (streams disabled via env flag)")
        return

    # Runtime admin kill-switch.
    try:
        from app.market.dhan_connection_guard import ensure_enabled
        ensure_enabled("Dhan WebSocket")
    except Exception:
        print("[INFO] Live feed start skipped (manually disconnected via admin switch)")
        return
    
    with _started_lock:
        if _started:
            return
        if not _acquire_feed_lock():
            return
        _started = True
    
    def run_feed():
        global _market_feed
        # Ensure an event loop exists in this thread (required by dhanhq)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        sync_counter = 0
        
        while True:
            try:
                # Emergency admin disconnect: keep WS closed and do not attempt reconnect.
                try:
                    from app.market.dhan_connection_guard import is_enabled
                    if not is_enabled():
                        if _market_feed:
                            try:
                                _market_feed.close_connection()
                            except Exception:
                                pass
                        try:
                            from app.market.ws_manager import get_ws_manager
                            get_ws_manager().disconnect(1, error="manually_disconnected")
                        except Exception:
                            pass
                        time.sleep(2)
                        continue
                except Exception:
                    # If guard import fails for any reason, do not block connectivity.
                    pass

                # ========== RATE LIMITING: CHECK IF WE CAN ATTEMPT CONNECTION ==========
                if not _should_attempt_connection():
                    time.sleep(5)  # Check again in 5 seconds
                    continue
                
                creds = _load_credentials()
                token = (getattr(creds, "auth_token", None) or getattr(creds, "daily_token", None)) if creds else None
                if not creds or not creds.client_id or not token:
                    print("[WARN] No Dhan credentials - waiting...")
                    _emit_admin_alert(
                        message="Dhan credentials missing or invalid; live feed waiting for valid credentials.",
                        level="WARN",
                        key="livefeed:missing_credentials",
                        min_interval_seconds=600,
                    )
                    _record_connection_attempt(success=False)
                    time.sleep(10)
                    continue
                
                # Get initial security targets for Tier B instruments
                initial_targets = _get_security_ids_from_watchlist()
                if not initial_targets:
                    print("[WARN] No securities to subscribe to")
                    _emit_admin_alert(
                        message="Live feed found no eligible securities to subscribe.",
                        level="WARN",
                        key="livefeed:no_targets",
                        min_interval_seconds=600,
                    )
                    _record_connection_attempt(success=False)
                    time.sleep(10)
                    continue
                
                # Convert security IDs to DhanHQ format
                instruments = []
                for sec_id, meta in initial_targets.items():
                    exchange = meta.get("exchange")
                    if exchange is None:
                        continue
                    mode = _resolve_feed_mode(meta)
                    instruments.append((exchange, sec_id, mode))
                
                # Create DhanFeed (compatible with multiple dhanhq versions)
                try:
                    _market_feed = _create_dhan_feed(creds.client_id, token, instruments)
                except Exception as e:
                    print(f"[ERROR] Failed to create DhanFeed instance: {e}")
                    import traceback
                    traceback.print_exc()
                    _record_connection_attempt(success=False)
                    time.sleep(10)
                    continue
                
                print(f"[OK] Starting Dhan WebSocket feed (Phase 4 Dynamic)")
                print(f"[OK] Initial subscriptions: {len(instruments)} securities")
                print(f"[INFO] Rate limiting active: max {_max_consecutive_failures} failures before cooldown")
                
                # Track subscriptions and register with WebSocket Manager
                _subscribed_securities.update({
                    str(sec): {"exchange": exchange, "mode": mode}
                    for exchange, sec, mode in instruments
                })

                # Register subscriptions with orchestrator
                orchestrator = get_orchestrator()
                for exchange, sec_id, _ in instruments:
                    meta = initial_targets.get(str(sec_id)) or {}
                    exchange_name = _exchange_name_from_code(exchange, meta.get("segment"))
                    segment_name = (meta.get("segment") or exchange_name).upper()
                    success, _reason, assigned_ws_id = orchestrator.subscribe(
                        token=str(sec_id),
                        exchange=exchange_name,
                        segment=segment_name,
                        symbol=meta.get("symbol") or str(sec_id),
                        expiry=meta.get("expiry"),
                        meta=meta,
                    )
                    if success:
                        print(f"[WS-MGR] Registered {sec_id} with WS-{assigned_ws_id}")
                
                _record_connection_attempt(success=True)
                
                print("[OK] Connecting to DhanHQ WebSocket...")
                _emit_admin_alert(
                    message=f"Dhan WebSocket connected with {len(instruments)} subscriptions.",
                    level="INFO",
                    key="livefeed:connected",
                    min_interval_seconds=300,
                )

                # Mark WebSocket connection as active in orchestrator
                orchestrator.on_connected(1, _market_feed)  # Use WS-1 for the main feed
                print("[WS-MGR] WebSocket connection marked as active")
                
                # Mark connection active in WS manager for admin visibility
                try:
                    from app.market.ws_manager import get_ws_manager
                    ws_mgr = get_ws_manager()
                    ws_mgr.connect(1, _market_feed)
                except Exception:
                    pass
                
                # Establish and maintain WebSocket connection once
                try:
                    logger.debug("Calling _market_feed.run_forever()")
                    _market_feed.run_forever()
                except Exception as e:
                    print(f"[ERROR] _market_feed.run_forever() crashed: {e}")
                    _emit_admin_alert(
                        message=f"Dhan WebSocket runtime error: {e}",
                        level="ERROR",
                        key=f"livefeed:run_forever:{str(e)[:80]}",
                        min_interval_seconds=180,
                    )
                    # If it's an authorization failure, trigger cooldown
                    if "401" in str(e) or "Unauthorized" in str(e) or "Access Token" in str(e):
                         _trigger_cooldown("Authorization Failed")
                    elif "1006" in str(e) or "Connection closed" in str(e):
                        # Connection closed cleanly or uncleanly
                        print("[WARN] Connection closed by server.")
                    raise e # Re-raise to trigger outer loop retry logic


                # Main data loop
                while True:
                    try:
                        # Phase 4: Periodically sync subscriptions with watchlist
                        sync_counter += 1
                        if sync_counter >= 10000:  # Sync every ~10 seconds (10000 × 1ms)
                            sync_subscriptions_with_watchlist()
                            sync_counter = 0

                        # Fetch and process data
                        response = _market_feed.get_data()
                        if response:
                            on_message_callback(_market_feed, response)

                        time.sleep(0.001)  # 1ms delay (reduced from 10ms for better latency)

                    except Exception as e:
                        print(f"[ERROR] Data fetch error: {e}")
                        print("[WARN] WebSocket connection lost, will reconnect with backoff...")
                        _emit_admin_alert(
                            message=f"Dhan WebSocket data loop error: {e}",
                            level="ERROR",
                            key=f"livefeed:data_loop:{str(e)[:80]}",
                            min_interval_seconds=180,
                        )
                        try:
                            from app.market.ws_manager import get_ws_manager
                            ws_mgr = get_ws_manager()
                            ws_mgr.disconnect(1, error=str(e))
                        except Exception:
                            pass
                        _record_connection_attempt(success=False)
                        time.sleep(1)
                        break
                
            except ConnectionError as e:
                print(f"[ERROR] DhanHQ connection error: {e}")
                print("[WARN] Connection rejected - likely due to rate limiting or credentials issue")
                _emit_admin_alert(
                    message=f"Dhan WebSocket connection error: {e}",
                    level="ERROR",
                    key=f"livefeed:connection_error:{str(e)[:80]}",
                    min_interval_seconds=180,
                )
                if "429" in str(e):
                    _trigger_cooldown("HTTP_429")
                try:
                    from app.market.ws_manager import get_ws_manager
                    ws_mgr = get_ws_manager()
                    ws_mgr.disconnect(1, error=str(e))
                except Exception:
                    pass
                _record_connection_attempt(success=False)
                time.sleep(5)
            except Exception as e:
                print(f"[ERROR] Dhan feed crashed: {e}")
                _emit_admin_alert(
                    message=f"Dhan feed crashed: {e}",
                    level="ERROR",
                    key=f"livefeed:crashed:{str(e)[:80]}",
                    min_interval_seconds=180,
                )
                if "429" in str(e):
                    _trigger_cooldown("HTTP_429")
                try:
                    from app.market.ws_manager import get_ws_manager
                    ws_mgr = get_ws_manager()
                    ws_mgr.disconnect(1, error=str(e))
                except Exception:
                    pass
                _record_connection_attempt(success=False)
                time.sleep(5)
    
    # Start in background thread
    feed_thread = threading.Thread(target=run_feed, daemon=True)
    feed_thread.start()
    print("[OK] Dhan feed thread started (Phase 4 Dynamic Subscriptions)")
    print("[INFO] Rate limiting active to prevent IP banning:")
    print(f"       • Exponential backoff: 5s → 10s → 20s → 40s (max {_max_backoff_delay}s)")
    print(f"       • Max connection attempts: {_max_consecutive_failures} before 1-hour cooldown")
    print(f"       • This protects against DhanHQ rate limiting and IP bans")


def stop_live_feed():
    """Stop the feed gracefully"""
    global _market_feed
    if _market_feed:
        try:
            _market_feed.close_connection()
        except:
            pass
