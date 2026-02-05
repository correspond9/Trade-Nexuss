"""Latency model for execution simulation."""
from __future__ import annotations

import random
from typing import Dict

from app.execution_simulator.execution_config import ExecutionConfig


class LatencyModel:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def sample_latency_ms(self, exchange: str, user_id: int | None = None) -> int:
        cfg = self.config.for_exchange(exchange)
        low, high = cfg.latency_ms
        return int(random.randint(low, high))
