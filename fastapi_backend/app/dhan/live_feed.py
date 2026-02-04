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
from datetime import datetime, timedelta
from typing import Dict, Optional
from dhanhq import DhanContext, dhanhq as DhanHQClient, MarketFeed

from app.market.live_prices import update_price
from app.market.subscription_manager import SUBSCRIPTION_MGR
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
_subscribed_securities: Dict[str, int] = {}  # security_id -> exchange
_subscription_lock = threading.RLock()
_security_id_symbol_map: Dict[str, str] = {}
_security_id_subscription_map: Dict[str, Dict[str, object]] = {}
_MCX_WATCH = mcx_watch_symbols()
_EXPIRY_FORMATS = ("%d%b%Y", "%d%B%Y", "%d%b%y", "%Y-%m-%d")
_REST_CLIENT_LOCK = threading.Lock()
_REST_CLIENT: Optional[DhanHQClient] = None
_LAST_CLOSE_CACHE: Dict[str, Dict[str, object]] = {}
_LAST_CLOSE_CACHE_LOCK = threading.Lock()
_LAST_CLOSE_TTL = timedelta(hours=6)

# ==================== RATE LIMITING & CONNECTION PROTECTION ====================
# Exponential backoff to avoid IP banning from DhanHQ API
_connection_attempts = 0
_last_connection_attempt = None
_backoff_delay = 5  # Start with 5 seconds
_max_backoff_delay = 120  # Cap at 2 minutes
_consecutive_failures = 0
_max_consecutive_failures = 10
_cooldown_period = 3600  # 1 hour cooldown after max failures (protects against IP ban)
_last_cooldown_start = None

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
        dhan_context = DhanContext(client_id=creds.client_id, access_token=token)
        dhan_client = DhanHQClient(dhan_context)
        _REST_CLIENT = dhan_client
        return _REST_CLIENT


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


def _normalize_expiry_value(expiry: Optional[str]) -> Optional[datetime]:
    if not expiry:
        return None
    text = expiry.strip().upper()
    for fmt in _EXPIRY_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _build_default_index_targets() -> Dict[str, Dict[str, object]]:
    targets: Dict[str, Dict[str, object]] = {}
    for sec_id, meta in iter_default_index_targets().items():
        targets[str(sec_id)] = {
            "exchange": meta.get("exchange"),
            "symbol": meta.get("symbol"),
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
            }
        else:
            fallback = get_mcx_fallback(symbol)
            if fallback:
                print(f"[MCX-RESOLVE] {symbol}: using fallback security_id={fallback['security_id']}")
                targets[str(fallback["security_id"])] = {
                    "exchange": fallback.get("exchange"),
                    "symbol": symbol,
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


def _get_security_ids_from_watchlist() -> Dict[str, Dict[str, object]]:
    """Return desired security targets keyed by security ID."""
    security_targets = _build_default_index_targets()
    security_targets.update(_resolve_mcx_feed_targets())

    # Include option instruments for NIFTY/BANKNIFTY/SENSEX (ATM-based strike windows)
    option_symbols = {"NIFTY", "BANKNIFTY", "SENSEX"}
    subscription_map: Dict[str, Dict[str, object]] = {}
    try:
        for _, sub_info in SUBSCRIPTION_MGR.subscriptions.items():
            symbol = (sub_info.get("symbol_canonical") or sub_info.get("symbol") or "").upper()
            option_type = (sub_info.get("option_type") or "").upper()
            if symbol not in option_symbols:
                continue
            if option_type not in ("CE", "PE"):
                continue

            sec_id = sub_info.get("security_id")
            exchange = sub_info.get("exchange")
            if not sec_id or exchange is None:
                continue

            sec_id_str = str(sec_id)
            security_targets[sec_id_str] = {
                "exchange": exchange,
                "symbol": symbol,
            }
            subscription_map[sec_id_str] = {
                "symbol": symbol,
                "expiry": sub_info.get("expiry"),
                "strike": sub_info.get("strike"),
                "option_type": option_type,
            }
    except Exception:
        pass

    if not security_targets:
        # Absolute fallback to ensure feed never starves
        security_targets = {
            "13": {"exchange": 0, "symbol": "NIFTY"},
            "51": {"exchange": 0, "symbol": "SENSEX"},
        }

    _refresh_symbol_map(security_targets)
    _refresh_subscription_map(subscription_map)
    return security_targets


def on_message_callback(feed, message):
    """Callback when market data is received"""
    if not message:
        return
    
    try:
        # Extract security_id from message
        sec_id = message.get("security_id")
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
            ltp = message.get("LTP")
            if isinstance(ltp, str):
                ltp = float(ltp)
            if ltp is None or ltp == 0:
                return

            try:
                from app.services.authoritative_option_chain_service import authoritative_option_chain_service
                authoritative_option_chain_service.update_option_tick_from_websocket(
                    symbol=option_meta.get("symbol"),
                    expiry=option_meta.get("expiry"),
                    strike=option_meta.get("strike"),
                    option_type=option_meta.get("option_type"),
                    ltp=ltp,
                )
            except Exception as cache_e:
                print(f"[WARN] Failed to update option cache for {sec_id_str}: {cache_e}")
            return
        
        # Extract LTP (Last Traded Price) for underlying
        ltp = message.get("LTP")
        if isinstance(ltp, str):
            ltp = float(ltp)

        if ltp is None or ltp == 0:
            exchange_code = _subscribed_securities.get(sec_id_str)
            last_close = _get_last_close_price(sec_id_str, exchange_code)
            if last_close is not None:
                update_price(symbol, last_close)
                print(f"[PRICE] {symbol} = {last_close} (last close)")
            return

        update_price(symbol, ltp)
        print(f"[PRICE] {symbol} = {ltp}")
        
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
            
            # Subscribe to new securities only when the feed is available
            to_subscribe = desired_ids - current_ids
            if to_subscribe and _market_feed:
                for sec_id in to_subscribe:
                    meta = desired_targets.get(sec_id)
                    exchange = meta.get("exchange") if meta else None
                    if exchange is None:
                        continue
                    try:
                        _market_feed.subscribe_symbols([(exchange, sec_id, 15)])
                        _subscribed_securities[sec_id] = exchange
                        print(f"[SUBSCRIBE] Security {sec_id} subscribed")
                    except Exception as e:
                        print(f"[WARN] Failed to subscribe {sec_id}: {e}")
            
            # Unsubscribe anything that's no longer desired
            to_unsubscribe = current_ids - desired_ids
            if to_unsubscribe and _market_feed:
                for sec_id in to_unsubscribe:
                    exchange = _subscribed_securities.get(sec_id)
                    if exchange is None:
                        continue
                    try:
                        _market_feed.unsubscribe_symbols([(exchange, sec_id, 15)])
                        _subscribed_securities.pop(sec_id, None)
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
    
    with _started_lock:
        if _started:
            return
        _started = True
    
    def run_feed():
        # Ensure an event loop exists in this thread (required by dhanhq)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        sync_counter = 0
        
        while True:
            try:
                # ========== RATE LIMITING: CHECK IF WE CAN ATTEMPT CONNECTION ==========
                if not _should_attempt_connection():
                    time.sleep(5)  # Check again in 5 seconds
                    continue
                
                creds = _load_credentials()
                token = (getattr(creds, "auth_token", None) or getattr(creds, "daily_token", None)) if creds else None
                if not creds or not creds.client_id or not token:
                    print("[WARN] No Dhan credentials - waiting...")
                    _record_connection_attempt(success=False)
                    time.sleep(10)
                    continue
                
                # Get initial security targets for Tier B instruments
                initial_targets = _get_security_ids_from_watchlist()
                if not initial_targets:
                    print("[WARN] No securities to subscribe to")
                    _record_connection_attempt(success=False)
                    time.sleep(10)
                    continue
                
                # Convert security IDs to DhanHQ format
                instruments = []
                for sec_id, meta in initial_targets.items():
                    exchange = meta.get("exchange")
                    if exchange is None:
                        continue
                    instruments.append((exchange, sec_id, 15))  # 15 = Ticker mode
                
                # Create DhanContext and MarketFeed
                dhan_context = DhanContext(client_id=creds.client_id, access_token=token)
                
                _market_feed = MarketFeed(
                    dhan_context=dhan_context,
                    instruments=instruments,
                    version="v2"
                )
                
                print(f"[OK] Starting Dhan WebSocket feed (Phase 4 Dynamic)")
                print(f"[OK] Initial subscriptions: {len(instruments)} securities")
                print(f"[INFO] Rate limiting active: max {_max_consecutive_failures} failures before cooldown")
                
                # Track subscriptions
                _subscribed_securities.update({sec: exchange for exchange, sec, _ in instruments})
                _record_connection_attempt(success=True)
                
                print("[OK] Connecting to DhanHQ WebSocket...")

                # Establish and maintain WebSocket connection once
                _market_feed.run_forever()

                # Main data loop
                while True:
                    try:
                        # Phase 4: Periodically sync subscriptions with watchlist
                        sync_counter += 1
                        if sync_counter >= 100:  # Sync every ~1 second (100 × 10ms)
                            sync_subscriptions_with_watchlist()
                            sync_counter = 0

                        # Fetch and process data
                        response = _market_feed.get_data()
                        if response:
                            on_message_callback(_market_feed, response)

                        time.sleep(0.01)  # 10ms delay

                    except Exception as e:
                        print(f"[ERROR] Data fetch error: {e}")
                        print("[WARN] WebSocket connection lost, will reconnect with backoff...")
                        _record_connection_attempt(success=False)
                        time.sleep(1)
                        break
                
            except ConnectionError as e:
                print(f"[ERROR] DhanHQ connection error: {e}")
                print("[WARN] Connection rejected - likely due to rate limiting or credentials issue")
                _record_connection_attempt(success=False)
                time.sleep(5)
            except Exception as e:
                print(f"[ERROR] Dhan feed crashed: {e}")
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
