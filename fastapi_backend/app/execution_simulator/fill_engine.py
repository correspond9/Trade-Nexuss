"""Fill engine for partial and full fills."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.execution_simulator.slippage_model import SlippageModel


@dataclass
class FillResult:
    fill_price: float
    fill_quantity: int
    slippage: float


class FillEngine:
    def __init__(self, slippage_model: SlippageModel) -> None:
        self.slippage_model = slippage_model

    def compute_fills(self, exchange: str, side: str, order_qty: int, top_price: float, top_qty: int, spread: float) -> List[FillResult]:
        if order_qty <= 0 or top_qty <= 0:
            return []
        fill_qty = min(order_qty, top_qty)
        slippage = self.slippage_model.compute_slippage(exchange, order_qty, top_qty, spread, top_price)
        price = top_price + slippage if side == "BUY" else top_price - slippage
        return [FillResult(fill_price=price, fill_quantity=fill_qty, slippage=slippage)]
