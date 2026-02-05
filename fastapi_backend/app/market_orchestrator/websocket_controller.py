"""WebSocket connection controller and token distribution."""
from __future__ import annotations

from threading import RLock
from typing import Dict, Iterable, List, Optional, Tuple


PRIORITY_ORDER = [
    "INDEX_OPTIONS",
    "STOCK_OPTIONS",
    "MCX_OPTIONS",
    "FUTURES",
    "EQUITIES",
]


class WebSocketController:
    def __init__(self, max_connections: int = 5, max_per_connection: int = 5000) -> None:
        self.max_connections = max_connections
        self.max_per_connection = max_per_connection
        self.websocket_pool: Dict[int, set] = {i: set() for i in range(1, max_connections + 1)}
        self.token_to_ws: Dict[str, int] = {}
        self.ws_handles: Dict[int, object] = {}
        self.ws_active: Dict[int, bool] = {i: False for i in range(1, max_connections + 1)}
        self._lock = RLock()

    def register_handle(self, ws_id: int, handle: object) -> None:
        with self._lock:
            self.ws_handles[ws_id] = handle
            self.ws_active[ws_id] = True

    def mark_inactive(self, ws_id: int) -> None:
        with self._lock:
            self.ws_active[ws_id] = False
            self.ws_handles.pop(ws_id, None)

    def _find_target_ws(self) -> Optional[int]:
        ws_id = min(self.websocket_pool, key=lambda k: len(self.websocket_pool[k]))
        if len(self.websocket_pool[ws_id]) >= self.max_per_connection:
            return None
        return ws_id

    def add_token(self, token: str, ws_id: Optional[int] = None) -> Tuple[bool, Optional[int], str]:
        with self._lock:
            if token in self.token_to_ws:
                return True, self.token_to_ws[token], "already_assigned"

            if ws_id is None:
                ws_id = self._find_target_ws()
            if ws_id is None:
                return False, None, "no_capacity"

            if len(self.websocket_pool[ws_id]) >= self.max_per_connection:
                return False, None, "ws_at_capacity"

            self.websocket_pool[ws_id].add(token)
            self.token_to_ws[token] = ws_id
            return True, ws_id, "assigned"

    def add_tokens_by_priority(self, tokens_by_priority: Dict[str, Iterable[str]]) -> Dict[str, int]:
        results = {"assigned": 0, "skipped": 0, "failed": 0}
        for priority in PRIORITY_ORDER:
            for token in tokens_by_priority.get(priority, []):
                ok, _ws, reason = self.add_token(str(token))
                if ok:
                    results["assigned"] += 1
                elif reason == "already_assigned":
                    results["skipped"] += 1
                else:
                    results["failed"] += 1
        return results

    def remove_token(self, token: str) -> bool:
        with self._lock:
            ws_id = self.token_to_ws.get(token)
            if not ws_id:
                return False
            self.websocket_pool[ws_id].discard(token)
            del self.token_to_ws[token]
            return True

    def get_ws_for_token(self, token: str) -> Optional[int]:
        with self._lock:
            return self.token_to_ws.get(token)

    def get_tokens_for_ws(self, ws_id: int) -> List[str]:
        with self._lock:
            return list(self.websocket_pool.get(ws_id, set()))

    def get_status(self) -> Dict[str, object]:
        with self._lock:
            total_subscriptions = sum(len(tokens) for tokens in self.websocket_pool.values())
            tokens_per_ws = {f"ws{ws_id}": len(tokens) for ws_id, tokens in self.websocket_pool.items()}
            active_connections = sum(1 for ws_id in self.ws_active if self.ws_active[ws_id])
            return {
                "total_ws_connections": self.max_connections,
                "active_ws_connections": active_connections,
                "total_subscriptions": total_subscriptions,
                "tokens_per_ws": tokens_per_ws,
            }
