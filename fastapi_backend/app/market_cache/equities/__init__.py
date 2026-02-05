"""Unified market cache (equities). Placeholder for equity engine integration."""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional, Tuple

_EQUITY_CACHE: Dict[Tuple[str, str], Dict] = {}
_LOCK = RLock()


def _make_key(exchange: str, symbol: str) -> Tuple[str, str]:
    return (exchange.upper(), symbol.upper())


def set_equity(exchange: str, symbol: str, payload: Dict) -> None:
    key = _make_key(exchange, symbol)
    with _LOCK:
        _EQUITY_CACHE[key] = payload


def get_equity(exchange: str, symbol: str) -> Optional[Dict]:
    key = _make_key(exchange, symbol)
    with _LOCK:
        return _EQUITY_CACHE.get(key)


def list_equities(exchange: Optional[str] = None) -> List[Dict]:
    with _LOCK:
        results = []
        for (exch, _sym), payload in _EQUITY_CACHE.items():
            if exchange and exch != exchange.upper():
                continue
            results.append(payload)
        return results
