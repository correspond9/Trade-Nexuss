"""
Authoritative Option Chain API Router
Serves frontend from central cache only - no direct Dhan API calls
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.authoritative_option_chain_service import authoritative_option_chain_service

logger = logging.getLogger(__name__)

router = APIRouter()

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
            raise HTTPException(
                status_code=404,
                detail=f"Option chain not found for {underlying} {expiry}"
            )
        
        # Add metadata
        response = {
            "status": "success",
            "data": option_chain,
            "source": "central_cache",
            "timestamp": datetime.now().isoformat(),
            "cache_stats": authoritative_option_chain_service.get_cache_statistics()
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

@router.post("/build/{underlying}")
async def build_option_chain_for_underlying(underlying: str) -> Dict[str, Any]:
    """
    Build complete option chain for an underlying
    This triggers the full flow: expiries → ATM → strikes → REST → cache
    """
    try:
        logger.info(f"🏗️ Building complete option chain for {underlying}")
        
        success = await authoritative_option_chain_service.build_complete_option_chain(underlying)
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to build option chain for {underlying}"
            )
        
        # Get updated statistics
        stats = authoritative_option_chain_service.get_cache_statistics()
        
        return {
            "status": "success",
            "underlying": underlying,
            "message": f"Option chain built successfully for {underlying}",
            "cache_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to build option chain: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/refresh/greeks")
async def refresh_greeks_and_oi() -> Dict[str, Any]:
    """
    Refresh Greeks and OI from REST API
    Periodic refresh every 30-60 seconds
    """
    try:
        logger.info("🔄 Refreshing Greeks and OI...")
        
        success = await authoritative_option_chain_service.refresh_greeks_and_oi()
        
        return {
            "status": "success" if success else "error",
            "message": "Greeks and OI refreshed successfully" if success else "Failed to refresh Greeks and OI",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to refresh Greeks and OI: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/refresh/atm")
async def refresh_atm_strikes() -> Dict[str, Any]:
    """
    Refresh ATM strikes for all underlyings
    Periodic ATM recalculation
    """
    try:
        logger.info("🔄 Refreshing ATM strikes...")
        
        success = await authoritative_option_chain_service.periodic_atm_recalculation()
        
        return {
            "status": "success" if success else "error",
            "message": "ATM strikes refreshed successfully" if success else "Failed to refresh ATM strikes",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to refresh ATM strikes: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

@router.post("/initialize")
async def initialize_service() -> Dict[str, Any]:
    """
    Initialize the authoritative option chain service
    """
    try:
        logger.info("🚀 Initializing authoritative option chain service...")
        
        success = await authoritative_option_chain_service.initialize()
        
        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize option chain service"
            )
        
        return {
            "status": "success",
            "message": "Authoritative option chain service initialized successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to initialize service: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
