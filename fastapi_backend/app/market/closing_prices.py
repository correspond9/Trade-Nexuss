"""
Closing Prices for Option Chain Initialization
Generated for market-closed periods (e.g., Feb 3, 2026)
Expiries are fetched daily from DhanHQ REST API during off-market hours
"""

from datetime import datetime
import logging
import math

logger = logging.getLogger(__name__)


def _fetch_expiries_from_scheduler(underlying: str) -> list:
    try:
        from app.schedulers.expiry_refresh_scheduler import get_expiry_scheduler
        scheduler = get_expiry_scheduler()
        expiries = scheduler.get_expiries(underlying)
        return expiries or []
    except Exception:
        return []


def _resolve_underlying_price(symbol: str) -> float:
    try:
        from app.market.live_prices import get_price
        p = get_price(symbol)
        if p:
            return float(p)
    except Exception:
        pass
    defaults = {"NIFTY": 25300.0, "BANKNIFTY": 44500.0, "SENSEX": 84000.0}
    return defaults.get(symbol, 0.0)


def _build_strikes(symbol: str, price: float, strike_interval: float, count: int) -> list:
    if strike_interval <= 0 or price <= 0 or count <= 0:
        return []
    atm = round(price / strike_interval) * strike_interval
    half = count // 2
    return [atm + strike_interval * i for i in range(-half, half + 1)]


def _premium_model(symbol: str, distance_steps: float) -> float:
    bases = {"NIFTY": 150.0, "BANKNIFTY": 250.0, "SENSEX": 300.0}
    decays = {"NIFTY": 6.0, "BANKNIFTY": 10.0, "SENSEX": 12.0}
    base = bases.get(symbol, 100.0)
    decay = decays.get(symbol, 5.0)
    v = base - decay * distance_steps
    if v < 0.5:
        v = 0.5
    return round(v, 2)


def _build_closing_snapshot_for(symbol: str) -> dict:
    try:
        from app.services.authoritative_option_chain_service import authoritative_option_chain_service
        price = _resolve_underlying_price(symbol)
        interval = float(authoritative_option_chain_service.index_options.get(symbol, {}).get("strike_interval") or 0.0)
        strikes = _build_strikes(symbol, price, interval, 25)
        expiries = _fetch_expiries_from_scheduler(symbol)
        if not expiries:
            expiries = ["CURRENT"]
        closing = {}
        for expiry in expiries[:2]:
            m = {}
            for s in strikes:
                steps = abs((s - round(price / interval) * interval) / interval) if interval else 0.0
                ce = _premium_model(symbol, steps)
                pe = _premium_model(symbol, steps)
                m[str(float(s))] = {"CE": ce, "PE": pe}
            closing[expiry] = m
        return {
            "expiries": expiries,
            "closing_prices": closing,
            "current_price": price,
        }
    except Exception:
        return {}

def get_closing_prices() -> dict:
    """Return closing prices for option chain initialization"""
    data = {}
    for sym in ("NIFTY", "BANKNIFTY", "SENSEX"):
        snap = _build_closing_snapshot_for(sym)
        if snap:
            data[sym] = snap
    return data
