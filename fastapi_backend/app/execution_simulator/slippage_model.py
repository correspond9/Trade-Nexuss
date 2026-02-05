"""Slippage model for execution simulation."""
from __future__ import annotations

from app.execution_simulator.execution_config import ExecutionConfig


class SlippageModel:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def compute_slippage(self, exchange: str, order_qty: int, top_qty: int, spread: float, ref_price: float) -> float:
        cfg = self.config.for_exchange(exchange)
        liquidity = max(float(top_qty), 1.0)
        size_ratio = min(order_qty / liquidity, 5.0)
        spread_factor = min(spread / ref_price, 0.01) if ref_price else 0.0
        slippage_pct = cfg.base_slippage_pct * (1.0 + size_ratio) + spread_factor
        return ref_price * slippage_pct
