"""
Unified market cache (options).
Entries are keyed by exchange + symbol + expiry.
"""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional, Tuple

_OPTION_CACHE: Dict[Tuple[str, str, str], Dict] = {}
_LOCK = RLock()


def _make_key(exchange: str, symbol: str, expiry: str) -> Tuple[str, str, str]:
    return (exchange.upper(), symbol.upper(), expiry)


def set_option_chain(exchange: str, symbol: str, expiry: str, payload: Dict) -> None:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        _OPTION_CACHE[key] = payload


def get_option_chain(exchange: str, symbol: str, expiry: str) -> Optional[Dict]:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        return _OPTION_CACHE.get(key)


def list_option_chains(exchange: Optional[str] = None, symbol: Optional[str] = None) -> List[Dict]:
    with _LOCK:
        results = []
        for (exch, sym, _exp), payload in _OPTION_CACHE.items():
            if exchange and exch != exchange.upper():
                continue
            if symbol and sym != symbol.upper():
                continue
            results.append(payload)
        return results


def update_option_leg(exchange: str, symbol: str, expiry: str, strike: float, option_type: str, updates: Dict) -> bool:
    key = _make_key(exchange, symbol, expiry)
    with _LOCK:
        chain = _OPTION_CACHE.get(key)
        if not chain:
            return False
        strikes = chain.get("strikes", {})
        strike_key = str(float(strike)) if strike is not None else None
        if strike_key not in strikes:
            return False
        leg = strikes[strike_key].get(option_type)
        if not isinstance(leg, dict):
            return False
        leg.update({k: v for k, v in updates.items() if v is not None})
        return True
