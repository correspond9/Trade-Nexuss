"""MCX commodity futures service (parallel to equity engine)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.commodity_engine.commodity_expiry_service import commodity_expiry_service
from app.market.instrument_master.registry import REGISTRY
from app.market_cache.futures import set_future, update_future

logger = logging.getLogger(__name__)

MCX_FUTURES_SYMBOLS = [
    "CRUDEOIL",
    "NATURALGAS",
    "COPPER",
    "GOLD",
    "GOLDM",
    "SILVER",
    "SILVERM",
    "SILVERMIC",
    "ALUMINIUM",
]


class CommodityFuturesService:
    def __init__(self) -> None:
        self.futures_cache: Dict[str, Dict[str, Dict]] = {}
        self.token_map: Dict[str, Dict[str, object]] = {}
        self.last_refresh: Dict[str, str] = {}

    def _normalize_expiry(self, expiry: str):
        return REGISTRY._normalize_expiry(expiry)

    def _resolve_future_record(self, symbol: str, expiry: str) -> Optional[Dict]:
        symbol_upper = symbol.upper()
        target_expiry = self._normalize_expiry(expiry)
        candidates = []

        for row in REGISTRY.get_by_symbol(symbol_upper):
            exchange = (row.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            option_type = (row.get("OPTION_TYPE") or "").strip().upper()
            if option_type not in ("", "XX"):
                continue
            row_expiry = self._normalize_expiry(row.get("SM_EXPIRY_DATE", ""))
            if target_expiry and row_expiry == target_expiry:
                return row
            if row_expiry:
                candidates.append((row_expiry, row))

        if target_expiry and candidates:
            # Pick the closest expiry if exact match not found (within 7 days)
            candidates.sort(key=lambda item: abs((item[0] - target_expiry).days))
            nearest_expiry, nearest_row = candidates[0]
            if abs((nearest_expiry - target_expiry).days) <= 7:
                return nearest_row

        return candidates[0][1] if candidates else None

    def _build_entry(self, symbol: str, expiry: str, record: Dict) -> Dict:
        security_id = (record.get("SECURITY_ID") or "").strip()
        lot_size = None
        try:
            from app.services.dhan_security_id_mapper import dhan_security_mapper
            lot_from_csv = dhan_security_mapper.get_lot_size(symbol)
            if isinstance(lot_from_csv, int) and lot_from_csv > 0:
                lot_size = lot_from_csv
        except Exception:
            pass
        tick_size = record.get("TICK_SIZE")
        try:
            lot_size = int(float(lot_size)) if lot_size is not None else None
        except (TypeError, ValueError):
            lot_size = None
        try:
            tick_size = float(tick_size) if tick_size is not None else None
        except (TypeError, ValueError):
            tick_size = None

        entry = {
            "exchange": "MCX",
            "segment": "COM",
            "symbol": symbol,
            "expiry": expiry,
            "token": security_id or None,
            "ltp": None,
            "bid": None,
            "ask": None,
            "volume": None,
            "oi": None,
            "lot_size": lot_size,
            "tick_size": tick_size,
            "last_updated": datetime.utcnow().isoformat(),
        }
        if security_id:
            self.token_map[str(security_id)] = {
                "symbol": symbol,
                "expiry": expiry,
            }
        return entry

    async def build_for_symbol(self, symbol: str) -> Dict[str, Dict]:
        expiries = await commodity_expiry_service.fetch_expiry_list(symbol)
        selected = commodity_expiry_service.select_current_next(expiries)
        if not selected:
            return {}

        built = {}
        for expiry in selected:
            record = self._resolve_future_record(symbol, expiry)
            if not record:
                logger.warning(f"⚠️ MCX futures record missing for {symbol} {expiry}")
                continue
            entry = self._build_entry(symbol, expiry, record)
            if symbol not in self.futures_cache:
                self.futures_cache[symbol] = {}
            self.futures_cache[symbol][expiry] = entry
            set_future("MCX", symbol, expiry, entry)
            built[expiry] = entry

        self.last_refresh[symbol] = datetime.utcnow().isoformat()
        return built

    def list_futures(self, expiry: Optional[str] = None) -> List[Dict]:
        rows = []
        for symbol in self.futures_cache:
            for exp, entry in self.futures_cache[symbol].items():
                if expiry and exp != expiry:
                    continue
                rows.append(entry)
        return rows

    def update_future_tick(
        self,
        symbol: str,
        expiry: str,
        ltp: Optional[float] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        oi: Optional[float] = None,
        volume: Optional[float] = None,
    ) -> None:
        updates = {
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "oi": oi,
            "volume": volume,
            "last_updated": datetime.utcnow().isoformat(),
        }
        update_future("MCX", symbol, expiry, updates)


commodity_futures_service = CommodityFuturesService()
commodity_futures_cache = commodity_futures_service.futures_cache
