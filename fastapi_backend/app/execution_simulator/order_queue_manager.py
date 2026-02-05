"""FIFO order queue by price level."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Deque, Dict, List, Tuple


class OrderQueueManager:
    def __init__(self) -> None:
        self._queues: Dict[Tuple[str, str, float], Deque[int]] = defaultdict(deque)

    def enqueue(self, symbol: str, side: str, price: float, order_id: int) -> None:
        key = (symbol.upper(), side.upper(), float(price))
        self._queues[key].append(order_id)

    def dequeue(self, symbol: str, side: str, price: float) -> int | None:
        key = (symbol.upper(), side.upper(), float(price))
        if key not in self._queues or not self._queues[key]:
            return None
        return self._queues[key].popleft()

    def list_queue(self, symbol: str, side: str, price: float) -> List[int]:
        key = (symbol.upper(), side.upper(), float(price))
        return list(self._queues.get(key, []))

    def clear_order(self, order_id: int) -> None:
        for key in list(self._queues.keys()):
            queue = self._queues[key]
            if order_id in queue:
                queue.remove(order_id)
            if not queue:
                del self._queues[key]
