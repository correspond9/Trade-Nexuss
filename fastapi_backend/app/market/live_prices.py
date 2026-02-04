import threading

# Only track the four Tier-B dashboard instruments.
_DASHBOARD_SYMBOLS = ("NIFTY", "BANKNIFTY", "SENSEX", "CRUDEOIL", "RELIANCE")

prices = {symbol: None for symbol in _DASHBOARD_SYMBOLS}

_lock = threading.Lock()

def update_price(symbol: str, price: float):
    """Update price for a symbol"""
    with _lock:
        prices[symbol] = price

def get_prices():
    """Get all dashboard prices"""
    with _lock:
        return prices.copy()


def get_dashboard_symbols():
    """Return tuple of symbols rendered on the dashboard"""
    return _DASHBOARD_SYMBOLS

def get_price(symbol: str):
    """Get price for a specific symbol"""
    with _lock:
        return prices.get(symbol)
