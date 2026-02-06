import asyncio
import os
import time
from collections import deque
from typing import Deque, Dict, Optional


class DhanRateLimiter:
    def __init__(self) -> None:
        self._locks: Dict[str, asyncio.Lock] = {}
        self._blocked_until: Dict[str, float] = {}
        self._windows: Dict[str, Dict[str, Deque[float]]] = {}
        self._limits: Dict[str, Dict[str, int]] = {
            "quote": {
                "per_second": int(os.getenv("DHAN_QUOTE_RPS", "1")),
                "per_minute": int(os.getenv("DHAN_QUOTE_RPM", "250")),
                "per_hour": int(os.getenv("DHAN_QUOTE_RPH", "1000")),
                "per_day": int(os.getenv("DHAN_QUOTE_RPD", "7000")),
            },
            "data": {
                "per_second": int(os.getenv("DHAN_DATA_RPS", "5")),
                "per_minute": int(os.getenv("DHAN_DATA_RPM", "250")),
                "per_hour": int(os.getenv("DHAN_DATA_RPH", "1000")),
                "per_day": int(os.getenv("DHAN_DATA_RPD", "100000")),
            },
            "expiry": {
                "per_second": int(os.getenv("DHAN_EXPIRY_RPS", "1")),
                "per_minute": int(os.getenv("DHAN_EXPIRY_RPM", "60")),
                "per_hour": int(os.getenv("DHAN_EXPIRY_RPH", "1000")),
                "per_day": int(os.getenv("DHAN_EXPIRY_RPD", "7000")),
            },
        }

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def _get_windows(self, key: str) -> Dict[str, Deque[float]]:
        if key not in self._windows:
            self._windows[key] = {
                "per_second": deque(),
                "per_minute": deque(),
                "per_hour": deque(),
                "per_day": deque(),
            }
        return self._windows[key]

    def is_blocked(self, key: str) -> bool:
        return time.time() < self._blocked_until.get(key, 0.0)

    def block(self, key: str, seconds: int) -> None:
        until = time.time() + max(0, seconds)
        self._blocked_until[key] = max(self._blocked_until.get(key, 0.0), until)

    async def wait(self, key: str) -> None:
        lock = self._get_lock(key)
        async with lock:
            await self._wait_locked(key)

    async def _wait_locked(self, key: str) -> None:
        now = time.time()
        windows = self._get_windows(key)
        limits = self._limits.get(key) or self._limits["data"]

        for window_key, seconds in {
            "per_second": 1,
            "per_minute": 60,
            "per_hour": 3600,
            "per_day": 86400,
        }.items():
            limit = limits.get(window_key)
            if limit is None:
                continue
            queue = windows[window_key]
            while queue and now - queue[0] >= seconds:
                queue.popleft()
            if len(queue) >= limit:
                sleep_for = seconds - (now - queue[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                now = time.time()
                while queue and now - queue[0] >= seconds:
                    queue.popleft()
            queue.append(now)

    def get_limits(self, key: str) -> Dict[str, int]:
        return dict(self._limits.get(key) or {})
