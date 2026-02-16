"""DhanHQ margin calculation wrapper with rate limiting and caching."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp

from app.services.dhan_rate_limiter import DhanRateLimiter

logger = logging.getLogger(__name__)


class DhanMarginService:
    def __init__(self) -> None:
        self.base_url = "https://api.dhan.co"
        self.rate_limiter = DhanRateLimiter()
        self.cache: Dict[str, Tuple[Dict[str, Any], float]] = {}
        self.cache_ttl_seconds = 2

    async def _fetch_credentials(self) -> Optional[Dict[str, str]]:
        try:
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential

            db = SessionLocal()
            try:
                creds = db.query(DhanCredential).filter(DhanCredential.is_default == True).first()
                if not creds:
                    creds = db.query(DhanCredential).first()
                if not creds:
                    return None
                access_token = (creds.daily_token or creds.auth_token or "").strip()
                if not access_token:
                    return None
                return {
                    "client_id": (creds.client_id or "").strip(),
                    "access_token": access_token,
                }
            finally:
                db.close()
        except Exception as exc:
            logger.error("Failed to load Dhan credentials: %s", exc)
            return None

    def _cache_key(self, payload: Dict[str, Any], endpoint: str) -> str:
        return f"{endpoint}:{hash(str(payload))}"

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        cached = self.cache.get(key)
        if not cached:
            return None
        data, timestamp = cached
        if (datetime.utcnow().timestamp() - timestamp) <= self.cache_ttl_seconds:
            return data
        self.cache.pop(key, None)
        return None

    def _cache_set(self, key: str, data: Dict[str, Any]) -> None:
        self.cache[key] = (data, datetime.utcnow().timestamp())

    def _normalize_segment(self, segment: Optional[Union[str, int]]) -> Optional[int]:
        if segment is None:
            return None
        if isinstance(segment, int):
            return segment
        text = str(segment).strip().upper()
        if not text:
            return None
        if text.isdigit():
            return int(text)

        # Map known segment names to Dhan exchange codes for margin API.
        segment_map = {
            "IDX_I": 0,
            "NSE_EQ": 1,
            "NSE_FNO": 2,
            "BSE_EQ": 4,
            "MCX_COMM": 5,
            "MCX_COM": 5,
            "BSE_FNO": 8,
        }
        return segment_map.get(text)

    def _normalize_product_type(self, product_type: Optional[str]) -> str:
        if not product_type:
            return "INTRADAY"
        text = product_type.upper()
        if text in {"MIS", "INTRADAY"}:
            return "INTRADAY"
        if text in {"NORMAL", "NRML", "MARGIN"}:
            return "MARGIN"
        if text in {"CNC", "DELIVERY"}:
            return "CNC"
        if text == "MTF":
            return "MTF"
        return "INTRADAY"

    async def _post(self, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if await self.rate_limiter.is_blocked_async("data"):
            return None
        await self.rate_limiter.wait("data")

        creds = await self._fetch_credentials()
        if not creds:
            return None

        headers = {
            "access-token": creds["access_token"],
            "client-id": creds["client_id"],
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"
        key = self._cache_key(payload, endpoint)
        cached = self._cache_get(key)
        if cached:
            return cached

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                    data = await response.json()
                    if response.status != 200:
                        logger.warning("Dhan margin API error %s: %s", response.status, data)
                        if response.status in (401, 403):
                            await self.rate_limiter.block_async("data", 900)
                        if response.status == 429:
                            await self.rate_limiter.block_async("data", 120)
                        return None
                    self._cache_set(key, data)
                    return data
        except asyncio.TimeoutError:
            logger.warning("Dhan margin API timeout")
            return None
        except Exception as exc:
            logger.error("Dhan margin API error: %s", exc)
            return None

    async def calculate_margin_single(
        self,
        exchange_segment: Union[str, int],
        transaction_type: str,
        quantity: int,
        product_type: str,
        security_id: str,
        price: float,
        trigger_price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        segment = self._normalize_segment(exchange_segment)
        if not segment:
            return None

        creds = await self._fetch_credentials()
        if not creds:
            return None

        payload = {
            "dhanClientId": creds["client_id"],
            "exchangeSegment": segment,
            "transactionType": transaction_type.upper(),
            "quantity": int(quantity),
            "productType": self._normalize_product_type(product_type),
            "securityId": str(security_id),
            "price": float(price),
        }
        if trigger_price is not None:
            payload["triggerPrice"] = float(trigger_price)

        return await self._post("/v2/margincalculator", payload)

    async def calculate_margin_multi(
        self,
        scripts: List[Dict[str, Any]],
        include_positions: bool = True,
        include_orders: bool = True,
    ) -> Optional[Dict[str, Any]]:
        if not scripts:
            return None

        normalized_scripts: List[Dict[str, Any]] = []
        for script in scripts:
            segment = self._normalize_segment(script.get("exchangeSegment"))
            if not segment:
                continue
            normalized_scripts.append({
                "exchangeSegment": segment,
                "transactionType": str(script.get("transactionType") or "BUY").upper(),
                "quantity": int(script.get("quantity") or 0),
                "productType": self._normalize_product_type(script.get("productType")),
                "securityId": str(script.get("securityId")),
                "price": float(script.get("price") or 0),
                "triggerPrice": script.get("triggerPrice"),
            })

        if not normalized_scripts:
            return None

        payload = {
            "includePosition": include_positions,
            "includeOrders": include_orders,
            "scripts": normalized_scripts,
        }

        return await self._post("/v2/margincalculator/multi", payload)


dhan_margin_service = DhanMarginService()
