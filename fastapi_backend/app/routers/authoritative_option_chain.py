"""
Authoritative Option Chain API Router
Serves frontend from central cache only - no direct Dhan API calls
"""

import logging
import asyncio
import time
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.authoritative_option_chain_service import authoritative_option_chain_service

logger = logging.getLogger(__name__)

router = APIRouter()
_warmup_lock = asyncio.Lock()
_last_warmup_by_underlying: Dict[str, float] = {}
_warmup_cooldown_seconds = 20.0

# STEP 10: SERVE FRONTEND FROM CACHE
@router.get("/live")
async def get_option_chain_live(
    underlying: str = Query(..., description="Underlying symbol (e.g., NIFTY, BANKNIFTY)"),
    expiry: str = Query(..., description="Expiry date (YYYY-MM-DD)")
) -> Dict[str, Any]:
    """
    Get option chain from central cache - frontend reads ONLY from here
    
    Response must come ONLY from option_chain_cache
    """
    try:
        logger.info(f"📊 Serving option chain from cache: {underlying} {expiry}")
        
        # Get from central cache
        option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
        
        if option_chain is None:
            # Guarded on-demand warm-up for cold cache / missing expiry.
            now = time.time()
            last_attempt = _last_warmup_by_underlying.get(underlying, 0.0)
            if now - last_attempt >= _warmup_cooldown_seconds:
                async with _warmup_lock:
                    now_locked = time.time()
                    last_attempt_locked = _last_warmup_by_underlying.get(underlying, 0.0)
                    if now_locked - last_attempt_locked >= _warmup_cooldown_seconds:
                        _last_warmup_by_underlying[underlying] = now_locked
                        try:
                            logger.info(f"♻️ Cache miss for {underlying} {expiry}; running on-demand market-aware warm-up")
                            await asyncio.wait_for(
                                authoritative_option_chain_service.populate_cache_with_market_aware_data(),
                                timeout=3.0,
                            )
                        except asyncio.TimeoutError:
                            logger.warning(f"⚠️ Warm-up timed out for {underlying}; serving cache miss response")
                        except Exception as warmup_error:
                            logger.warning(f"⚠️ Warm-up attempt failed for {underlying}: {warmup_error}")

                option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)

            if option_chain is None:
                try:
                    from app.market.closing_prices import get_closing_prices
                    closing_payload = get_closing_prices() or {}
                    if closing_payload:
                        authoritative_option_chain_service.populate_with_closing_prices_sync(closing_payload)
                        option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
                except Exception as fallback_error:
                    logger.warning(f"⚠️ Closing-price fallback failed for {underlying} {expiry}: {fallback_error}")

            if option_chain is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Option chain not found for {underlying} {expiry}"
                )
        
        try:
            from app.market.live_prices import get_price
            underlying_ltp = get_price(underlying)
        except Exception:
            underlying_ltp = None

        # Add metadata
        response = {
            "status": "success",
            "data": option_chain,
            "source": "central_cache",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": authoritative_option_chain_service.get_cache_statistics(),
            "underlying_ltp": underlying_ltp,
        }
        
        logger.info(f"✅ Served option chain for {underlying} {expiry}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to serve option chain: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/available/underlyings")
async def get_available_underlyings() -> Dict[str, Any]:
    """Get list of available underlyings in cache"""
    try:
        underlyings = authoritative_option_chain_service.get_available_underlyings()
        
        return {
            "status": "success",
            "data": underlyings,
            "count": len(underlyings),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get available underlyings: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/available/expiries")
async def get_available_expiries(
    underlying: str = Query(..., description="Underlying symbol")
) -> Dict[str, Any]:
    """Get list of available expiries for an underlying"""
    try:
        expiries = authoritative_option_chain_service.get_available_expiries(underlying)
        
        return {
            "status": "success",
            "underlying": underlying,
            "data": expiries,
            "count": len(expiries),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get available expiries: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/atm/{underlying}")
async def get_atm_strike(underlying: str) -> Dict[str, Any]:
    """Get current ATM strike for underlying"""
    try:
        atm_strike = authoritative_option_chain_service.get_atm_strike(underlying)
        
        if atm_strike is None:
            raise HTTPException(
                status_code=404,
                detail=f"ATM strike not available for {underlying}"
            )
        
        return {
            "status": "success",
            "underlying": underlying,
            "atm_strike": atm_strike,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get ATM strike: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.get("/cache/stats")
async def get_cache_statistics() -> Dict[str, Any]:
    """Get central cache statistics"""
    try:
        stats = authoritative_option_chain_service.get_cache_statistics()
        
        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get cache statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
