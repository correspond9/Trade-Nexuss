
# Exchange timings (simplified)
from datetime import datetime
from zoneinfo import ZoneInfo
from app.ems.market_config import market_config

_IST = ZoneInfo("Asia/Kolkata")


def is_market_open(exchange):
    now = datetime.now(_IST)
    return market_config.is_market_open(exchange, now)
