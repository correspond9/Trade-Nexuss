"""
REST API endpoints for two-tier subscription system.
Watchlist, option chains, and subscription status.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, Dict, List
from pydantic import BaseModel
import re

from app.market.watchlist_manager import get_watchlist_manager
from app.market.atm_engine import get_atm_engine
from app.market.subscription_manager import get_subscription_manager
from app.market.ws_manager import get_ws_manager
from app.market.instrument_master.registry import REGISTRY
from app.schedulers.expiry_refresh_scheduler import get_expiry_scheduler
from app.routers.authoritative_option_chain import router as option_chain_router

from datetime import datetime, date
from typing import Optional

router = APIRouter(prefix="/api/v2", tags=["market"])

# ==========================================================
# SECTION: Expiry Normalization Utility
# ==========================================================

def _normalize_expiry(expiry: str) -> Optional[date]:
    """
    Convert expiry string to Python date.
    Supports multiple formats used in exchange data.
    """
    text = (expiry or "").strip().upper()

    for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%b%y", "%d%B%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    return None


# ==========================================================
# SECTION: Request / Response Models
# ==========================================================

class AddWatchlistRequest(BaseModel):
    user_id: int
    symbol: str
    expiry: str
    instrument_type: str = "STOCK_OPTION"
    underlying_ltp: Optional[float] = None


class RemoveWatchlistRequest(BaseModel):
    user_id: int
    symbol: str
    expiry: str


class OptionChainRequest(BaseModel):
    symbol: str
    expiry: str
    underlying_ltp: float


class AdminSubscribeIndicesRequest(BaseModel):
    symbols: Optional[List[str]] = None
    tier: str = "TIER_B"


# ==========================================================
# SECTION: WATCHLIST ENDPOINTS
# ==========================================================

@router.post("/watchlist/add")
async def add_to_watchlist(req: AddWatchlistRequest):
    watchlist_mgr = get_watchlist_manager()
    result = watchlist_mgr.add_to_watchlist(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry,
        instrument_type=req.instrument_type,
        underlying_ltp=req.underlying_ltp
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Failed"))

    return result


@router.post("/watchlist/remove")
async def remove_from_watchlist(req: RemoveWatchlistRequest):
    watchlist_mgr = get_watchlist_manager()
    result = watchlist_mgr.remove_from_watchlist(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/watchlist/{user_id}")
async def get_user_watchlist(user_id: int):
    watchlist_mgr = get_watchlist_manager()
    watchlist = watchlist_mgr.get_user_watchlist(user_id)

    return {
        "user_id": user_id,
        "count": len(watchlist),
        "watchlist": watchlist
    }


# ==========================================================
# SECTION: OPTION CHAIN ENDPOINTS
# ==========================================================

@router.get("/option-chain/{symbol}")
async def get_option_chain(
    symbol: str,
    expiry: str = Query(...),
    underlying_ltp: float = Query(...)
):
    atm_engine = get_atm_engine()

    try:
        chain = atm_engine.generate_chain(
            symbol=symbol,
            expiry=expiry,
            underlying_ltp=underlying_ltp
        )
        return chain
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/option-chain/subscribe")
async def subscribe_option_chain(req: OptionChainRequest):
    atm_engine = get_atm_engine()
    sub_mgr = get_subscription_manager()

    try:
        chain = atm_engine.generate_chain(
            symbol=req.symbol,
            expiry=req.expiry,
            underlying_ltp=req.underlying_ltp,
            force_recalc=True
        )

        strikes = chain["strikes"]
        subscribed = []
        failed = []

        for strike in strikes:

            token_ce = f"{req.symbol}_{req.expiry}_{strike:.0f}CE"
            success, msg, ws_id = sub_mgr.subscribe(
                token=token_ce,
                symbol=req.symbol,
                expiry=req.expiry,
                strike=strike,
                option_type="CE",
                tier="TIER_A"
            )

            if success:
                subscribed.append(token_ce)
            else:
                failed.append(token_ce)

            token_pe = f"{req.symbol}_{req.expiry}_{strike:.0f}PE"
            success, msg, ws_id = sub_mgr.subscribe(
                token=token_pe,
                symbol=req.symbol,
                expiry=req.expiry,
                strike=strike,
                option_type="PE",
                tier="TIER_A"
            )

            if success:
                subscribed.append(token_pe)
            else:
                failed.append(token_pe)

        return {
            "symbol": req.symbol,
            "expiry": req.expiry,
            "option_chain": chain,
            "subscribed": subscribed,
            "failed": failed,
            "total_subscribed": len(subscribed)
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==========================================================
# SECTION: SUBSCRIPTION STATUS
# ==========================================================

@router.get("/subscriptions/status")
async def get_subscription_status():
    sub_mgr = get_subscription_manager()
    ws_mgr = get_ws_manager()

    return {
        "subscriptions": sub_mgr.get_ws_stats(),
        "websocket": ws_mgr.get_status()
    }


# ==========================================================
# SECTION: INCLUDE AUTHORITATIVE OPTION ROUTES
# ==========================================================

router.include_router(option_chain_router, prefix="/options", tags=["option-chain"])


print("[OK] Market API v2 endpoints loaded")
print("[OK] Authoritative option chain routes registered at /api/v2/options/*")
