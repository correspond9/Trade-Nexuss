"""MCX WebSocket manager (separate from equity engine)."""
from __future__ import annotations

import importlib
import inspect
import logging
import threading
import time
import asyncio
from typing import Dict, List, Optional, Tuple

from app.commodity_engine.commodity_utils import fetch_dhan_credentials
from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
from app.commodity_engine.commodity_futures_service import commodity_futures_service
from app.market.security_ids import EXCHANGE_CODE_MCX

logger = logging.getLogger(__name__)


def _resolve_dhan_feed_class():
    try:
        marketfeed = importlib.import_module("dhanhq.marketfeed")
    except Exception as exc:
        raise ImportError("dhanhq.marketfeed not available") from exc

    for name in ("DhanFeed", "MarketFeed", "MarketFeedV2", "DhanMarketFeed", "MarketFeedWS"):
        cls = getattr(marketfeed, name, None)
        if cls is not None:
            return cls
    raise ImportError("No compatible Dhan feed class found in dhanhq.marketfeed")


def _create_dhan_feed(client_id: str, token: str, instruments):
    feed_cls = _resolve_dhan_feed_class()
    try:
        source = inspect.getsource(feed_cls)
    except Exception:
        source = ""

    wants_creds = "get_client_id" in source or "get_access_token" in source
    if wants_creds:
        class _Creds:
            def __init__(self, cid: str, tok: str):
                self._cid = cid
                self._tok = tok

            def get_client_id(self):
                return self._cid

            def get_access_token(self):
                return self._tok

        creds_obj = _Creds(client_id, token)
        try:
            return feed_cls(creds_obj, instruments)
        except TypeError:
            return feed_cls(creds_obj, token, instruments)

    try:
        return feed_cls(client_id, token, instruments, version="v2")
    except TypeError:
        return feed_cls(client_id, token, instruments)


class _CommodityWSConnection(threading.Thread):
    def __init__(self, connection_id: int, instruments: List[Tuple[int, str]], manager: "CommodityWebSocketManager"):
        super().__init__(daemon=True)
        self.connection_id = connection_id
        self.instruments = instruments
        self.manager = manager
        self._stop = threading.Event()
        self.feed = None

    def stop(self):
        self._stop.set()

    def run(self):
        logger.info(f"[MCX-WS] Connection {self.connection_id} starting with {len(self.instruments)} instruments")
        creds = self.manager.credentials
        if not creds:
            logger.error("[MCX-WS] Missing credentials - cannot start")
            return

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self.feed = _create_dhan_feed(creds["client_id"], creds["access_token"], self.instruments)
        try:
            self.feed.run_forever()
        except Exception as exc:
            logger.error(f"[MCX-WS] Connection {self.connection_id} run_forever failed: {exc}")
            if "429" in str(exc):
                self.manager.block("HTTP_429")
            return

        while not self._stop.is_set():
            try:
                message = self.feed.get_data()
                if message:
                    self.manager.on_message(message)
                time.sleep(0.01)
            except Exception as exc:
                logger.error(f"[MCX-WS] Connection {self.connection_id} error: {exc}")
                if "429" in str(exc):
                    self.manager.block("HTTP_429")
                time.sleep(1)


class CommodityWebSocketManager:
    def __init__(self) -> None:
        self.max_per_connection = 5000
        self.connections: List[_CommodityWSConnection] = []
        self.token_index: Dict[str, Dict[str, object]] = {}
        self.last_quotes: Dict[str, Dict[str, object]] = {}
        self.credentials: Optional[Dict[str, str]] = None
        self._lock = threading.RLock()
        self._block_until = 0.0
        self._last_start_attempt = 0.0
        self._min_start_interval = 30.0
        self._cooldown_seconds = 300.0

    def block(self, reason: str) -> None:
        now = time.time()
        self._block_until = now + self._cooldown_seconds
        logger.warning(f"[MCX-WS] Blocking reconnection for {self._cooldown_seconds}s due to {reason}")

    def reset_block(self) -> None:
        self._block_until = 0.0

    async def refresh_credentials(self) -> None:
        self.credentials = await fetch_dhan_credentials()

    def build_token_index(self) -> None:
        self.token_index = {}
        self.token_index.update(commodity_option_chain_service.token_map)
        self.token_index.update(commodity_futures_service.token_map)

    def _chunk_instruments(self, tokens: List[str]) -> List[List[Tuple[int, str]]]:
        chunks: List[List[Tuple[int, str]]] = []
        current: List[Tuple[int, str]] = []
        for token in tokens:
            current.append((EXCHANGE_CODE_MCX, str(token)))
            if len(current) >= self.max_per_connection:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)
        return chunks

    def stop(self):
        for conn in self.connections:
            conn.stop()
        self.connections = []

    async def start(self):
        now = time.time()
        if now < self._block_until:
            logger.warning("[MCX-WS] Start skipped (cooldown active)")
            return
        if (now - self._last_start_attempt) < self._min_start_interval:
            logger.warning("[MCX-WS] Start skipped (min interval)")
            return
        self._last_start_attempt = now
        await self.refresh_credentials()
        self.build_token_index()
        tokens = list(self.token_index.keys())
        if not tokens:
            logger.warning("[MCX-WS] No MCX tokens available for subscription")
            return

        self.stop()
        chunks = self._chunk_instruments(tokens)
        for idx, chunk in enumerate(chunks, start=1):
            conn = _CommodityWSConnection(idx, chunk, self)
            self.connections.append(conn)
            conn.start()

    def on_message(self, message: Dict[str, object]):
        sec_id = message.get("security_id")
        if not sec_id:
            return
        sec_id_str = str(sec_id)
        self.last_quotes[sec_id_str] = message

        meta = self.token_index.get(sec_id_str)
        if not meta:
            return

        def _extract(payload: Dict[str, object], keys: List[str]) -> Optional[float]:
            for key in keys:
                if key in payload and payload[key] is not None:
                    value = payload[key]
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue
            data = payload.get("data")
            if isinstance(data, dict):
                return _extract(data, keys)
            return None

        ltp = _extract(message, ["LTP", "ltp", "last", "last_price", "lastPrice"])
        bid = _extract(message, ["bid", "best_bid", "bestBid"])
        ask = _extract(message, ["ask", "best_ask", "bestAsk"])
        oi = _extract(message, ["oi", "open_interest", "openInterest"])
        volume = _extract(message, ["volume", "vol", "traded_volume"])
        iv = _extract(message, ["iv", "implied_volatility"])

        if meta.get("option_type"):
            commodity_option_chain_service.update_option_tick(
                symbol=str(meta.get("symbol")),
                expiry=str(meta.get("expiry")),
                strike=float(meta.get("strike")),
                option_type=str(meta.get("option_type")),
                ltp=ltp,
                bid=bid,
                ask=ask,
                oi=oi,
                volume=volume,
                iv=iv,
            )
        else:
            commodity_futures_service.update_future_tick(
                symbol=str(meta.get("symbol")),
                expiry=str(meta.get("expiry")),
                ltp=ltp,
                bid=bid,
                ask=ask,
                oi=oi,
                volume=volume,
            )

    def get_ltp(self, security_id: str) -> Optional[float]:
        quote = self.last_quotes.get(str(security_id))
        if not quote:
            return None
        for key in ("LTP", "ltp", "last", "last_price", "lastPrice"):
            if key in quote and quote[key] is not None:
                try:
                    return float(quote[key])
                except (TypeError, ValueError):
                    continue
        data = quote.get("data")
        if isinstance(data, dict):
            return self.get_ltp(data.get("security_id"))
        return None

    def get_status(self) -> Dict[str, object]:
        """Return MCX WebSocket connection stats for health checks."""
        connections = []
        connected = 0
        total_instruments = 0
        for conn in self.connections:
            count = len(conn.instruments)
            total_instruments += count
            is_alive = conn.is_alive()
            if is_alive:
                connected += 1
            connections.append({
                "id": conn.connection_id,
                "active": is_alive,
                "instruments": count,
            })

        return {
            "total_subscriptions": total_instruments or len(self.token_index),
            "connected_connections": connected,
            "total_connections": len(self.connections),
            "per_connection": connections,
            "cooldown_active": time.time() < self._block_until,
            "cooldown_until": self._block_until if self._block_until else None,
        }


commodity_ws_manager = CommodityWebSocketManager()
