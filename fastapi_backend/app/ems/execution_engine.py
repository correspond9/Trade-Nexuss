
from .exchange_clock import is_market_open

def execute(order):
    if not is_market_open(order["exchange"]):
        return {"status":"PENDING_AMO"}
    return {"status":"FILLED"}
