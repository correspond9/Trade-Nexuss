"""Order rejection rules for execution simulation."""
from __future__ import annotations

from typing import Optional

from app.ems.exchange_clock import is_market_open
from app.execution_simulator.execution_config import ExecutionConfig


class RejectionEngine:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def validate(self, exchange: str, order_type: str, side: str, price: Optional[float], quantity: int, snapshot: dict) -> Optional[str]:
        if not is_market_open(exchange):
            return "MARKET_CLOSED"

        cfg = self.config.for_exchange(exchange)
        if quantity > cfg.max_order_size:
            return "ORDER_SIZE_TOO_LARGE"

        if order_type == "LIMIT" and (price is None or price <= 0):
            return "INVALID_LIMIT_PRICE"

        bid = snapshot.get("best_bid")
        ask = snapshot.get("best_ask")
        if bid is None or ask is None:
            return "NO_LIQUIDITY"

        if order_type == "LIMIT" and price is not None:
            reference = ask if side == "BUY" else bid
            if reference and abs(price - reference) / reference > cfg.price_tolerance_pct:
                return "PRICE_OUT_OF_TOLERANCE"

        return None
