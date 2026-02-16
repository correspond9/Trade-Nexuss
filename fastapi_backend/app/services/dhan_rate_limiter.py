import asyncio
import logging
import os
import time
from collections import deque
from typing import Deque, Dict, Optional

logger = logging.getLogger(__name__)


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
        self._redis = None
        self._redis_available = False
        self._redis_init_attempted = False
        self._namespace = os.getenv("DHAN_RATE_LIMIT_NAMESPACE", "global")
        self._redis_url = os.getenv("REDIS_URL", "").strip()
        self._distributed_enabled = self._parse_bool(
            os.getenv("DHAN_RATE_LIMIT_DISTRIBUTED", "true")
        ) and bool(self._redis_url)

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "on"}

    async def _ensure_redis(self) -> bool:
        if not self._distributed_enabled:
            return False
        if self._redis_available and self._redis is not None:
            return True
        if self._redis_init_attempted and not self._redis_available:
            return False

        self._redis_init_attempted = True
        try:
            import redis.asyncio as redis_async

            client = redis_async.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            self._redis = client
            self._redis_available = True
            logger.info("✅ DhanRateLimiter using Redis distributed mode")
            return True
        except Exception as e:
            self._redis = None
            self._redis_available = False
            logger.warning(f"⚠️ Redis limiter unavailable, falling back to local limiter: {e}")
            return False

    def _blocked_key(self, key: str) -> str:
        return f"dhan_rl:{self._namespace}:{key}:blocked"

    def _window_key(self, key: str, window_key: str, window_seconds: int, now: float) -> str:
        bucket = int(now // window_seconds)
        return f"dhan_rl:{self._namespace}:{key}:{window_key}:{bucket}"

    async def _is_blocked_distributed(self, key: str) -> bool:
        if not await self._ensure_redis():
            return False
        try:
            value = await self._redis.get(self._blocked_key(key))
            return bool(value)
        except Exception:
            return False

    async def _block_distributed(self, key: str, seconds: int) -> None:
        if not await self._ensure_redis():
            return
        try:
            ttl = max(1, int(seconds))
            await self._redis.setex(self._blocked_key(key), ttl, "1")
        except Exception:
            pass

    async def _wait_distributed(self, key: str) -> None:
        if not await self._ensure_redis():
            await self._wait_locked(key)
            return

        limits = self._limits.get(key) or self._limits["data"]

        while True:
            if await self._is_blocked_distributed(key):
                await asyncio.sleep(0.2)
                continue

            now = time.time()
            should_sleep_for = 0.0

            for window_key, seconds in {
                "per_second": 1,
                "per_minute": 60,
                "per_hour": 3600,
                "per_day": 86400,
            }.items():
                limit = limits.get(window_key)
                if limit is None:
                    continue

                redis_key = self._window_key(key, window_key, seconds, now)
                try:
                    count = await self._redis.incr(redis_key)
                    if count == 1:
                        await self._redis.expire(redis_key, seconds + 2)
                except Exception:
                    await self._wait_locked(key)
                    return

                if count > limit:
                    bucket_start = int(now // seconds) * seconds
                    wait_for = max((bucket_start + seconds) - now, 0.01)
                    if wait_for > should_sleep_for:
                        should_sleep_for = wait_for

            if should_sleep_for > 0:
                await asyncio.sleep(should_sleep_for)
                continue
            return

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
        local_blocked = time.time() < self._blocked_until.get(key, 0.0)
        if local_blocked:
            return True
        return False

    async def is_blocked_async(self, key: str) -> bool:
        if self.is_blocked(key):
            return True
        return await self._is_blocked_distributed(key)

    def block(self, key: str, seconds: int) -> None:
        until = time.time() + max(0, seconds)
        self._blocked_until[key] = max(self._blocked_until.get(key, 0.0), until)

    async def block_async(self, key: str, seconds: int) -> None:
        self.block(key, seconds)
        await self._block_distributed(key, seconds)

    async def wait(self, key: str) -> None:
        if await self._ensure_redis():
            await self._wait_distributed(key)
            return

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
