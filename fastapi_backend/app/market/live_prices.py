import threading
import logging

# Only track the four Tier-B dashboard instruments.
_DASHBOARD_SYMBOLS = ("NIFTY", "BANKNIFTY", "SENSEX", "CRUDEOIL", "RELIANCE")
logger = logging.getLogger("trading_nexus.market.live_prices")

prices = {symbol: None for symbol in _DASHBOARD_SYMBOLS}

_lock = threading.Lock()

def _normalize_symbol(symbol: str) -> str:
    if not symbol:
        return symbol
    text = symbol.strip().upper()
    if text in {"NIFTY 50", "NIFTY50"}:
        return "NIFTY"
    if text in {"BANK NIFTY", "NIFTY BANK", "BANKNIFTY"}:
        return "BANKNIFTY"
    if text in {"SENSEX", "BSE SENSEX", "S&P BSE SENSEX", "SENSEX 50"}:
        return "SENSEX"
    return text


def update_price(symbol: str, price: float):
    """Update price for a symbol"""
    with _lock:
        # Handle both underlying and option symbols.
        if "_" in symbol:
            parts = symbol.split("_")
            if len(parts) >= 2:
                underlying = _normalize_symbol(parts[1])
                prices[underlying] = price
                logger.debug("[PRICE] Updated %s from option %s: %s", underlying, symbol, price)
            return

        normalized = _normalize_symbol(symbol)
        prices[normalized] = price
        logger.debug("[PRICE] Updated %s: %s", normalized, price)

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
        normalized = _normalize_symbol(symbol)
        return prices.get(normalized)
