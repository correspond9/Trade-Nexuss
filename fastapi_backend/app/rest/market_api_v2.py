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

router = APIRouter(prefix="/api/v2", tags=["market"])


# ==========================================================
# SECTION 1 — Expiry Normalization Utility
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
# SECTION 2 — Request Models
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
# SECTION 3 — WATCHLIST ENDPOINTS
# ==========================================================

@router.post("/watchlist/add")
async def add_to_watchlist(req: AddWatchlistRequest):
    mgr = get_watchlist_manager()

    result = mgr.add(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry,
        instrument_type=req.instrument_type,
        underlying_ltp=req.underlying_ltp,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.post("/watchlist/remove")
async def remove_from_watchlist(req: RemoveWatchlistRequest):
    mgr = get_watchlist_manager()

    result = mgr.remove(
        user_id=req.user_id,
        symbol=req.symbol,
        expiry=req.expiry,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/watchlist/{user_id}")
async def get_user_watchlist(user_id: int):
    mgr = get_watchlist_manager()
    return mgr.get(user_id)


# ==========================================================
# SECTION 4 — OPTION CHAIN
# ==========================================================

@router.post("/option-chain")
async def get_option_chain(req: OptionChainRequest):
    atm_engine = get_atm_engine()

    return atm_engine.build_chain(
        symbol=req.symbol,
        expiry=req.expiry,
        underlying_ltp=req.underlying_ltp,
    )


# ==========================================================
# SECTION 5 — SUBSCRIPTIONS
# ==========================================================

@router.post("/subscribe")
async def subscribe_option_chain(req: AdminSubscribeIndicesRequest):
    sub_mgr = get_subscription_manager()

    return sub_mgr.subscribe_indices(
        symbols=req.symbols,
        tier=req.tier,
    )


@router.get("/subscriptions/status")
async def get_subscription_status():
    sub_mgr = get_subscription_manager()
    ws_mgr = get_ws_manager()

    return {
        "subscriptions": sub_mgr.get_ws_stats(),
        "websocket": ws_mgr.get_status()
    }


# ==========================================================
# SECTION 6 — INCLUDE AUTHORITATIVE ROUTES
# ==========================================================

router.include_router(
    option_chain_router,
    prefix="/options",
    tags=["option-chain"]
)

print("[OK] Market API v2 endpoints loaded")
print("[OK] Authoritative option chain routes registered at /api/v2/options/*")
