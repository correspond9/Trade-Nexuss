"""Central subscription registry for market data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Dict, List, Optional


@dataclass
class SubscriptionEntry:
    token: str
    exchange: str
    segment: str
    symbol: str
    expiry: Optional[str]
    websocket_id: Optional[int]
    active: bool = True
    meta: Dict[str, object] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class SubscriptionRegistry:
    def __init__(self) -> None:
        self._items: Dict[str, SubscriptionEntry] = {}
        self._lock = RLock()

    def add(self, entry: SubscriptionEntry) -> bool:
        with self._lock:
            if entry.token in self._items:
                return False
            self._items[entry.token] = entry
            return True

    def upsert(self, entry: SubscriptionEntry) -> None:
        with self._lock:
            self._items[entry.token] = entry

    def get(self, token: str) -> Optional[SubscriptionEntry]:
        with self._lock:
            return self._items.get(token)

    def exists(self, token: str) -> bool:
        with self._lock:
            return token in self._items

    def remove(self, token: str) -> bool:
        with self._lock:
            if token not in self._items:
                return False
            del self._items[token]
            return True

    def set_active(self, token: str, active: bool) -> bool:
        with self._lock:
            entry = self._items.get(token)
            if not entry:
                return False
            entry.active = active
            return True

    def update_ws(self, token: str, websocket_id: Optional[int]) -> bool:
        with self._lock:
            entry = self._items.get(token)
            if not entry:
                return False
            entry.websocket_id = websocket_id
            return True

    def list_all(self) -> List[SubscriptionEntry]:
        with self._lock:
            return list(self._items.values())

    def list_by_ws(self, websocket_id: int) -> List[SubscriptionEntry]:
        with self._lock:
            return [entry for entry in self._items.values() if entry.websocket_id == websocket_id]

    def list_by_exchange(self, exchange: str) -> List[SubscriptionEntry]:
        exch = exchange.upper()
        with self._lock:
            return [entry for entry in self._items.values() if entry.exchange.upper() == exch]

    def count(self) -> int:
        with self._lock:
            return len(self._items)
