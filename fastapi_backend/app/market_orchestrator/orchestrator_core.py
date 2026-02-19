"""Market Data Orchestrator core."""
from __future__ import annotations

import time
from threading import RLock
from typing import Dict, Optional, Tuple
import asyncio
import os

from app.market_orchestrator.exchange_router import ExchangeRouter
from app.market_orchestrator.market_cache_manager import MarketCacheManager
from app.market_orchestrator.reconnect_manager import ReconnectManager
from app.market_orchestrator.session_manager import SessionManager
from app.market_orchestrator.subscription_registry import SubscriptionEntry, SubscriptionRegistry
from app.market_orchestrator.websocket_controller import WebSocketController


class RestThrottle:
    def __init__(self) -> None:
        self._lock = RLock()
        self._last_call: Dict[str, float] = {}

    def wait_for_slot(self, key: str, min_interval: float) -> None:
        with self._lock:
            last = self._last_call.get(key, 0.0)
            now = time.monotonic()
            wait = min_interval - (now - last)
            if wait > 0:
                time.sleep(wait)
            self._last_call[key] = time.monotonic()


class MarketDataOrchestrator:
    def __init__(self) -> None:
        self.registry = SubscriptionRegistry()
        self.ws_controller = WebSocketController()
        self.cache_manager = MarketCacheManager()
        self.exchange_router = ExchangeRouter()
        self.session_manager = SessionManager()
        self.reconnect_manager = ReconnectManager()
        self.rest_throttle = RestThrottle()
        self.last_tick_time: Optional[float] = None
        self._lock = RLock()
        self._streams_lock = RLock()
        self._streams_started = False

    def subscribe(self, token: str, exchange: str, segment: str, symbol: str, expiry: Optional[str] = None, priority: Optional[str] = None, meta: Optional[Dict[str, object]] = None) -> Tuple[bool, str, Optional[int]]:
        if self.registry.exists(token):
            entry = self.registry.get(token)
            return True, "already_subscribed", entry.websocket_id if entry else None

        ok, ws_id, reason = self.ws_controller.add_token(token)
        if not ok:
            return False, reason, None

        entry = SubscriptionEntry(
            token=token,
            exchange=exchange,
            segment=segment,
            symbol=symbol,
            expiry=expiry,
            websocket_id=ws_id,
            active=True,
            meta=meta or {},
        )
        self.registry.add(entry)
        return True, "subscribed", ws_id

    def unsubscribe(self, token: str) -> bool:
        removed = self.ws_controller.remove_token(token)
        self.registry.remove(token)
        return removed

    def on_tick(self, tick: Dict) -> None:
        with self._lock:
            self.last_tick_time = time.time()
        self.cache_manager.update_from_tick(tick)
        self.exchange_router.route_tick(tick)

    def on_disconnect(self, ws_id: int, error: Optional[str] = None) -> None:
        self.ws_controller.mark_inactive(ws_id)
        self.reconnect_manager.mark_disconnected(ws_id, error=error)

    def on_connected(self, ws_id: int, handle: object) -> None:
        self.ws_controller.register_handle(ws_id, handle)
        self.reconnect_manager.mark_connected(ws_id)

    def rest_call(self, key: str, min_interval: float, func, *args, **kwargs):
        self.rest_throttle.wait_for_slot(key, min_interval)
        return func(*args, **kwargs)

    def get_status(self) -> Dict[str, object]:
        ws_status = self.ws_controller.get_status()
        return {
            "total_ws_connections": ws_status["total_ws_connections"],
            "total_subscriptions": ws_status["total_subscriptions"],
            "tokens_per_ws": ws_status["tokens_per_ws"],
            "last_tick_time": self.last_tick_time,
            "cache_status": self.cache_manager.cache_status(),
        }

    def start_equity_stream(self) -> None:
        from app.dhan.live_feed import start_live_feed
        start_live_feed()

    async def start_mcx_stream(self) -> None:
        from app.commodity_engine.commodity_futures_service import commodity_futures_service, MCX_FUTURES_SYMBOLS
        from app.commodity_engine.commodity_ws_manager import commodity_ws_manager

        # Ensure token maps are populated before starting MCX websocket manager.
        # In production cold-starts, token_map can be empty if commodity refresh has not run yet.
        if not commodity_ws_manager.token_index:
            for symbol in MCX_FUTURES_SYMBOLS:
                try:
                    await commodity_futures_service.build_for_symbol(symbol)
                except Exception:
                    continue
            commodity_ws_manager.build_token_index()

        await commodity_ws_manager.start()

    async def start_streams(self) -> None:
        with self._streams_lock:
            if self._streams_started:
                return
            self._streams_started = True
        flag = (os.getenv("DISABLE_DHAN_WS") or os.getenv("BACKEND_OFFLINE") or os.getenv("DISABLE_MARKET_STREAMS") or "").strip().lower()
        if flag in ("1", "true", "yes", "on"):
            return

        # Runtime admin kill-switch.
        try:
            from app.market.dhan_connection_guard import is_enabled
            if not is_enabled():
                return
        except Exception:
            # If guard is unavailable for any reason, don't block stream startup.
            pass

        commodities_enabled = (os.getenv("ENABLE_COMMODITIES") or "").strip().lower() in ("1", "true", "yes", "on")

        self.start_equity_stream()
        if commodities_enabled:
            await self.start_mcx_stream()

    def start_streams_sync(self) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.start_streams())
        else:
            asyncio.run(self.start_streams())
