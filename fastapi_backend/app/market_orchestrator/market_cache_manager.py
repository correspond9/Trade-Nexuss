"""Unified market cache manager for options, futures, equities, and index."""
from __future__ import annotations

from datetime import datetime
from threading import RLock
from typing import Dict, Optional

try:
    from app.market_cache.options import set_option_chain, update_option_leg, list_option_chains
    from app.market_cache.futures import set_future, update_future, list_futures
    from app.market_cache.equities import set_equity, list_equities
except Exception:
    set_option_chain = None
    update_option_leg = None
    list_option_chains = None
    set_future = None
    update_future = None
    list_futures = None
    set_equity = None
    list_equities = None


class MarketCacheManager:
    def __init__(self) -> None:
        self._index_cache: Dict[str, Dict] = {}
        self._lock = RLock()

    def _now(self) -> str:
        return datetime.utcnow().isoformat()

    def update_option(self, exchange: str, symbol: str, expiry: str, strike: float, option_type: str, fields: Dict) -> bool:
        if update_option_leg is None:
            return False
        payload = dict(fields)
        payload["timestamp"] = payload.get("timestamp") or self._now()
        return update_option_leg(exchange, symbol, expiry, strike, option_type, payload)

    def set_option_chain(self, exchange: str, symbol: str, expiry: str, payload: Dict) -> None:
        if set_option_chain is None:
            return
        payload = dict(payload)
        payload.setdefault("timestamp", self._now())
        set_option_chain(exchange, symbol, expiry, payload)

    def update_future(self, exchange: str, symbol: str, expiry: str, fields: Dict) -> bool:
        if update_future is None:
            return False
        payload = dict(fields)
        payload["timestamp"] = payload.get("timestamp") or self._now()
        return update_future(exchange, symbol, expiry, payload)

    def set_future(self, exchange: str, symbol: str, expiry: str, payload: Dict) -> None:
        if set_future is None:
            return
        payload = dict(payload)
        payload.setdefault("timestamp", self._now())
        set_future(exchange, symbol, expiry, payload)

    def set_equity(self, exchange: str, symbol: str, payload: Dict) -> None:
        if set_equity is None:
            return
        payload = dict(payload)
        payload.setdefault("timestamp", self._now())
        set_equity(exchange, symbol, payload)

    def set_index(self, symbol: str, payload: Dict) -> None:
        with self._lock:
            data = dict(payload)
            data.setdefault("timestamp", self._now())
            self._index_cache[symbol.upper()] = data

    def update_from_tick(self, tick: Dict) -> None:
        exchange = str(tick.get("exchange") or "").upper()
        symbol = str(tick.get("symbol") or "").upper()
        expiry = tick.get("expiry")
        option_type = tick.get("option_type")
        strike = tick.get("strike")
        is_index = bool(tick.get("is_index"))
        ltp = tick.get("ltp")
        depth = tick.get("depth")

        fields = {
            "exchange": exchange,
            "symbol": symbol,
            "expiry": expiry,
            "ltp": ltp,
            "bid": tick.get("bid"),
            "ask": tick.get("ask"),
            "volume": tick.get("volume"),
            "oi": tick.get("oi"),
            "timestamp": tick.get("timestamp") or self._now(),
        }

        if option_type and strike is not None and expiry:
            self.update_option(exchange, symbol, str(expiry), float(strike), str(option_type), fields)
        elif expiry:
            self.update_future(exchange, symbol, str(expiry), fields)
        elif is_index:
            self.set_index(symbol, fields)
            try:
                if ltp is not None:
                    from app.market.live_prices import update_price
                    update_price(symbol, float(ltp))
            except Exception:
                pass
        else:
            self.set_equity(exchange, symbol, fields)
            try:
                if ltp is not None:
                    from app.market.live_prices import update_price, get_dashboard_symbols
                    if symbol in get_dashboard_symbols():
                        update_price(symbol, float(ltp))
            except Exception:
                pass

        if depth is not None:
            try:
                from app.market.market_state import state
                state.setdefault("depth", {})[symbol] = depth
            except Exception:
                pass

    def cache_status(self) -> Dict[str, object]:
        options_count = len(list_option_chains()) if list_option_chains else 0
        futures_count = len(list_futures()) if list_futures else 0
        equities_count = len(list_equities()) if list_equities else 0
        with self._lock:
            index_count = len(self._index_cache)
        return {
            "options": options_count,
            "futures": futures_count,
            "equities": equities_count,
            "index": index_count,
        }
