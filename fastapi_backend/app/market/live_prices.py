import threading

# Only track the four Tier-B dashboard instruments.
_DASHBOARD_SYMBOLS = ("NIFTY", "BANKNIFTY", "SENSEX", "CRUDEOIL", "RELIANCE")

prices = {symbol: None for symbol in _DASHBOARD_SYMBOLS}

_lock = threading.Lock()

def update_price(symbol: str, price: float):
    """Update price for a symbol"""
    with _lock:
        # ✨ NEW: Handle both underlying and option symbols
        # Extract underlying symbol from option tokens (e.g., CE_NIFTY_... -> NIFTY)
        if "_" in symbol:
            # This is an option token, extract underlying
            parts = symbol.split("_")
            if len(parts) >= 2:
                underlying = parts[1]  # NIFTY from CE_NIFTY_...
                if underlying in _DASHBOARD_SYMBOLS:
                    prices[underlying] = price
                    print(f"[PRICE] Updated {underlying} from option {symbol}: {price}")
        else:
            # This is a direct underlying symbol
            if symbol in _DASHBOARD_SYMBOLS:
                prices[symbol] = price
                print(f"[PRICE] Updated {symbol}: {price}")

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
