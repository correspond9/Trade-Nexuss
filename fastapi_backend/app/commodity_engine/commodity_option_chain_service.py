"""MCX commodity option chain service (parallel to equity engine)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.commodity_engine.commodity_expiry_service import commodity_expiry_service
from app.commodity_engine.commodity_utils import fetch_dhan_credentials
from app.market.instrument_master.registry import REGISTRY
from app.market_cache.options import set_option_chain, update_option_leg

logger = logging.getLogger(__name__)

MCX_UNDERLYINGS = ["CRUDEOIL", "NATURALGAS"]


class CommodityOptionChainService:
    def __init__(self) -> None:
        self.option_chain_cache: Dict[str, Dict[str, Dict]] = {}
        self.token_map: Dict[str, Dict[str, object]] = {}
        self.last_refresh: Dict[str, str] = {}

    def _normalize_expiry(self, expiry: str) -> Optional[datetime.date]:
        return REGISTRY._normalize_expiry(expiry)

    def _resolve_option_token(self, symbol: str, expiry: str, strike: float, option_type: str) -> Optional[str]:
        symbol_upper = symbol.upper()
        target_expiry = self._normalize_expiry(expiry)
        records = REGISTRY.by_underlying.get(symbol_upper, [])
        best = None
        for row in records:
            exchange = (row.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            row_expiry = self._normalize_expiry(row.get("SM_EXPIRY_DATE", ""))
            if target_expiry and row_expiry != target_expiry:
                continue
            row_strike = row.get("STRIKE_PRICE")
            row_opt = (row.get("OPTION_TYPE") or "").strip().upper()
            try:
                row_strike_val = float(row_strike)
            except (TypeError, ValueError):
                continue
            if row_opt != option_type.upper():
                continue
            if abs(row_strike_val - float(strike)) > 0.0001:
                continue
            sec_id = (row.get("SECURITY_ID") or "").strip()
            if not sec_id:
                continue
            best = sec_id
            break
        return best

    def _resolve_lot_size(self, symbol: str) -> Optional[int]:
        symbol_upper = symbol.upper()
        for row in REGISTRY.by_underlying.get(symbol_upper, []):
            exchange = (row.get("EXCH_ID") or "").strip().upper()
            if exchange != "MCX":
                continue
            lot = row.get("LOT_SIZE") or row.get("MARKET_LOT")
            try:
                lot_val = int(float(lot))
                if lot_val > 0:
                    return lot_val
            except (TypeError, ValueError):
                continue
        return None

    def _build_strikes(self, atm: float, strike_interval: float) -> List[float]:
        strikes = []
        for i in range(-25, 26):
            strike = atm + (i * strike_interval)
            if strike > 0:
                strikes.append(round(strike, 6))
        return strikes

    def _build_skeleton(
        self,
        symbol: str,
        expiry: str,
        lot_size: int,
        strike_interval: float,
        atm: float,
        strikes: List[float],
    ) -> Dict:
        strikes_dict: Dict[str, Dict] = {}
        for strike in strikes:
            strike_key = str(float(strike))
            ce_token = self._resolve_option_token(symbol, expiry, strike, "CE")
            pe_token = self._resolve_option_token(symbol, expiry, strike, "PE")
            strikes_dict[strike_key] = {
                "CE": {
                    "token": ce_token,
                    "ltp": None,
                    "bid": None,
                    "ask": None,
                    "oi": None,
                    "volume": None,
                    "iv": None,
                },
                "PE": {
                    "token": pe_token,
                    "ltp": None,
                    "bid": None,
                    "ask": None,
                    "oi": None,
                    "volume": None,
                    "iv": None,
                },
            }
            if ce_token:
                self.token_map[str(ce_token)] = {
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": float(strike),
                    "option_type": "CE",
                }
            if pe_token:
                self.token_map[str(pe_token)] = {
                    "symbol": symbol,
                    "expiry": expiry,
                    "strike": float(strike),
                    "option_type": "PE",
                }

        return {
            "exchange": "MCX",
            "segment": "COM",
            "underlying": symbol,
            "expiry": expiry,
            "lot_size": lot_size,
            "strike_interval": strike_interval,
            "atm": atm,
            "strikes": strikes_dict,
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def build_for_underlying(self, symbol: str, ltp: float) -> Dict[str, Dict]:
        expiries = await commodity_expiry_service.fetch_expiry_list(symbol)
        selected = commodity_expiry_service.select_current_next(expiries)
        if not selected:
            return {}

        strike_interval = REGISTRY.get_strike_step(symbol)
        if strike_interval <= 0:
            strike_interval = 1.0

        lot_size = self._resolve_lot_size(symbol) or 1

        built = {}
        for expiry in selected:
            atm = round(ltp / strike_interval) * strike_interval
            strikes = self._build_strikes(atm, strike_interval)
            skeleton = self._build_skeleton(symbol, expiry, lot_size, strike_interval, atm, strikes)

            if symbol not in self.option_chain_cache:
                self.option_chain_cache[symbol] = {}
            self.option_chain_cache[symbol][expiry] = skeleton
            set_option_chain("MCX", symbol, expiry, skeleton)
            built[expiry] = skeleton

        self.last_refresh[symbol] = datetime.utcnow().isoformat()
        return built

    def get_chain(self, symbol: str, expiry: str) -> Optional[Dict]:
        return self.option_chain_cache.get(symbol.upper(), {}).get(expiry)

    def update_option_tick(
        self,
        symbol: str,
        expiry: str,
        strike: float,
        option_type: str,
        ltp: Optional[float] = None,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        oi: Optional[float] = None,
        volume: Optional[float] = None,
        iv: Optional[float] = None,
    ) -> None:
        updates = {
            "ltp": ltp,
            "bid": bid,
            "ask": ask,
            "oi": oi,
            "volume": volume,
            "iv": iv,
        }
        update_option_leg("MCX", symbol, expiry, strike, option_type, updates)


commodity_option_chain_service = CommodityOptionChainService()
commodity_option_chain_cache = commodity_option_chain_service.option_chain_cache
