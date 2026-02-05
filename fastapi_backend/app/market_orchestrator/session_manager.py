"""Exchange session manager for NSE/BSE/MCX."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Dict


@dataclass(frozen=True)
class SessionWindow:
    start: time
    end: time

    def contains(self, now: time) -> bool:
        if self.start <= self.end:
            return self.start <= now <= self.end
        return now >= self.start or now <= self.end


class SessionManager:
    def __init__(self, schedules: Dict[str, Dict[str, SessionWindow]] | None = None) -> None:
        if schedules is None:
            schedules = {
                "NSE": {"regular": SessionWindow(time(9, 15), time(15, 30))},
                "BSE": {"regular": SessionWindow(time(9, 15), time(15, 30))},
                "MCX": {
                    "morning": SessionWindow(time(9, 0), time(17, 0)),
                    "evening": SessionWindow(time(17, 0), time(23, 30)),
                },
            }
        self.schedules = schedules

    def _now(self) -> time:
        return datetime.now().time()

    def is_market_open(self, exchange: str) -> bool:
        exch = exchange.upper()
        now = self._now()
        if exch in ("NSE", "BSE"):
            return self.schedules[exch]["regular"].contains(now)
        if exch == "MCX":
            return self.schedules["MCX"]["morning"].contains(now) or self.schedules["MCX"]["evening"].contains(now)
        return False

    def is_market_closed(self, exchange: str) -> bool:
        return not self.is_market_open(exchange)

    def is_evening_session_mcx(self) -> bool:
        now = self._now()
        return self.schedules["MCX"]["evening"].contains(now)
