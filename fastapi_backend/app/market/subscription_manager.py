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
from app.market.instrument_master.registry import REGISTRY
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
    "NFO": 1,
    "BSE": 2,
    "MCX": 5,
}


def _normalize_expiry(expiry: Optional[str]) -> Optional[date]:
    if not expiry:
        return None
    text = expiry.strip().upper()
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
        return {
            "security_id": str(security_id).strip(),
            "exchange": exchange,
            "segment": row.get("SEGMENT"),
            "symbol": canonical,
        }

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
            if token in self.subscriptions:
                return (True, f"Already subscribed: {token}", self.subscriptions[token]["ws_id"])
            
            # Check rate limit
            current_total = sum(self.ws_usage.values())
            if current_total >= 25000:
                # Rate limit hit - should not happen for Tier B, evict LRU Tier A
                if tier == "TIER_A":
                    evicted = self._evict_lru_tier_a()
                    if evicted:
                        current_total -= 1
                    else:
                        return (False, "Rate limit: No Tier A chains to evict", None)
                else:
                    return (False, "Rate limit: 25,000 instruments at capacity", None)
            
            # Find least-loaded WS
            ws_id = min(self.ws_usage, key=self.ws_usage.get)
            self.ws_usage[ws_id] += 1
            
            metadata = _resolve_security_metadata(symbol, expiry, strike, option_type)
            canonical = canonical_symbol(symbol)

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
            
            return (True, f"Subscribed to {tier} on WS-{ws_id}", ws_id)
    
    def unsubscribe(self, token: str, reason: str = "User") -> Tuple[bool, str]:
        """Unsubscribe an instrument"""
        with self.lock:
            if token not in self.subscriptions:
                return (False, f"Not subscribed: {token}")
            
            sub = self.subscriptions[token]
            ws_id = sub["ws_id"]
            self.ws_usage[ws_id] -= 1
            
            del self.subscriptions[token]
            
            # Remove from LRU if present
            self.tier_a_lru = [(t, ts) for t, ts in self.tier_a_lru if t != token]
            
            # Log to DB
            self._log_subscription("UNSUBSCRIBE", token, reason)
            
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
        with self.lock:
            return {
                "total_subscriptions": sum(self.ws_usage.values()),
                "ws_usage": dict(self.ws_usage),
                "utilization_percent": (sum(self.ws_usage.values()) / 25000) * 100,
                "tier_a_count": len([s for s in self.subscriptions.values() if s["tier"] == "TIER_A"]),
                "tier_b_count": len([s for s in self.subscriptions.values() if s["tier"] == "TIER_B"])
            }
    
    def unsubscribe_all_tier_a(self) -> int:
        """Unsubscribe all Tier A subscriptions (e.g., at EOD)"""
        with self.lock:
            tier_a_tokens = [
                token for token, data in self.subscriptions.items()
                if data.get("tier") == "TIER_A"
            ]
            
            for token in tier_a_tokens:
                self.unsubscribe(token, reason="EOD_CLEANUP")
            
            return len(tier_a_tokens)
    
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
        # Disabled temporarily due to database locking issues
        pass
    
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


# Global subscription manager
SUBSCRIPTION_MGR = SubscriptionManager()

def get_subscription_manager() -> SubscriptionManager:
    """Get global subscription manager"""
    return SUBSCRIPTION_MGR
