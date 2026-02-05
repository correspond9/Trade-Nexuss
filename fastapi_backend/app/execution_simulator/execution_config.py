"""Configuration loader for execution simulator."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Dict, Tuple


@dataclass
class ExchangeConfig:
    latency_ms: Tuple[int, int]
    base_slippage_pct: float
    max_order_size: int
    price_tolerance_pct: float
    timeout_seconds: int


@dataclass
class ExecutionConfig:
    exchange: Dict[str, ExchangeConfig] = field(default_factory=dict)
    default_bid_qty: int = 100
    default_ask_qty: int = 100
    max_queue_depth: int = 5000

    @staticmethod
    def defaults() -> "ExecutionConfig":
        return ExecutionConfig(
            exchange={
                "NSE": ExchangeConfig(latency_ms=(50, 200), base_slippage_pct=0.0005, max_order_size=2000, price_tolerance_pct=0.03, timeout_seconds=20),
                "BSE": ExchangeConfig(latency_ms=(50, 220), base_slippage_pct=0.0007, max_order_size=1500, price_tolerance_pct=0.03, timeout_seconds=20),
                "MCX": ExchangeConfig(latency_ms=(80, 300), base_slippage_pct=0.0015, max_order_size=500, price_tolerance_pct=0.05, timeout_seconds=25),
                "DEFAULT": ExchangeConfig(latency_ms=(50, 200), base_slippage_pct=0.0007, max_order_size=1000, price_tolerance_pct=0.03, timeout_seconds=20),
            }
        )

    @staticmethod
    def load() -> "ExecutionConfig":
        path = os.getenv("EXECUTION_CONFIG_PATH", "")
        if not path:
            return ExecutionConfig.defaults()
        if not os.path.exists(path):
            return ExecutionConfig.defaults()
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return ExecutionConfig.defaults()

        config = ExecutionConfig.defaults()
        exchange_cfg = payload.get("exchange", {}) if isinstance(payload, dict) else {}
        for key, value in exchange_cfg.items():
            if not isinstance(value, dict):
                continue
            config.exchange[key.upper()] = ExchangeConfig(
                latency_ms=tuple(value.get("latency_ms", config.exchange["DEFAULT"].latency_ms)),
                base_slippage_pct=float(value.get("base_slippage_pct", config.exchange["DEFAULT"].base_slippage_pct)),
                max_order_size=int(value.get("max_order_size", config.exchange["DEFAULT"].max_order_size)),
                price_tolerance_pct=float(value.get("price_tolerance_pct", config.exchange["DEFAULT"].price_tolerance_pct)),
                timeout_seconds=int(value.get("timeout_seconds", config.exchange["DEFAULT"].timeout_seconds)),
            )
        config.default_bid_qty = int(payload.get("default_bid_qty", config.default_bid_qty)) if isinstance(payload, dict) else config.default_bid_qty
        config.default_ask_qty = int(payload.get("default_ask_qty", config.default_ask_qty)) if isinstance(payload, dict) else config.default_ask_qty
        config.max_queue_depth = int(payload.get("max_queue_depth", config.max_queue_depth)) if isinstance(payload, dict) else config.max_queue_depth
        return config

    def for_exchange(self, exchange: str) -> ExchangeConfig:
        return self.exchange.get(exchange.upper(), self.exchange["DEFAULT"])
