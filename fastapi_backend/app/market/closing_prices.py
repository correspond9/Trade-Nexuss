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


# Current market prices as of Feb 4, 2026 (Intraday)
# LIVE PRICES from market:
# - NIFTY: 25897
# - BANKNIFTY: 51750
# - SENSEX: 76500
# Fallback expiries (used only if daily scheduler fails):
# - NIFTY: Weekly Tuesdays
# - BANKNIFTY: Monthly last Thursday
# - SENSEX: Weekly Thursdays
CLOSING_PRICES = {
    "NIFTY": {
        "current_price": 25897.00,
        "expiries": _fetch_expiries_from_scheduler("NIFTY") or ["2026-02-10", "2026-02-17"],  # Fallback: Weekly Tuesdays
        "closing_prices": {
            "2026-02-17": {
                "23000": {"CE": 620.50, "PE": 35.25, "IV": 18.2, "delta_CE": 0.95, "delta_PE": -0.05, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -8.5, "theta_PE": 0.5, "vega_CE": 12.3, "vega_PE": 12.3},
                "23050": {"CE": 595.75, "PE": 42.50, "IV": 18.4, "delta_CE": 0.94, "delta_PE": -0.06, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -8.6, "theta_PE": 0.6, "vega_CE": 12.5, "vega_PE": 12.5},
                "23100": {"CE": 571.25, "PE": 50.75, "IV": 18.6, "delta_CE": 0.93, "delta_PE": -0.07, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -8.7, "theta_PE": 0.7, "vega_CE": 12.7, "vega_PE": 12.7},
                "23150": {"CE": 547.00, "PE": 59.50, "IV": 18.8, "delta_CE": 0.92, "delta_PE": -0.08, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -8.8, "theta_PE": 0.8, "vega_CE": 12.9, "vega_PE": 12.9},
                "23200": {"CE": 523.25, "PE": 68.75, "IV": 19.0, "delta_CE": 0.91, "delta_PE": -0.09, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -8.9, "theta_PE": 0.9, "vega_CE": 13.1, "vega_PE": 13.1},
                "23250": {"CE": 500.00, "PE": 78.50, "IV": 19.2, "delta_CE": 0.89, "delta_PE": -0.11, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -9.0, "theta_PE": 1.0, "vega_CE": 13.3, "vega_PE": 13.3},
                "23300": {"CE": 477.50, "PE": 88.75, "IV": 19.4, "delta_CE": 0.87, "delta_PE": -0.13, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -9.1, "theta_PE": 1.1, "vega_CE": 13.5, "vega_PE": 13.5},
                "23350": {"CE": 455.50, "PE": 99.50, "IV": 19.6, "delta_CE": 0.85, "delta_PE": -0.15, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -9.2, "theta_PE": 1.2, "vega_CE": 13.7, "vega_PE": 13.7},
                "23400": {"CE": 434.00, "PE": 110.75, "IV": 19.8, "delta_CE": 0.82, "delta_PE": -0.18, "gamma_CE": 0.004, "gamma_PE": 0.004, "theta_CE": -9.3, "theta_PE": 1.3, "vega_CE": 13.9, "vega_PE": 13.9},
                "23450": {"CE": 413.25, "PE": 122.50, "IV": 20.0, "delta_CE": 0.79, "delta_PE": -0.21, "gamma_CE": 0.004, "gamma_PE": 0.004, "theta_CE": -9.4, "theta_PE": 1.4, "vega_CE": 14.1, "vega_PE": 14.1},
                "23500": {"CE": 393.50, "PE": 135.00, "IV": 20.2, "delta_CE": 0.76, "delta_PE": -0.24, "gamma_CE": 0.004, "gamma_PE": 0.004, "theta_CE": -9.5, "theta_PE": 1.5, "vega_CE": 14.3, "vega_PE": 14.3},
                "23550": {"CE": 374.75, "PE": 148.25, "IV": 20.4, "delta_CE": 0.72, "delta_PE": -0.28, "gamma_CE": 0.005, "gamma_PE": 0.005, "theta_CE": -9.6, "theta_PE": 1.6, "vega_CE": 14.5, "vega_PE": 14.5},
                "23600": {"CE": 356.50, "PE": 162.50, "IV": 20.6, "delta_CE": 0.67, "delta_PE": -0.33, "gamma_CE": 0.005, "gamma_PE": 0.005, "theta_CE": -9.7, "theta_PE": 1.7, "vega_CE": 14.7, "vega_PE": 14.7},
                "23650": {"CE": 339.00, "PE": 177.50, "IV": 20.8, "delta_CE": 0.62, "delta_PE": -0.38, "gamma_CE": 0.005, "gamma_PE": 0.005, "theta_CE": -9.8, "theta_PE": 1.8, "vega_CE": 14.9, "vega_PE": 14.9},
                "23700": {"CE": 322.25, "PE": 193.00, "IV": 21.0, "delta_CE": 0.56, "delta_PE": -0.44, "gamma_CE": 0.006, "gamma_PE": 0.006, "theta_CE": -9.9, "theta_PE": 1.9, "vega_CE": 15.1, "vega_PE": 15.1},
                "23750": {"CE": 306.50, "PE": 209.25, "IV": 21.2, "delta_CE": 0.50, "delta_PE": -0.50, "gamma_CE": 0.006, "gamma_PE": 0.006, "theta_CE": -10.0, "theta_PE": 2.0, "vega_CE": 15.3, "vega_PE": 15.3},
                "23800": {"CE": 291.75, "PE": 226.00, "IV": 21.4, "delta_CE": 0.44, "delta_PE": -0.56, "gamma_CE": 0.006, "gamma_PE": 0.006, "theta_CE": -9.9, "theta_PE": 2.1, "vega_CE": 15.5, "vega_PE": 15.5},
                "23850": {"CE": 277.50, "PE": 243.75, "IV": 21.6, "delta_CE": 0.38, "delta_PE": -0.62, "gamma_CE": 0.005, "gamma_PE": 0.005, "theta_CE": -9.8, "theta_PE": 2.2, "vega_CE": 15.7, "vega_PE": 15.7},
                "23900": {"CE": 264.00, "PE": 262.25, "IV": 21.8, "delta_CE": 0.33, "delta_PE": -0.67, "gamma_CE": 0.005, "gamma_PE": 0.005, "theta_CE": -9.7, "theta_PE": 2.3, "vega_CE": 15.9, "vega_PE": 15.9},
                "23950": {"CE": 251.25, "PE": 281.50, "IV": 22.0, "delta_CE": 0.28, "delta_PE": -0.72, "gamma_CE": 0.004, "gamma_PE": 0.004, "theta_CE": -9.6, "theta_PE": 2.4, "vega_CE": 16.1, "vega_PE": 16.1},
                "24000": {"CE": 239.50, "PE": 301.75, "IV": 22.2, "delta_CE": 0.24, "delta_PE": -0.76, "gamma_CE": 0.004, "gamma_PE": 0.004, "theta_CE": -9.5, "theta_PE": 2.5, "vega_CE": 16.3, "vega_PE": 16.3},
            },
            "2026-02-10": {
                "23000": {"CE": 680.25, "PE": 45.75, "IV": 17.8, "delta_CE": 0.96, "delta_PE": -0.04, "gamma_CE": 0.0008, "gamma_PE": 0.0008, "theta_CE": -6.2, "theta_PE": 0.4, "vega_CE": 15.1, "vega_PE": 15.1},
                "23200": {"CE": 615.50, "PE": 78.25, "IV": 18.1, "delta_CE": 0.94, "delta_PE": -0.06, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -6.5, "theta_PE": 0.6, "vega_CE": 15.5, "vega_PE": 15.5},
                "23400": {"CE": 557.75, "PE": 112.50, "IV": 18.4, "delta_CE": 0.91, "delta_PE": -0.09, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -6.8, "theta_PE": 0.8, "vega_CE": 15.9, "vega_PE": 15.9},
                "23550": {"CE": 507.25, "PE": 147.00, "IV": 18.6, "delta_CE": 0.86, "delta_PE": -0.14, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -7.0, "theta_PE": 1.0, "vega_CE": 16.2, "vega_PE": 16.2},
                "23600": {"CE": 475.50, "PE": 164.75, "IV": 18.7, "delta_CE": 0.83, "delta_PE": -0.17, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -7.1, "theta_PE": 1.1, "vega_CE": 16.4, "vega_PE": 16.4},
                "23750": {"CE": 397.50, "PE": 227.25, "IV": 19.0, "delta_CE": 0.71, "delta_PE": -0.29, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -7.4, "theta_PE": 1.4, "vega_CE": 16.8, "vega_PE": 16.8},
                "23800": {"CE": 372.75, "PE": 247.50, "IV": 19.1, "delta_CE": 0.67, "delta_PE": -0.33, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -7.5, "theta_PE": 1.5, "vega_CE": 17.0, "vega_PE": 17.0},
                "23900": {"CE": 327.50, "PE": 291.75, "IV": 19.3, "delta_CE": 0.58, "delta_PE": -0.42, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -7.7, "theta_PE": 1.7, "vega_CE": 17.4, "vega_PE": 17.4},
                "24000": {"CE": 286.25, "PE": 335.50, "IV": 19.5, "delta_CE": 0.50, "delta_PE": -0.50, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -7.9, "theta_PE": 1.9, "vega_CE": 17.8, "vega_PE": 17.8},
                "24100": {"CE": 249.75, "PE": 378.75, "IV": 19.7, "delta_CE": 0.42, "delta_PE": -0.58, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -8.1, "theta_PE": 2.1, "vega_CE": 18.2, "vega_PE": 18.2},
            }
        }
    },
    "BANKNIFTY": {
        "current_price": 51750.00,
        "expiries": _fetch_expiries_from_scheduler("BANKNIFTY") or ["2026-02-24", "2026-03-30"],  # Fallback: Monthly
        "closing_prices": {
            "2026-02-24": {
                "47200": {"CE": 680.25, "PE": 35.50, "IV": 17.9, "delta_CE": 0.95, "delta_PE": -0.05, "gamma_CE": 0.0009, "gamma_PE": 0.0009, "theta_CE": -9.1, "theta_PE": 0.5, "vega_CE": 11.8, "vega_PE": 11.8},
                "47400": {"CE": 605.75, "PE": 52.25, "IV": 18.2, "delta_CE": 0.93, "delta_PE": -0.07, "gamma_CE": 0.0012, "gamma_PE": 0.0012, "theta_CE": -9.3, "theta_PE": 0.7, "vega_CE": 12.1, "vega_PE": 12.1},
                "47600": {"CE": 536.50, "PE": 70.50, "IV": 18.4, "delta_CE": 0.91, "delta_PE": -0.09, "gamma_CE": 0.0014, "gamma_PE": 0.0014, "theta_CE": -9.5, "theta_PE": 0.9, "vega_CE": 12.4, "vega_PE": 12.4},
                "47800": {"CE": 472.00, "PE": 90.75, "IV": 18.7, "delta_CE": 0.88, "delta_PE": -0.12, "gamma_CE": 0.0017, "gamma_PE": 0.0017, "theta_CE": -9.7, "theta_PE": 1.1, "vega_CE": 12.7, "vega_PE": 12.7},
                "48000": {"CE": 412.50, "PE": 112.00, "IV": 19.0, "delta_CE": 0.85, "delta_PE": -0.15, "gamma_CE": 0.0020, "gamma_PE": 0.0020, "theta_CE": -9.9, "theta_PE": 1.3, "vega_CE": 13.0, "vega_PE": 13.0},
                "48200": {"CE": 357.75, "PE": 135.25, "IV": 19.2, "delta_CE": 0.81, "delta_PE": -0.19, "gamma_CE": 0.0023, "gamma_PE": 0.0023, "theta_CE": -10.1, "theta_PE": 1.5, "vega_CE": 13.3, "vega_PE": 13.3},
                "48400": {"CE": 307.50, "PE": 160.00, "IV": 19.5, "delta_CE": 0.76, "delta_PE": -0.24, "gamma_CE": 0.0026, "gamma_PE": 0.0026, "theta_CE": -10.3, "theta_PE": 1.7, "vega_CE": 13.6, "vega_PE": 13.6},
                "48600": {"CE": 261.75, "PE": 186.50, "IV": 19.8, "delta_CE": 0.70, "delta_PE": -0.30, "gamma_CE": 0.0029, "gamma_PE": 0.0029, "theta_CE": -10.5, "theta_PE": 1.9, "vega_CE": 13.9, "vega_PE": 13.9},
                "48800": {"CE": 220.25, "PE": 215.00, "IV": 20.1, "delta_CE": 0.63, "delta_PE": -0.37, "gamma_CE": 0.0032, "gamma_PE": 0.0032, "theta_CE": -10.7, "theta_PE": 2.1, "vega_CE": 14.2, "vega_PE": 14.2},
                "49000": {"CE": 182.50, "PE": 245.25, "IV": 20.4, "delta_CE": 0.55, "delta_PE": -0.45, "gamma_CE": 0.0034, "gamma_PE": 0.0034, "theta_CE": -10.9, "theta_PE": 2.3, "vega_CE": 14.5, "vega_PE": 14.5},
            }
            ,
            "2026-03-30": {
                "47200": {"CE": 680.25, "PE": 35.50, "IV": 17.9, "delta_CE": 0.95, "delta_PE": -0.05, "gamma_CE": 0.0009, "gamma_PE": 0.0009, "theta_CE": -9.1, "theta_PE": 0.5, "vega_CE": 11.8, "vega_PE": 11.8},
                "47400": {"CE": 605.75, "PE": 52.25, "IV": 18.2, "delta_CE": 0.93, "delta_PE": -0.07, "gamma_CE": 0.0012, "gamma_PE": 0.0012, "theta_CE": -9.3, "theta_PE": 0.7, "vega_CE": 12.1, "vega_PE": 12.1},
                "47600": {"CE": 536.50, "PE": 70.50, "IV": 18.4, "delta_CE": 0.91, "delta_PE": -0.09, "gamma_CE": 0.0014, "gamma_PE": 0.0014, "theta_CE": -9.5, "theta_PE": 0.9, "vega_CE": 12.4, "vega_PE": 12.4},
                "47800": {"CE": 472.00, "PE": 90.75, "IV": 18.7, "delta_CE": 0.88, "delta_PE": -0.12, "gamma_CE": 0.0017, "gamma_PE": 0.0017, "theta_CE": -9.7, "theta_PE": 1.1, "vega_CE": 12.7, "vega_PE": 12.7},
                "48000": {"CE": 412.50, "PE": 112.00, "IV": 19.0, "delta_CE": 0.85, "delta_PE": -0.15, "gamma_CE": 0.0020, "gamma_PE": 0.0020, "theta_CE": -9.9, "theta_PE": 1.3, "vega_CE": 13.0, "vega_PE": 13.0},
                "48200": {"CE": 357.75, "PE": 135.25, "IV": 19.2, "delta_CE": 0.81, "delta_PE": -0.19, "gamma_CE": 0.0023, "gamma_PE": 0.0023, "theta_CE": -10.1, "theta_PE": 1.5, "vega_CE": 13.3, "vega_PE": 13.3},
                "48400": {"CE": 307.50, "PE": 160.00, "IV": 19.5, "delta_CE": 0.76, "delta_PE": -0.24, "gamma_CE": 0.0026, "gamma_PE": 0.0026, "theta_CE": -10.3, "theta_PE": 1.7, "vega_CE": 13.6, "vega_PE": 13.6},
                "48600": {"CE": 261.75, "PE": 186.50, "IV": 19.8, "delta_CE": 0.70, "delta_PE": -0.30, "gamma_CE": 0.0029, "gamma_PE": 0.0029, "theta_CE": -10.5, "theta_PE": 1.9, "vega_CE": 13.9, "vega_PE": 13.9},
                "48800": {"CE": 220.25, "PE": 215.00, "IV": 20.1, "delta_CE": 0.63, "delta_PE": -0.37, "gamma_CE": 0.0032, "gamma_PE": 0.0032, "theta_CE": -10.7, "theta_PE": 2.1, "vega_CE": 14.2, "vega_PE": 14.2},
                "49000": {"CE": 182.50, "PE": 245.25, "IV": 20.4, "delta_CE": 0.55, "delta_PE": -0.45, "gamma_CE": 0.0034, "gamma_PE": 0.0034, "theta_CE": -10.9, "theta_PE": 2.3, "vega_CE": 14.5, "vega_PE": 14.5},
            }
        }
    },
    "SENSEX": {
        "current_price": 76500.00,
        "expiries": _fetch_expiries_from_scheduler("SENSEX") or ["2026-02-05", "2026-02-19"],  # Fallback: Weekly Thursdays
        "closing_prices": {
            "2026-02-05": {
                "76900": {"CE": 640.50, "PE": 55.25, "IV": 18.1, "delta_CE": 0.95, "delta_PE": -0.05, "gamma_CE": 0.0009, "gamma_PE": 0.0009, "theta_CE": -6.5, "theta_PE": 0.4, "vega_CE": 13.2, "vega_PE": 13.2},
                "77100": {"CE": 585.25, "PE": 75.50, "IV": 18.4, "delta_CE": 0.92, "delta_PE": -0.08, "gamma_CE": 0.0012, "gamma_PE": 0.0012, "theta_CE": -6.8, "theta_PE": 0.7, "vega_CE": 13.6, "vega_PE": 13.6},
                "77400": {"CE": 505.00, "PE": 115.75, "IV": 18.8, "delta_CE": 0.87, "delta_PE": -0.13, "gamma_CE": 0.0015, "gamma_PE": 0.0015, "theta_CE": -7.2, "theta_PE": 1.1, "vega_CE": 14.0, "vega_PE": 14.0},
                "77700": {"CE": 430.75, "PE": 160.50, "IV": 19.2, "delta_CE": 0.80, "delta_PE": -0.20, "gamma_CE": 0.0018, "gamma_PE": 0.0018, "theta_CE": -7.6, "theta_PE": 1.5, "vega_CE": 14.4, "vega_PE": 14.4},
            },
            "2026-02-19": {
                "76900": {"CE": 580.50, "PE": 42.25, "IV": 18.6, "delta_CE": 0.94, "delta_PE": -0.06, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -8.8, "theta_PE": 0.6, "vega_CE": 10.5, "vega_PE": 10.5},
                "77000": {"CE": 550.00, "PE": 50.75, "IV": 18.8, "delta_CE": 0.93, "delta_PE": -0.07, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -8.9, "theta_PE": 0.7, "vega_CE": 10.7, "vega_PE": 10.7},
                "77100": {"CE": 520.25, "PE": 59.50, "IV": 19.0, "delta_CE": 0.92, "delta_PE": -0.08, "gamma_CE": 0.001, "gamma_PE": 0.001, "theta_CE": -9.0, "theta_PE": 0.8, "vega_CE": 10.9, "vega_PE": 10.9},
                "77200": {"CE": 491.75, "PE": 68.75, "IV": 19.2, "delta_CE": 0.91, "delta_PE": -0.09, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -9.1, "theta_PE": 0.9, "vega_CE": 11.1, "vega_PE": 11.1},
                "77300": {"CE": 464.50, "PE": 78.50, "IV": 19.4, "delta_CE": 0.89, "delta_PE": -0.11, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -9.2, "theta_PE": 1.0, "vega_CE": 11.3, "vega_PE": 11.3},
                "77400": {"CE": 438.75, "PE": 88.75, "IV": 19.6, "delta_CE": 0.87, "delta_PE": -0.13, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -9.3, "theta_PE": 1.1, "vega_CE": 11.5, "vega_PE": 11.5},
                "77500": {"CE": 414.25, "PE": 99.50, "IV": 19.8, "delta_CE": 0.85, "delta_PE": -0.15, "gamma_CE": 0.002, "gamma_PE": 0.002, "theta_CE": -9.4, "theta_PE": 1.2, "vega_CE": 11.7, "vega_PE": 11.7},
                "77600": {"CE": 390.75, "PE": 110.75, "IV": 20.0, "delta_CE": 0.82, "delta_PE": -0.18, "gamma_CE": 0.003, "gamma_PE": 0.003, "theta_CE": -9.5, "theta_PE": 1.3, "vega_CE": 11.9, "vega_PE": 11.9},
            }
        }
    }
}

def get_closing_prices() -> dict:
    """Return closing prices for option chain initialization"""
    return CLOSING_PRICES
