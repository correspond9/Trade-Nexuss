
# Exchange timings (simplified)
from datetime import datetime, time

def is_market_open(exchange):
    now = datetime.now().time()
    if exchange in ["NSE","BSE"]:
        return time(9,15) <= now <= time(15,30)
    if exchange == "MCX":
        return time(9,0) <= now <= time(23,30)
    return False
