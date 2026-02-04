"""
Instrument Subscription Router
API endpoints for instrument universe management and search functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.database import get_db
from app.services.instrument_subscription_service import instrument_subscription_service

router = APIRouter()

@router.post("/simple-test")
async def simple_test():
    """Simple test to isolate coroutine issues"""
    try:
        from app.services.instrument_subscription_service import instrument_subscription_service
        
        # Test 1: Check approved universe
        universe = instrument_subscription_service.approved_universe
        logger.info(f"Universe type: {type(universe)}")
        logger.info(f"Index options type: {type(universe.get('index_options', {}))}")
        
        # Test 2: Try iterating
        index_options = universe.get('index_options', {})
        logger.info(f"Index options items: {list(index_options.items())}")
        
        # Test 3: Try getting ATM for one symbol
        atm = await instrument_subscription_service._get_current_atm_strike("NIFTY 50")
        logger.info(f"ATM result: {atm}")
        
        return {
            "status": "success",
            "universe_keys": list(universe.keys()),
            "index_options_keys": list(index_options.keys()),
            "atm": atm
        }
        
    except Exception as e:
        import traceback
        logger.error(f"Simple test error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/debug-test")
async def debug_test(
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to test individual methods"""
    try:
        # Test getting ATM strike for NIFTY 50
        atm_strike = await instrument_subscription_service._get_current_atm_strike("NIFTY 50")
        
        # Test generating expiries
        expiries = await instrument_subscription_service._generate_expiries(3)
        
        # Test generating strike range
        strikes = instrument_subscription_service._generate_strike_range(19750.0, 5)
        
        return {
            "status": "success",
            "atm_strike": atm_strike,
            "expiries": expiries,
            "strikes_count": len(strikes),
            "sample_strikes": strikes[:5]
        }
        
    except Exception as e:
        import traceback
        return {
            "status": "error", 
            "error": str(e),
            "traceback": traceback.format_exc()
        }

@router.post("/generate-universe")
async def generate_instrument_universe(
    db: AsyncSession = Depends(get_db)
):
    """
    Generate the complete instrument universe as per DhanHQ compliance
    This should be called once at system startup or when refreshing the universe
    """
    try:
        success = await instrument_subscription_service.generate_instrument_universe()
        
        if success:
            stats = instrument_subscription_service.get_subscription_stats()
            return {
                "status": "success",
                "message": "Instrument universe generated successfully",
                "timestamp": datetime.now().isoformat(),
                "stats": stats
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to generate instrument universe")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating universe: {str(e)}")

@router.get("/search")
async def search_instruments(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search instruments by query with relevance ranking
    Returns instruments sorted by relevance score
    """
    try:
        if not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")
        
        results = instrument_subscription_service.search_instruments(q, limit)
        
        return {
            "status": "success",
            "query": q,
            "timestamp": datetime.now().isoformat(),
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching instruments: {str(e)}")

@router.get("/instrument/{token}")
async def get_instrument_by_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get instrument details by token
    """
    try:
        instrument = instrument_subscription_service.get_instrument_by_token(token)
        
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "instrument": {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "exchange": instrument.exchange.value,
                "instrument_type": instrument.instrument_type.value,
                "token": instrument.token,
                "expiry": instrument.expiry,
                "strike": instrument.strike,
                "option_type": instrument.option_type.value if instrument.option_type else None,
                "lot_size": instrument.lot_size,
                "tick_size": instrument.tick_size,
                "isin": instrument.isin,
                "trading_session": instrument.trading_session
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting instrument: {str(e)}")

@router.get("/symbol/{symbol}")
async def get_instruments_by_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all instruments for a symbol (including all expiries, strikes, and option types)
    """
    try:
        instruments = instrument_subscription_service.get_instruments_by_symbol(symbol)
        
        if not instruments:
            raise HTTPException(status_code=404, detail="No instruments found for symbol")
        
        return {
            "status": "success",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "count": len(instruments),
            "instruments": [
                {
                    "symbol": inst.symbol,
                    "name": inst.name,
                    "exchange": inst.exchange.value,
                    "instrument_type": inst.instrument_type.value,
                    "token": inst.token,
                    "expiry": inst.expiry,
                    "strike": inst.strike,
                    "option_type": inst.option_type.value if inst.option_type else None,
                    "lot_size": inst.lot_size,
                    "tick_size": inst.tick_size
                }
                for inst in instruments
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting instruments: {str(e)}")

@router.get("/subscription-plans")
async def get_subscription_plans(
    db: AsyncSession = Depends(get_db)
):
    """
    Get WebSocket subscription plans
    Shows how instruments are distributed across WebSocket connections
    """
    try:
        plans = []
        for plan in instrument_subscription_service.subscription_plans:
            plans.append({
                "websocket_id": plan.websocket_id,
                "instrument_count": plan.count,
                "sample_tokens": plan.instruments[:5]  # Show first 5 tokens as sample
            })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "total_plans": len(plans),
            "max_instruments_per_websocket": 5000,
            "max_websocket_connections": 5,
            "plans": plans
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subscription plans: {str(e)}")

@router.get("/subscription-plan/{websocket_id}")
async def get_subscription_plan(
    websocket_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific WebSocket subscription plan
    """
    try:
        plan = instrument_subscription_service.get_subscription_plan(websocket_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        return {
            "status": "success",
            "websocket_id": websocket_id,
            "timestamp": datetime.now().isoformat(),
            "instrument_count": plan.count,
            "instruments": plan.instruments
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subscription plan: {str(e)}")

@router.get("/websocket/{token}")
async def get_websocket_for_token(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get WebSocket connection ID for a specific instrument token
    """
    try:
        websocket_id = instrument_subscription_service.get_websocket_for_token(token)
        
        if websocket_id is None:
            raise HTTPException(status_code=404, detail="Token not found in any subscription plan")
        
        return {
            "status": "success",
            "token": token,
            "websocket_id": websocket_id,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting WebSocket for token: {str(e)}")

@router.get("/stats")
async def get_subscription_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive subscription statistics
    """
    try:
        stats = instrument_subscription_service.get_subscription_stats()
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.get("/universe-summary")
async def get_universe_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of the approved instrument universe
    Shows what instruments are approved for subscription
    """
    try:
        universe = instrument_subscription_service.approved_universe
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "approved_universe": {
                "index_options": {
                    "description": "NSE & BSE Index Options (CE & PE mandatory)",
                    "instruments": list(universe["index_options"].keys()),
                    "details": {
                        name: {
                            "exchange": config["exchange"].value,
                            "expiries": config["expiries"],
                            "strikes_per_expiry": config["strikes_per_expiry"],
                            "strike_range": config["strike_range"]
                        }
                        for name, config in universe["index_options"].items()
                    }
                },
                "stock_options": {
                    "description": "Top 100 NSE F&O Stock Options",
                    "count": universe["stock_options"]["count"],
                    "expiries": universe["stock_options"]["expiries"],
                    "strikes_per_expiry": universe["stock_options"]["strikes_per_expiry"],
                    "strike_range": universe["stock_options"]["strike_range"]
                },
                "stock_futures": {
                    "description": "Top 100 NSE F&O Stock Futures",
                    "count": universe["stock_futures"]["count"],
                    "expiries": universe["stock_futures"]["expiries"]
                },
                "equity": {
                    "description": "Top 1000 NSE Equity Stocks",
                    "count": universe["equity"]["count"]
                },
                "mcx_futures": {
                    "description": "MCX Commodity Futures",
                    "commodities": universe["mcx_futures"]["commodities"],
                    "expiries": universe["mcx_futures"]["expiries"]
                },
                "mcx_options": {
                    "description": "MCX Commodity Options",
                    "commodities": universe["mcx_options"]["commodities"],
                    "expiries": universe["mcx_options"]["expiries"],
                    "strikes_per_expiry": universe["mcx_options"]["strikes_per_expiry"],
                    "strike_range": universe["mcx_options"]["strike_range"]
                }
            },
            "compliance_limits": {
                "max_websocket_connections": 5,
                "max_instruments_per_websocket": 5000,
                "rest_quote_apis_per_second": 1,
                "rest_data_apis_per_second": 5
            },
            "expected_counts": {
                "index_options": "~5,600",
                "stock_options": "~10,000",
                "stock_futures": "~200",
                "nse_equities": "~1,000",
                "mcx_futures": "~18",
                "mcx_options": "~80",
                "total": "~16,900"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting universe summary: {str(e)}")

@router.get("/search-suggestions")
async def get_search_suggestions(
    q: str = Query(..., min_length=1, description="Partial search query"),
    limit: int = Query(10, ge=1, le=20, description="Maximum suggestions"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get search suggestions for autocomplete
    Returns minimal data for fast autocomplete functionality
    """
    try:
        if not q.strip():
            return {
                "status": "success",
                "query": q,
                "timestamp": datetime.now().isoformat(),
                "suggestions": []
            }
        
        # Search with higher limit and extract minimal data
        results = instrument_subscription_service.search_instruments(q, limit * 2)
        
        suggestions = []
        for result in results[:limit]:
            instrument = result["instrument"]
            suggestions.append({
                "symbol": instrument["symbol"],
                "name": instrument["name"],
                "token": instrument["token"],
                "exchange": instrument["exchange"],
                "instrument_type": instrument["instrument_type"],
                "relevance_score": result["relevance_score"]
            })
        
        return {
            "status": "success",
            "query": q,
            "timestamp": datetime.now().isoformat(),
            "suggestions": suggestions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting suggestions: {str(e)}")
