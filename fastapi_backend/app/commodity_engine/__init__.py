"""Commodity engine orchestration (MCX)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import aiohttp

from app.commodity_engine.commodity_expiry_service import commodity_expiry_service
from app.commodity_engine.commodity_futures_service import commodity_futures_service, MCX_FUTURES_SYMBOLS
from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service, MCX_UNDERLYINGS
from app.commodity_engine.commodity_utils import fetch_dhan_credentials
from app.commodity_engine.commodity_market_session_manager import commodity_market_session_manager
from app.commodity_engine.commodity_ws_manager import commodity_ws_manager

logger = logging.getLogger(__name__)


class CommodityEngine:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_expiry_snapshot: Dict[str, str] = {}
        self._rest_lock = asyncio.Lock()
        self._rest_last_call: Optional[float] = None
        self._rest_min_interval = 1.0
        self._ltp_cache: Dict[str, Dict[str, object]] = {}
        self._rest_block_until: float = 0.0
        self._rest_cooldown_seconds = 120.0
        self._startup_option_delay_seconds = 90.0

    async def _rate_limit_rest(self) -> None:
        async with self._rest_lock:
            now = asyncio.get_event_loop().time()
            if now < self._rest_block_until:
                await asyncio.sleep(self._rest_block_until - now)
            last = self._rest_last_call or 0.0
            wait = self._rest_min_interval - (now - last)
            if wait > 0:
                await asyncio.sleep(wait)
            self._rest_last_call = asyncio.get_event_loop().time()

    async def _fetch_ltp_rest(self, symbol: str) -> Optional[float]:
        if asyncio.get_event_loop().time() < self._rest_block_until:
            return None
        cached = self._ltp_cache.get(symbol)
        if cached and (asyncio.get_event_loop().time() - float(cached.get("ts", 0.0))) < 2.0:
            return cached.get("ltp")
        meta = commodity_expiry_service.get_underlying_meta(symbol)
        if not meta:
            return None
        creds = await fetch_dhan_credentials()
        if not creds:
            return None
        headers = {
            "access-token": creds["access_token"],
            "client-id": creds["client_id"],
            "Content-Type": "application/json",
        }
        url = "https://api.dhan.co/v2/marketfeed/quote"
        payload = {meta["segment"]: [int(meta["security_id"])]}
        for attempt in range(3):
            await self._rate_limit_rest()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.warning(f"⚠️ MCX quote API error for {symbol}: {response.status} - {error_text}")
                            if response.status in (429, 502):
                                if response.status == 429:
                                    self._rest_block_until = asyncio.get_event_loop().time() + self._rest_cooldown_seconds
                                await asyncio.sleep(2 + attempt * 2)
                                continue
                            return None
                        data = await response.json()
                        segment_data = data.get("data", {}).get(meta["segment"], {})
                        sec_payload = segment_data.get(str(meta["security_id"])) or segment_data.get(int(meta["security_id"]))
                        if isinstance(sec_payload, list) and sec_payload:
                            sec_payload = sec_payload[0]
                        if isinstance(sec_payload, dict):
                            ltp = sec_payload.get("ltp") or sec_payload.get("LTP")
                            if ltp is not None:
                                value = float(ltp)
                                self._ltp_cache[symbol] = {"ltp": value, "ts": asyncio.get_event_loop().time()}
                                return value
            except Exception as exc:
                logger.error(f"❌ MCX REST LTP fetch failed for {symbol}: {exc}")
                await asyncio.sleep(1 + attempt)
        return None

    async def _get_underlying_ltp(self, symbol: str) -> Optional[float]:
        meta = commodity_expiry_service.get_underlying_meta(symbol)
        if meta and meta.get("security_id"):
            ltp = commodity_ws_manager.get_ltp(str(meta["security_id"]))
            if ltp is not None:
                return ltp
        for attempt in range(3):
            ltp = await self._fetch_ltp_rest(symbol)
            if ltp is not None:
                return ltp
            await asyncio.sleep(2.0 + attempt * 2)
        return None

    async def refresh_all(self, reason: str, include_options: bool = True) -> None:
        logger.info(f"[MCX] Refreshing commodity cache ({reason})")
        if include_options:
            for symbol in MCX_UNDERLYINGS:
                ltp = await self._get_underlying_ltp(symbol)
                if ltp is None:
                    logger.warning(f"⚠️ MCX LTP missing for {symbol} - skipping option chain")
                    continue
                await commodity_option_chain_service.build_for_underlying(symbol, ltp)
                await asyncio.sleep(1.0)

        for symbol in MCX_FUTURES_SYMBOLS:
            await commodity_futures_service.build_for_symbol(symbol)
            await asyncio.sleep(1.0)

        commodity_ws_manager.build_token_index()
        try:
            from app.market_orchestrator import get_orchestrator
            await get_orchestrator().start_mcx_stream()
        except Exception:
            await commodity_ws_manager.start()

        logger.info("[MCX] Commodity cache refresh complete")

    async def refresh_options_only(self, reason: str) -> None:
        logger.info(f"[MCX] Refreshing option chains ({reason})")
        for symbol in MCX_UNDERLYINGS:
            ltp = await self._get_underlying_ltp(symbol)
            if ltp is None:
                logger.warning(f"⚠️ MCX LTP missing for {symbol} - skipping option chain")
                continue
            await commodity_option_chain_service.build_for_underlying(symbol, ltp)
            await asyncio.sleep(1.0)

        commodity_ws_manager.build_token_index()
        try:
            from app.market_orchestrator import get_orchestrator
            await get_orchestrator().start_mcx_stream()
        except Exception:
            await commodity_ws_manager.start()

        logger.info("[MCX] Option chain refresh complete")

    async def _check_expiry_rollover(self) -> bool:
        changed = False
        for symbol in MCX_UNDERLYINGS + MCX_FUTURES_SYMBOLS:
            expiries = await commodity_expiry_service.fetch_expiry_list(symbol)
            selected = commodity_expiry_service.select_current_next(expiries)
            snapshot = ",".join(selected)
            key = symbol.upper()
            if self._last_expiry_snapshot.get(key) != snapshot and selected:
                self._last_expiry_snapshot[key] = snapshot
                changed = True
        return changed

    async def _session_loop(self) -> None:
        while self._running:
            if commodity_market_session_manager.check_transition():
                await self.refresh_all("market_open")
            if await self._check_expiry_rollover():
                await self.refresh_all("expiry_rollover")
            await asyncio.sleep(60)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self.refresh_all("startup", include_options=False)

        async def _delayed_refresh():
            await asyncio.sleep(self._startup_option_delay_seconds)
            await self.refresh_options_only("startup_delay")

        asyncio.create_task(_delayed_refresh())
        self._task = asyncio.create_task(self._session_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        commodity_ws_manager.stop()


commodity_engine = CommodityEngine()
