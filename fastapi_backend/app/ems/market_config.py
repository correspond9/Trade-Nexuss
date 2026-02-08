from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time, datetime
from typing import Dict, List, Set


@dataclass
class ExchangeHours:
    open_time: time
    close_time: time
    working_days: Set[int]  # 0=Mon ... 6=Sun
    force_state: str = "none"  # "none" | "open" | "close"


class MarketConfig:
    def __init__(self) -> None:
        self.exchanges: Dict[str, ExchangeHours] = {
            "NSE": ExchangeHours(time(9, 15), time(15, 31), set([0, 1, 2, 3, 4])),
            "BSE": ExchangeHours(time(9, 15), time(15, 31), set([0, 1, 2, 3, 4])),
            "MCX": ExchangeHours(time(9, 0), time(23, 30), set([0, 1, 2, 3, 4])),
        }

    def get(self) -> Dict[str, Dict]:
        out = {}
        for ex, cfg in self.exchanges.items():
            out[ex] = {
                "open_time": cfg.open_time.strftime("%H:%M"),
                "close_time": cfg.close_time.strftime("%H:%M"),
                "working_days": sorted(list(cfg.working_days)),
                "force_state": cfg.force_state,
            }
        return out

    def update(self, payload: Dict[str, Dict]) -> None:
        for ex, data in payload.items():
            if ex not in self.exchanges:
                continue
            cfg = self.exchanges[ex]
            open_txt = data.get("open_time")
            close_txt = data.get("close_time")
            days = data.get("working_days")
            if isinstance(open_txt, str):
                try:
                    h, m = [int(x) for x in open_txt.split(":")]
                    cfg.open_time = time(h, m)
                except Exception:
                    pass
            if isinstance(close_txt, str):
                try:
                    h, m = [int(x) for x in close_txt.split(":")]
                    cfg.close_time = time(h, m)
                except Exception:
                    pass
            if isinstance(days, (list, set)):
                cleaned = set([int(d) for d in days if isinstance(d, int) and 0 <= d <= 6])
                if cleaned:
                    cfg.working_days = cleaned

    def set_force(self, exchange: str, state: str) -> None:
        if exchange in self.exchanges and state in {"none", "open", "close"}:
            self.exchanges[exchange].force_state = state

    def is_market_open(self, exchange: str, now: datetime | None = None) -> bool:
        if exchange not in self.exchanges:
            return False
        cfg = self.exchanges[exchange]
        if cfg.force_state == "open":
            return True
        if cfg.force_state == "close":
            return False
        if not now:
            now = datetime.now()
        if now.weekday() not in cfg.working_days:
            return False
        current = now.time()
        return cfg.open_time <= current <= cfg.close_time


market_config = MarketConfig()
