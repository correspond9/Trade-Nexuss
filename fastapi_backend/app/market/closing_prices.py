"""
Closing Prices for Option Chain Initialization
Generated for market-closed periods (e.g., Feb 3, 2026)
Expiries are fetched daily from DhanHQ REST API during off-market hours
"""

from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def _fetch_expiries_from_scheduler(underlying: str) -> list:
    """
    Get expiries from daily scheduler cache
    Falls back to hardcoded dates if scheduler not ready
    """
    try:
        from app.schedulers.expiry_refresh_scheduler import get_expiry_scheduler
        scheduler = get_expiry_scheduler()
        expiries = scheduler.get_expiries(underlying)
        if expiries:
            logger.info(f"✅ Using cached expiries for {underlying} from daily scheduler: {expiries[:3]}...")
            return expiries
        else:
            logger.warning(f"⚠️ Scheduler cache empty for {underlying}, using fallback")
            return []
    except Exception as e:
        logger.warning(f"⚠️ Error accessing expiry scheduler for {underlying}: {e}")
        return []


# No hardcoded closing prices; use live sources only.
CLOSING_PRICES = {}

def get_closing_prices() -> dict:
    """Return closing prices for option chain initialization"""
    return CLOSING_PRICES
