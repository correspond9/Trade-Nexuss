"""Commodity expiry discovery for MCX using Dhan option chain expiry API."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional

import aiohttp

from app.commodity_engine.commodity_utils import fetch_dhan_credentials
from app.market.instrument_master.registry import REGISTRY
from app.services.dhan_rate_limiter import DhanRateLimiter

logger = logging.getLogger(__name__)


@dataclass
class CommodityExpiryRegistry:
    expiries: Dict[str, List[str]] = field(default_factory=dict)
    last_updated: Dict[str, str] = field(default_factory=dict)

    def set_expiries(self, symbol: str, expiries: List[str]) -> None:
        self.expiries[symbol.upper()] = expiries
        self.last_updated[symbol.upper()] = datetime.utcnow().isoformat()

    def get_expiries(self, symbol: str) -> List[str]:
        return self.expiries.get(symbol.upper(), [])


class CommodityExpiryService:
    def __init__(self) -> None:
        self.registry = CommodityExpiryRegistry()
        self.dhan_base_url = "https://api.dhan.co"
        self._rate_lock = asyncio.Lock()
        self._last_call = None
        self._min_interval = 1.0
        self._cache_ttl_seconds = 300
        self.rate_limiter = DhanRateLimiter()

    def _parse_expiry(self, expiry: str) -> Optional[date]:
        if not expiry:
            return None
        text = str(expiry).strip().upper()
        for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%b%y", "%d%B%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def select_current_next(self, expiries: List[str]) -> List[str]:
        today = datetime.utcnow().date()
        parsed = []
        for exp in expiries:
            exp_date = self._parse_expiry(exp)
            if not exp_date:
                continue
            if exp_date >= today:
                parsed.append((exp_date, exp))
        parsed.sort(key=lambda x: x[0])
        return [exp for _, exp in parsed[:2]]

    def _resolve_underlying_meta(self, symbol: str) -> Optional[Dict[str, str]]:
        symbol_upper = symbol.upper()

        # Prefer nearest-month MCX future (valid active security id)
        nearest = REGISTRY.get_nearest_mcx_future(symbol_upper)
        if nearest and nearest.get("security_id"):
            return {"security_id": str(nearest["security_id"]), "segment": "MCX_COMM"}

        records = REGISTRY.get_by_symbol(symbol_upper)
        if not records:
            return None

        # Fallback: first MCX record with a security id
        for record in records:
            exchange = (record.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            security_id = (record.get("SECURITY_ID") or "").strip()
            if security_id:
                return {"security_id": security_id, "segment": "MCX_COMM"}

        return None

    def get_underlying_meta(self, symbol: str) -> Optional[Dict[str, str]]:
        return self._resolve_underlying_meta(symbol)

    def _fallback_expiries_from_registry(self, symbol: str) -> List[str]:
        expiries = set()
        for row in REGISTRY.get_by_symbol(symbol.upper()):
            exchange = (row.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            raw_expiry = row.get("SM_EXPIRY_DATE") or row.get("EXPIRY_DATE")
            parsed = self._parse_expiry(raw_expiry) if raw_expiry else None
            if parsed:
                expiries.add(parsed.isoformat())
        return sorted(expiries)

    async def _rate_limit(self) -> None:
        async with self._rate_lock:
            if not self._last_call:
                self._last_call = datetime.utcnow()
                return
            elapsed = (datetime.utcnow() - self._last_call).total_seconds()
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            self._last_call = datetime.utcnow()

    async def fetch_expiry_list(self, symbol: str) -> List[str]:
        cached = self.registry.get_expiries(symbol)
        last_updated = self.registry.last_updated.get(symbol.upper())
        if cached and last_updated:
            try:
                age = (datetime.utcnow() - datetime.fromisoformat(last_updated)).total_seconds()
                if age < self._cache_ttl_seconds:
                    return cached
            except Exception:
                pass

        await self._rate_limit()
        await self.rate_limiter.wait("expiry")
        if self.rate_limiter.is_blocked("expiry"):
            fallback = self._fallback_expiries_from_registry(symbol)
            if fallback:
                self.registry.set_expiries(symbol, fallback)
            return fallback
        creds = await fetch_dhan_credentials()
        if not creds:
            return []

        meta = self._resolve_underlying_meta(symbol)
        if not meta:
            logger.warning(f"⚠️ MCX meta not found for {symbol}; using registry fallback")
            fallback = self._fallback_expiries_from_registry(symbol)
            if fallback:
                self.registry.set_expiries(symbol, fallback)
            return fallback

        headers = {
            "access-token": creds["access_token"],
            "client-id": creds["client_id"],
            "Content-Type": "application/json",
        }
        url = f"{self.dhan_base_url}/v2/optionchain/expirylist"
        payload = {
            "UnderlyingScrip": int(meta["security_id"]),
            "UnderlyingSeg": meta["segment"],
        }

        for attempt in range(3):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            expiries = data.get("data", [])
                            if isinstance(expiries, list):
                                self.registry.set_expiries(symbol, expiries)
                                return expiries
                            return []

                        error_text = await response.text()
                        if response.status == 502:
                            break
                        logger.warning(
                            f"⚠️ MCX expiry API error for {symbol}: {response.status} - {error_text}"
                        )
                        if response.status in (401, 403):
                            self.rate_limiter.block("expiry", 900)
                        if response.status == 429:
                            self.rate_limiter.block("expiry", 120)
                        if response.status == 429:
                            await asyncio.sleep(3 + attempt * 2)
                            continue
                        fallback = self._fallback_expiries_from_registry(symbol)
                        if fallback:
                            self.registry.set_expiries(symbol, fallback)
                            return fallback
                        return []
            except Exception as exc:
                logger.warning(f"⚠️ MCX expiry fetch failed for {symbol}: {exc}")
                await asyncio.sleep(1 + attempt)
        fallback = self._fallback_expiries_from_registry(symbol)
        if fallback:
            self.registry.set_expiries(symbol, fallback)
            return fallback
        return []


commodity_expiry_service = CommodityExpiryService()
