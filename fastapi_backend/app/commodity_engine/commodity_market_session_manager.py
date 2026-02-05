"""MCX market session manager with morning/evening sessions."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time


@dataclass
class MarketSessionState:
    is_open: bool = False
    last_transition: str = ""


class CommodityMarketSessionManager:
    def __init__(self) -> None:
        self.morning_start = time(9, 0)
        self.morning_end = time(17, 0)
        self.evening_start = time(17, 0)
        self.evening_end = time(23, 30)
        self.state = MarketSessionState()

    def _is_in_session(self, now: datetime) -> bool:
        current = now.time()
        if self.morning_start <= current < self.morning_end:
            return True
        if self.evening_start <= current < self.evening_end:
            return True
        return False

    def is_open(self, now: datetime | None = None) -> bool:
        if not now:
            now = datetime.now()
        return self._is_in_session(now)

    def check_transition(self, now: datetime | None = None) -> bool:
        if not now:
            now = datetime.now()
        open_now = self._is_in_session(now)
        if open_now and not self.state.is_open:
            self.state.is_open = True
            self.state.last_transition = now.isoformat()
            return True
        if not open_now and self.state.is_open:
            self.state.is_open = False
            self.state.last_transition = now.isoformat()
        return False


commodity_market_session_manager = CommodityMarketSessionManager()
