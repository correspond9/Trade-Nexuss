"""
Unified market cache (futures).
Entries are keyed by exchange + symbol + expiry.
"""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional, Tuple

_FUTURES_CACHE: Dict[Tuple[str, str, str], Dict] = {}
_LOCK = RLock()


def _make_key(exchange: str, symbol: str, expiry: str) -> Tuple[str, str, str]:
    return (exchange.upper(), symbol.upper(), expiry)


def set_future(exchange: str, symbol: str, expiry: str, payload: Dict) -> None:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        _FUTURES_CACHE[key] = payload


def get_future(exchange: str, symbol: str, expiry: str) -> Optional[Dict]:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        return _FUTURES_CACHE.get(key)


def list_futures(exchange: Optional[str] = None, symbol: Optional[str] = None, expiry: Optional[str] = None) -> List[Dict]:
    with _LOCK:
        results = []
        for (exch, sym, exp), payload in _FUTURES_CACHE.items():
            if exchange and exch != exchange.upper():
                continue
            if symbol and sym != symbol.upper():
                continue
            if expiry and exp != expiry:
                continue
            results.append(payload)
        return results


def update_future(exchange: str, symbol: str, expiry: str, updates: Dict) -> bool:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        entry = _FUTURES_CACHE.get(key)
        if not entry:
            return False
        entry.update({k: v for k, v in updates.items() if v is not None})
        return True
