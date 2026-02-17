"""
Subscription State Manager for Tier A (on-demand) and Tier B (always-on).
Tracks all active subscriptions and their lifecycle.
"""

import threading
from datetime import datetime, date
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
from app.storage.db import SessionLocal
from app.storage.models import Subscription, SubscriptionLog
from app.storage.migrations import init_db
from app.market.instrument_master.registry import REGISTRY
from app.market.instrument_master.tier_b_etf_symbols import get_tier_b_etf_symbols
from app.market.instrument_master.tier_a_equity_symbols import get_tier_a_equity_symbols
from app.market_orchestrator import get_orchestrator
from app.market.security_ids import (
    canonical_symbol,
    get_default_equity_security,
    get_default_index_security,
    get_mcx_fallback,
)

_EXPIRY_FORMATS = ("%d%b%Y", "%d%B%Y", "%d%b%y", "%Y-%m-%d")
_EXCHANGE_CODE_MAP = {
    "IDX": 0,
    "NSE": 1,
    "NFO": 2,
    "NSE_FNO": 2,
    "BSE": 4,
    "BSE_FNO": 8,
    "MCX": 5,
}
_EXCHANGE_CODE_TO_NAME = {
    0: "NSE",
    1: "NSE",
    2: "NSE",
    4: "BSE",
    8: "BSE",
    5: "MCX",
}


def _normalize_expiry(expiry: Optional[object]) -> Optional[date]:
    if not expiry:
        return None
    if isinstance(expiry, datetime):
        return expiry.date()
    if isinstance(expiry, date):
        return expiry
    text = str(expiry).strip().upper()
    for fmt in _EXPIRY_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _safe_float(value: Optional[float]) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _determine_exchange(row_exchange: Optional[str], symbol: str) -> Optional[int]:
    if row_exchange:
        code = _EXCHANGE_CODE_MAP.get(row_exchange.strip().upper())
        if code is not None:
            return code
    # Fallback for well-known canonical indices
    default_meta = get_default_index_security(symbol)
    if default_meta:
        return default_meta.get("exchange")
    equity_meta = get_default_equity_security(symbol)
    if equity_meta:
        return equity_meta.get("exchange")
    return None


def _exchange_name_from_meta(exchange_code: Optional[int], segment: Optional[str]) -> str:
    if segment:
        segment_upper = segment.upper()
        if "MCX" in segment_upper:
            return "MCX"
        if "BSE" in segment_upper:
            return "BSE"
        if "NSE" in segment_upper or "NFO" in segment_upper:
            return "NSE"
    if exchange_code is None:
        return "UNKNOWN"
    return _EXCHANGE_CODE_TO_NAME.get(exchange_code, "UNKNOWN")


def _resolve_security_metadata(
    symbol: Optional[str],
    expiry: Optional[str],
    strike: Optional[float],
    option_type: Optional[str]
) -> Dict[str, object]:
    if not symbol:
        return {}
    symbol_upper = symbol.upper()
    canonical = canonical_symbol(symbol_upper) or symbol_upper
    normalized_expiry = _normalize_expiry(expiry)
    strike_val = _safe_float(strike)
    opt_type = option_type.upper() if option_type else None

    records = REGISTRY.get_by_symbol(symbol_upper) or REGISTRY.get_by_symbol(canonical)
    for row in records:
        row_expiry = _normalize_expiry(row.get("SM_EXPIRY_DATE") or row.get("EXPIRY") or row.get("EXPIRY_DATE"))
        if normalized_expiry and row_expiry and row_expiry != normalized_expiry:
            continue
        if normalized_expiry and not row_expiry:
            continue

        row_option = (row.get("OPTION_TYPE") or "").upper()
        if opt_type:
            if row_option != opt_type:
                continue
        else:
            if row_option not in ("", "XX"):
                continue

        row_strike = _safe_float(row.get("STRIKE_PRICE"))
        if strike_val is not None:
            if row_strike is None or abs(row_strike - strike_val) > 1e-6:
                continue

        security_id = row.get("SECURITY_ID") or row.get("SecurityId")
        if not security_id:
            continue

        exchange = _determine_exchange(row.get("EXCH_ID"), canonical)
        if opt_type in ("CE", "PE"):
            row_exchange = (row.get("EXCH_ID") or "").strip().upper()
            if row_exchange == "BSE":
                exchange = _EXCHANGE_CODE_MAP.get("BSE_FNO", 8)
            elif row_exchange == "NSE":
                exchange = _EXCHANGE_CODE_MAP.get("NSE_FNO", 2)
        return {
            "security_id": str(security_id).strip(),
            "exchange": exchange,
            "segment": row.get("SEGMENT"),
            "symbol": canonical,
        }

    # Equity fallback: by_symbol index can miss some NSE cash rows (e.g., TCS).
    # For non-option subscriptions, explicitly resolve from NSE equity registry.
    if not opt_type:
        try:
            for row in REGISTRY.get_equity_stocks_nse(limit=12000):
                row_symbol = (row.get("UNDERLYING_SYMBOL") or row.get("SYMBOL") or row.get("SYMBOL_NAME") or "").strip().upper()
                if row_symbol != canonical:
                    continue

                inst_type = (row.get("INSTRUMENT_TYPE") or "").strip().upper()
                if inst_type not in {"ES", "ETF"}:
                    continue

                security_id = row.get("SECURITY_ID") or row.get("SecurityId")
                if not security_id:
                    continue

                exchange = _determine_exchange(row.get("EXCH_ID"), canonical)
                return {
                    "security_id": str(security_id).strip(),
                    "exchange": exchange,
                    "segment": row.get("SEGMENT") or "NSE_EQ",
                    "symbol": canonical,
                }
        except Exception:
            pass

    # Fallback: try DhanHQ security ID mapper for options
    if opt_type and normalized_expiry and strike_val is not None:
        try:
            from app.services.dhan_security_id_mapper import dhan_security_mapper

            expiry_iso = normalized_expiry.isoformat()
            token_key = f"{opt_type}_{canonical}_{strike_val}_{expiry_iso}"
            security_id = dhan_security_mapper.get_security_id(token_key)
            option_data = dhan_security_mapper.get_option_data(token_key) if security_id else None

            if security_id:
                segment = option_data.get("segment") if option_data else None
                segment_upper = (segment or "").upper()
                exchange = _EXCHANGE_CODE_MAP.get("NFO")
                if "BSE" in segment_upper and "FNO" in segment_upper:
                    exchange = _EXCHANGE_CODE_MAP.get("BSE_FNO", 8)

                return {
                    "security_id": str(security_id),
                    "exchange": exchange,
                    "segment": segment,
                    "symbol": canonical,
                }
        except Exception:
            pass

    # If option metadata cannot be resolved, do NOT fall back to index IDs
    if opt_type and normalized_expiry and strike_val is not None:
        return {}

    # Fallback to predefined maps (e.g., MCX near-month placeholders or indices)
    default_equity = get_default_equity_security(symbol_upper)
    if default_equity:
        return default_equity
    default_meta = get_default_index_security(symbol_upper)
    if default_meta:
        return default_meta
    mcx_meta = get_mcx_fallback(symbol_upper)
    if mcx_meta:
        return mcx_meta
    return {}

class SubscriptionManager:
    """
    Central subscription state tracker.
    
    Tier A (On-Demand):
    - User-driven via watchlist
    - Unsubscribed at EOD or when rate limit triggered (LRU eviction)
    
    Tier B (Always-On):
    - Pre-loaded at startup
    - Index options, MCX futures/options
    - Persistent through trading day
    """
    
    def __init__(self):
        self.subscriptions = {}  # token -> {tier, symbol, expiry, strike, option_type, subscribed_at, ws_id, active}
        self.tier_a_lru = []  # List of (token, subscribed_at) for LRU eviction
        self.ws_usage = {i: 0 for i in range(1, 6)}  # ws_1 to ws_5 instrument counts
        self.lock = threading.RLock()
        self.db = SessionLocal()
        self._db_loaded = False
        
        # ✨ Database loading deferred to first use (after startup hook completes)
        # Don't load at import time to avoid connection issues
    
    def subscribe(
        self,
        token: str,
        symbol: str,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
        tier: str = "TIER_A"
    ) -> Tuple[bool, str]:
        """
        Subscribe an instrument.
        
        Args:
            token: unique instrument id (e.g., "RELIANCE_26FEB_2640CE")
            symbol: underlying symbol
            expiry: expiry date (optional for equity)
            strike: strike price (optional for equity/futures)
            option_type: "CE"/"PE" (optional for equity)
            tier: "TIER_A" or "TIER_B"
        
        Returns:
            (success: bool, message: str, ws_id: int)
        """
        with self.lock:
            try:
                from app.market.security_ids import mcx_watch_symbols
                if not REGISTRY.loaded:
                    REGISTRY.load()
                allowed_indices = {"NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"}
                allowed_equities = set()
                try:
                    allowed_equities = get_tier_a_equity_symbols()
                except Exception:
                    allowed_equities = set()
                allowed_symbols = set(REGISTRY.f_o_stocks) | allowed_indices | set(mcx_watch_symbols().keys()) | allowed_equities
                if canonical_symbol(symbol) not in allowed_symbols:
                    return (False, "NOT_ALLOWED", None)
            except Exception:
                pass
            if token in self.subscriptions:
                return (True, f"Already subscribed: {token}", self.subscriptions[token]["ws_id"])

            metadata = _resolve_security_metadata(symbol, expiry, strike, option_type)
            canonical = canonical_symbol(symbol)
            exchange_name = _exchange_name_from_meta(metadata.get("exchange"), metadata.get("segment"))
            segment_name = (metadata.get("segment") or exchange_name).upper()

            orchestrator = get_orchestrator()
            ok, reason, ws_id = orchestrator.subscribe(
                token=str(token),
                exchange=exchange_name,
                segment=segment_name,
                symbol=canonical or symbol,
                expiry=expiry,
                meta=metadata,
            )

            if not ok and tier == "TIER_A":
                evicted = self._evict_lru_tier_a()
                if evicted:
                    ok, reason, ws_id = orchestrator.subscribe(
                        token=str(token),
                        exchange=exchange_name,
                        segment=segment_name,
                        symbol=canonical or symbol,
                        expiry=expiry,
                        meta=metadata,
                    )

            if not ok or ws_id is None:
                return (False, f"Rate limit: {reason}", None)

            # Reflect subscription in WS manager for admin visibility
            try:
                from app.market.ws_manager import get_ws_manager
                ws_mgr = get_ws_manager()
                ws_mgr.add_instrument(str(token), ws_id)
            except Exception:
                pass

            self.ws_usage[ws_id] = self.ws_usage.get(ws_id, 0) + 1

            # Store subscription
            self.subscriptions[token] = {
                "symbol": symbol,
                "symbol_canonical": canonical or symbol,
                "expiry": expiry,
                "strike": strike,
                "option_type": option_type,
                "tier": tier,
                "subscribed_at": datetime.utcnow(),
                "ws_id": ws_id,
                "active": True,
                "exchange": metadata.get("exchange"),
                "security_id": metadata.get("security_id"),
                "segment": metadata.get("segment"),
            }
            
            # Track LRU for Tier A
            if tier == "TIER_A":
                self.tier_a_lru.append((token, datetime.utcnow()))
            
            # Log to DB
            self._log_subscription("SUBSCRIBE", token, f"Added to {tier}")

            # Push dynamic watchlist changes to live feed immediately (don't wait periodic sync).
            try:
                from app.dhan.live_feed import sync_subscriptions_with_watchlist
                sync_subscriptions_with_watchlist()
            except Exception:
                pass
            
            return (True, f"Subscribed to {tier} on WS-{ws_id}", ws_id)
    
    def unsubscribe(self, token: str, reason: str = "User") -> Tuple[bool, str]:
        """Unsubscribe an instrument"""
        with self.lock:
            if token not in self.subscriptions:
                return (False, f"Not subscribed: {token}")
            
            sub = self.subscriptions[token]
            ws_id = sub["ws_id"]
            orchestrator = get_orchestrator()
            orchestrator.unsubscribe(str(token))
            if ws_id in self.ws_usage:
                self.ws_usage[ws_id] = max(self.ws_usage[ws_id] - 1, 0)
            
            # Reflect removal in WS manager
            try:
                from app.market.ws_manager import get_ws_manager
                ws_mgr = get_ws_manager()
                ws_mgr.remove_instrument(str(token))
            except Exception:
                pass

            del self.subscriptions[token]
            
            # Remove from LRU if present
            self.tier_a_lru = [(t, ts) for t, ts in self.tier_a_lru if t != token]
            
            # Log to DB
            self._log_subscription("UNSUBSCRIBE", token, reason)

            # Push dynamic watchlist changes to live feed immediately.
            try:
                from app.dhan.live_feed import sync_subscriptions_with_watchlist
                sync_subscriptions_with_watchlist()
            except Exception:
                pass
            
            return (True, f"Unsubscribed: {token}")
    
    def get_subscription(self, token: str) -> Optional[Dict]:
        """Get subscription details"""
        with self.lock:
            return self.subscriptions.get(token)
    
    def list_active_subscriptions(self, tier: Optional[str] = None) -> List[Dict]:
        """List all active subscriptions, optionally filtered by tier"""
        with self.lock:
            subs = []
            for token, data in self.subscriptions.items():
                if tier is None or data.get("tier") == tier:
                    subs.append({
                        "token": token,
                        **data
                    })
            return subs
    
    def get_active_count(self) -> int:
        """Total active subscriptions"""
        with self.lock:
            return len(self.subscriptions)
    
    def get_ws_stats(self) -> Dict:
        """Get WebSocket load stats"""
        orchestrator = get_orchestrator()
        status = orchestrator.get_status()
        ws_usage = {}
        for key, value in status.get("tokens_per_ws", {}).items():
            key_str = str(key)
            if not key_str.startswith("ws"):
                continue
            ws_id = int(key_str.replace("ws", ""))
            ws_usage[ws_id] = int(value)

        with self.lock:
            total = sum(ws_usage.values()) if ws_usage else sum(self.ws_usage.values())
            return {
                "total_subscriptions": total,
                "ws_usage": ws_usage or dict(self.ws_usage),
                "utilization_percent": (total / 25000) * 100 if total else 0.0,
                "tier_a_count": len([s for s in self.subscriptions.values() if s["tier"] == "TIER_A"]),
                "tier_b_count": len([s for s in self.subscriptions.values() if s["tier"] == "TIER_B"])
            }
    
    def unsubscribe_all_tier_a(self) -> int:
        """Unsubscribe all Tier A subscriptions (e.g., at EOD)"""
        # Build protection set from open mock positions
        protected_tokens = set()
        protected_normalized = set()
        try:
            from app.storage.db import SessionLocal
            from app.storage.models import MockPosition
            from app.rms.span_margin_calculator import _parse_symbol as parse_fno_symbol
            from app.rms.mcx_margin_calculator import _parse_symbol as parse_mcx_symbol
            db = SessionLocal()
            positions = (
                db.query(MockPosition)
                .filter(MockPosition.quantity != 0)
                .filter(MockPosition.status == "OPEN")
                .all()
            )
            for pos in positions:
                sym = (pos.symbol or "").strip()
                if sym:
                    protected_tokens.add(sym)
                meta = parse_fno_symbol(sym)
                if not meta or not meta.get("underlying"):
                    meta = parse_mcx_symbol(sym)
                underlying = (meta.get("underlying") or "").upper()
                expiry = meta.get("expiry")
                strike = meta.get("strike")
                opt = (meta.get("option_type") or "").upper() or None
                protected_normalized.add((underlying, expiry, strike, opt))
        except Exception:
            pass
        
        # Unsubscribe Tier A except protected
        unsubscribed = 0
        with self.lock:
            tier_a_items = [
                (token, data) for token, data in self.subscriptions.items()
                if data.get("tier") == "TIER_A"
            ]
            for token, data in tier_a_items:
                if token in protected_tokens:
                    continue
                underlying = (data.get("symbol_canonical") or data.get("symbol") or "").upper()
                expiry = data.get("expiry")
                strike = data.get("strike")
                try:
                    strike = float(strike) if strike is not None else None
                except Exception:
                    strike = None
                opt = (data.get("option_type") or "").upper() or None
                if (underlying, expiry, strike, opt) in protected_normalized:
                    continue
                ok, _msg = self.unsubscribe(token, reason="EOD_CLEANUP")
                if ok:
                    unsubscribed += 1
        return unsubscribed
    
    def _evict_lru_tier_a(self) -> bool:
        """
        Evict least-recently-added Tier A subscription.
        Returns True if evicted, False if no Tier A to evict.
        """
        if not self.tier_a_lru:
            return False
        
        token, _ = self.tier_a_lru.pop(0)
        self.unsubscribe(token, reason="RATE_LIMIT_EVICTION")
        return True
    
    def _log_subscription(self, action: str, token: str, reason: str):
        """Log subscription event to database"""
        session = None
        try:
            from app.storage.db import SessionLocal
            from app.storage.models import Subscription, SubscriptionLog

            session = SessionLocal()
            log = SubscriptionLog(action=action, instrument_token=token, reason=reason)
            session.add(log)

            if action == "SUBSCRIBE":
                sub_state = self.subscriptions.get(token)
                if sub_state:
                    row = session.query(Subscription).filter(Subscription.instrument_token == token).first()
                    if not row:
                        row = Subscription(instrument_token=token)
                        session.add(row)

                    row.symbol = sub_state.get("symbol")
                    row.expiry_date = sub_state.get("expiry")
                    row.strike_price = sub_state.get("strike")
                    row.option_type = sub_state.get("option_type")
                    row.tier = sub_state.get("tier") or "TIER_A"
                    row.subscribed_at = sub_state.get("subscribed_at") or datetime.utcnow()
                    row.ws_connection_id = sub_state.get("ws_id")
                    row.active = True
            else:
                row = session.query(Subscription).filter(Subscription.instrument_token == token).first()
                if row:
                    row.active = False

            session.commit()
        except Exception as e:
            try:
                if session:
                    session.rollback()
            except Exception:
                pass
            print(f"[WARN] Failed to persist subscription log/state for {token}: {e}")
        finally:
            try:
                if session:
                    session.close()
            except Exception:
                pass
    
    def _load_from_database(self):
        """Load existing subscriptions from database (called explicitly by startup hook)"""
        if self._db_loaded:
            return
        
        try:
            from sqlalchemy import inspect
            from app.storage.db import engine, Base
            from app.storage.models import Subscription
            
            # Ensure tables exist
            if not inspect(engine).has_table("subscriptions"):
                print("[SUBSCRIPTION_MGR] subscriptions table not found, creating schema...")
                Base.metadata.create_all(bind=engine)
                print("[SUBSCRIPTION_MGR] Schema created")
            
            orchestrator = get_orchestrator()
            active_subs = self.db.query(Subscription).filter(Subscription.active == True).all()
            
            loaded_count = 0
            for sub in active_subs:
                token = sub.instrument_token
                try:
                    from app.market.security_ids import mcx_watch_symbols
                    allowed_indices = {"NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"}
                    equities = set()
                    try:
                        for r in REGISTRY.get_equity_stocks_nse(limit=2000):
                            sym = (r.get("UNDERLYING_SYMBOL") or r.get("SYMBOL") or "").strip().upper()
                            if sym:
                                equities.add(sym)
                    except Exception:
                        pass
                    allowed_symbols = set(REGISTRY.f_o_stocks) | allowed_indices | set(mcx_watch_symbols().keys()) | equities
                    if canonical_symbol(sub.symbol) not in allowed_symbols:
                        continue
                except Exception:
                    pass
                metadata = _resolve_security_metadata(
                    symbol=sub.symbol,
                    expiry=sub.expiry_date,
                    strike=sub.strike_price,
                    option_type=sub.option_type,
                )
                exchange_name = _exchange_name_from_meta(metadata.get("exchange"), metadata.get("segment"))
                segment_name = (metadata.get("segment") or exchange_name).upper()
                ok, _reason, ws_id = orchestrator.subscribe(
                    token=str(token),
                    exchange=exchange_name,
                    segment=segment_name,
                    symbol=sub.symbol,
                    expiry=sub.expiry_date,
                    meta=metadata,
                )
                if not ok or ws_id is None:
                    ws_id = sub.ws_connection_id or 1

                self.subscriptions[token] = {
                    "symbol": sub.symbol,
                    "symbol_canonical": sub.symbol,  # Could be normalized
                    "expiry": sub.expiry_date,
                    "strike": sub.strike_price,
                    "option_type": sub.option_type,
                    "tier": sub.tier,
                    "subscribed_at": sub.subscribed_at,
                    "ws_id": ws_id,
                    "active": True,
                    "exchange": metadata.get("exchange"),
                    "security_id": metadata.get("security_id"),
                    "segment": metadata.get("segment"),
                }
                
                # Update WS usage
                self.ws_usage[ws_id] = self.ws_usage.get(ws_id, 0) + 1
                
                loaded_count += 1
            
            if loaded_count > 0:
                print(f"[DB] Loaded {loaded_count} subscriptions from database")
            else:
                print("[DB] No active subscriptions found in database")
            
            self._db_loaded = True
                
        except Exception as e:
            print(f"[ERROR] Failed to load subscriptions from database: {e}")
            self._db_loaded = True  # Mark as attempted even if failed
    
    def sync_to_db(self):
        """Sync all current subscriptions to database"""
        try:
            # Clear old active subscriptions
            self.db.query(Subscription).filter(Subscription.active == True).delete()
            
            # Add current
            with self.lock:
                for token, data in self.subscriptions.items():
                    sub = Subscription(
                        instrument_token=token,
                        symbol=data["symbol"],
                        expiry_date=data["expiry"],
                        strike_price=data["strike"],
                        option_type=data["option_type"],
                        tier=data["tier"],
                        subscribed_at=data["subscribed_at"],
                        ws_connection_id=data["ws_id"],
                        active=True
                    )
                    self.db.add(sub)
            
            self.db.commit()
        except Exception as e:
            print(f"[WARN] Failed to sync subscriptions to DB: {e}")


# Global subscription manager (init_db() called in startup hook)
SUBSCRIPTION_MGR = SubscriptionManager()

def get_subscription_manager() -> SubscriptionManager:
    """Get global subscription manager"""
    return SUBSCRIPTION_MGR
