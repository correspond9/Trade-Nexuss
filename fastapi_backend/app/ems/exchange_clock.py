
# Exchange timings (simplified)
from datetime import datetime, time
from zoneinfo import ZoneInfo
import os

_FORCE_MARKET_OPEN = os.getenv("FORCE_MARKET_OPEN", "true").strip().lower() in {"1", "true", "yes", "on"}
_IST = ZoneInfo("Asia/Kolkata")


def is_market_open(exchange):
    if _FORCE_MARKET_OPEN:
        return True
    now = datetime.now(_IST).time()
    if exchange in ["NSE", "BSE"]:
        return time(9, 15) <= now <= time(15, 30)
    if exchange == "MCX":
        return time(9, 0) <= now <= time(23, 30)
    return False
