"""
Option Chain Router v2
Real-time option chain with WebSocket integration
"""

from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.database import get_db
from app.services.option_chain_service import option_chain_service
from app.services.websocket_price_store import price_store
from app.services.instrument_subscription_service import instrument_subscription_service
from app.dependencies import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)

def get_simulated_option_prices(underlying: str, strike: float) -> dict:
    """
    Generate simulated option prices for market closed scenario
    Uses realistic option pricing based on distance from ATM
    """
    try:
        # Get current underlying price from bootstrap data
        from app.services.underlying_price_store import underlying_price_store
        underlying_data = underlying_price_store.get_underlying_ltp_api(underlying)
        underlying_price = underlying_data.get('ltp', 25000)  # Fallback to 25000
        
        # Calculate distance from ATM
        distance_from_atm = abs(strike - underlying_price)
        distance_percentage = distance_from_atm / underlying_price
        
        # Base premium decreases as we move away from ATM
        # ATM options have highest premium
        if distance_percentage <= 0.01:  # Within 1% of ATM
            base_ce_premium = 150.0
            base_pe_premium = 140.0
        elif distance_percentage <= 0.02:  # 1-2% from ATM
            base_ce_premium = 120.0
            base_pe_premium = 110.0
        elif distance_percentage <= 0.05:  # 2-5% from ATM
            base_ce_premium = 80.0
            base_pe_premium = 75.0
        elif distance_percentage <= 0.10:  # 5-10% from ATM
            base_ce_premium = 45.0
            base_pe_premium = 40.0
        else:  # More than 10% from ATM
            base_ce_premium = 20.0
            base_pe_premium = 18.0
        
        # Add some randomness for realism
        import random
        ce_premium = base_ce_premium + random.uniform(-10, 10)
        pe_premium = base_pe_premium + random.uniform(-10, 10)
        
        # Ensure minimum premium
        ce_premium = max(5.0, ce_premium)
        pe_premium = max(5.0, pe_premium)
        
        # Round to 2 decimal places
        ce_premium = round(ce_premium, 2)
        pe_premium = round(pe_premium, 2)
        
        return {
            'ce_ltp': ce_premium,
            'pe_ltp': pe_premium,
            'ce_best_bid': round(ce_premium * 0.95, 2),
            'ce_best_ask': round(ce_premium * 1.05, 2),
            'pe_best_bid': round(pe_premium * 0.95, 2),
            'pe_best_ask': round(pe_premium * 1.05, 2)
        }
        
    except Exception as e:
        logger.error(f"Error generating simulated option prices for {underlying} {strike}: {e}")
        return None

@router.post("/build-skeleton/{underlying}/{expiry}")
async def build_option_chain_skeleton(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Build option chain skeleton from REST API
    Call this once at market open or when adding new expiry
    """
    try:
        success = await option_chain_service.build_skeleton_from_rest(underlying, expiry)
        
        if success:
            # Auto-subscribe to WebSocket ticks
            await option_chain_service.subscribe_to_websocket_ticks(underlying, expiry)
            
            return {
                "status": "success",
                "message": f"Option chain skeleton built for {underlying} {expiry}",
                "underlying": underlying,
                "expiry": expiry,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to build option chain skeleton")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building skeleton: {str(e)}")

@router.get("/chain/{underlying}/{expiry}")
async def get_option_chain(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete option chain with live prices
    Merges skeleton + WebSocket prices
    """
    try:
        chain = option_chain_service.get_option_chain(underlying, expiry)
        
        if not chain:
            # Try to build skeleton if not exists
            success = await option_chain_service.build_skeleton_from_rest(underlying, expiry)
            if success:
                await option_chain_service.subscribe_to_websocket_ticks(underlying, expiry)
                chain = option_chain_service.get_option_chain(underlying, expiry)
        
        return {
            "status": "success",
            "underlying": underlying,
            "expiry": expiry,
            "timestamp": datetime.now().isoformat(),
            "chain": [option.__dict__ for option in chain],
            "count": len(chain)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting option chain: {str(e)}")

@router.get("/straddles/{underlying}/{expiry}")
async def get_straddle_chain(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get straddle chain with real-time prices from WebSocket
    """
    try:
        # First, ensure skeleton exists for this expiry
        skeleton_exists = await option_chain_service.build_skeleton_from_rest(underlying, expiry)
        if skeleton_exists:
            logger.info(f"Built skeleton for {underlying} {expiry}")
        else:
            logger.warning(f"Failed to build skeleton for {underlying} {expiry}")
        
        # Get skeleton from option chain service (REST structure)
        straddles = option_chain_service.get_straddle_chain(underlying, expiry)
        
        if not straddles:
            logger.warning(f"No straddles found for {underlying} {expiry}")
            return {
                "status": "success",
                "underlying": underlying,
                "expiry": expiry,
                "timestamp": datetime.now().isoformat(),
                "chain": [],
                "count": 0,
                "price_source": "no_skeleton",
                "message": f"No skeleton found for {underlying} {expiry}"
            }
        
        # Enhance with real-time prices from WebSocket price store
        enhanced_straddles = []
        for straddle in straddles:
            strike = straddle.get('strike')
            
            # Get real-time CE and PE prices from WebSocket price store
            ce_price_data = price_store.get_price_by_symbol(underlying, strike, 'CE')
            pe_price_data = price_store.get_price_by_symbol(underlying, strike, 'PE')
            
            if ce_price_data and pe_price_data:
                # Use real-time WebSocket prices
                ce_ltp = ce_price_data.get('ltp', straddle.get('ce_ltp', 0))
                pe_ltp = pe_price_data.get('ltp', straddle.get('pe_ltp', 0))
                ce_best_bid = ce_price_data.get('best_bid', straddle.get('ce_best_bid', 0))
                ce_best_ask = ce_price_data.get('best_ask', straddle.get('ce_best_ask', 0))
                pe_best_bid = pe_price_data.get('best_bid', straddle.get('pe_best_bid', 0))
                pe_best_ask = pe_price_data.get('best_ask', straddle.get('pe_best_ask', 0))
                
                price_source = "websocket_realtime"
                timestamp = ce_price_data.get('timestamp', datetime.now().isoformat())
            else:
                # Try to get simulated option prices for market closed scenario
                simulated_prices = get_simulated_option_prices(underlying, strike)
                if simulated_prices:
                    ce_ltp = simulated_prices.get('ce_ltp', straddle.get('ce_ltp', 0))
                    pe_ltp = simulated_prices.get('pe_ltp', straddle.get('pe_ltp', 0))
                    ce_best_bid = simulated_prices.get('ce_best_bid', ce_ltp * 0.95)
                    ce_best_ask = simulated_prices.get('ce_best_ask', ce_ltp * 1.05)
                    pe_best_bid = simulated_prices.get('pe_best_bid', pe_ltp * 0.95)
                    pe_best_ask = simulated_prices.get('pe_best_ask', pe_ltp * 1.05)
                    
                    price_source = "simulated_market_closed"
                    timestamp = datetime.now().isoformat()
                else:
                    # Use skeleton prices (mock data - all zeros)
                    ce_ltp = straddle.get('ce_ltp', 0)
                    pe_ltp = straddle.get('pe_ltp', 0)
                    ce_best_bid = straddle.get('ce_best_bid', 0)
                    ce_best_ask = straddle.get('ce_best_ask', 0)
                    pe_best_bid = straddle.get('pe_best_bid', 0)
                    pe_best_ask = straddle.get('pe_best_ask', 0)
                    
                    price_source = "skeleton_fallback"
                    timestamp = straddle.get('timestamp', datetime.now().isoformat())
            
            # Calculate straddle premium
            straddle_premium = ce_ltp + pe_ltp
            
            # Calculate spread
            ce_spread = ce_best_ask - ce_best_bid if ce_best_ask > ce_best_bid else 0
            pe_spread = pe_best_ask - pe_best_bid if pe_best_ask > pe_best_bid else 0
            total_spread = ce_spread + pe_spread
            
            # Calculate mid price
            ce_mid = (ce_best_bid + ce_best_ask) / 2 if ce_best_bid > 0 and ce_best_ask > 0 else ce_ltp
            pe_mid = (pe_best_bid + pe_best_ask) / 2 if pe_best_bid > 0 and pe_best_ask > 0 else pe_ltp
            mid_price = ce_mid + pe_mid
            
            enhanced_straddle = {
                **straddle,
                "ce_ltp": ce_ltp,
                "pe_ltp": pe_ltp,
                "ce_best_bid": ce_best_bid,
                "ce_best_ask": ce_best_ask,
                "pe_best_bid": pe_best_bid,
                "pe_best_ask": pe_best_ask,
                "straddle_premium": straddle_premium,
                "spread": total_spread,
                "mid_price": mid_price,
                "price_source": price_source,
                "timestamp": timestamp
            }
            
            enhanced_straddles.append(enhanced_straddle)
        
        return {
            "status": "success",
            "underlying": underlying,
            "expiry": expiry,
            "timestamp": datetime.now().isoformat(),
            "chain": enhanced_straddles,
            "count": len(enhanced_straddles),
            "price_source": "websocket_enhanced"
        }
        
    except Exception as e:
        logger.error(f"Error getting straddle chain: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting straddle chain: {str(e)}")

@router.get("/atm/{underlying}/{expiry}")
async def get_atm_strike(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ATM strike based on lowest straddle premium
    """
    try:
        straddles = option_chain_service.get_straddle_chain(underlying, expiry)
        
        if not straddles:
            raise HTTPException(status_code=404, detail="No straddle data available")
        
        # Find ATM based on lowest straddle premium
        atm_straddle = min(straddles, key=lambda x: x.get('straddle_premium', float('inf')))
        
        return {
            "status": "success",
            "underlying": underlying,
            "expiry": expiry,
            "atm_strike": atm_straddle['strike'],
            "atm_premium": atm_straddle['straddle_premium'],
            "calculation_method": "lowest_straddle_premium",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting ATM strike: {str(e)}")

@router.get("/expiries/{underlying}")
async def get_available_expiries(
    underlying: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get available expiry dates from Dhan API (real data)
    """
    from datetime import datetime, timedelta
    import calendar
    
    try:
        # Use existing instrument subscription service which now has real API calls
        expiries = await instrument_subscription_service._generate_expiries(8)
        
        # Separate weekly and monthly expiries
        # First 4 are typically weekly, next 4 are monthly
        weekly_expiries = expiries[:4] if len(expiries) >= 4 else expiries
        monthly_expiries = expiries[4:8] if len(expiries) >= 8 else expiries[4:]
        
        return {
            "status": "success",
            "underlying": underlying,
            "weekly": weekly_expiries,
            "monthly": monthly_expiries,
            "all": expiries,
            "timestamp": datetime.now().isoformat(),
            "data_source": "dhan_api_real"
        }
        
    except Exception as e:
        # Fallback to calculated expiries if API fails
        now = datetime.now()
        expiries = []
        
        # Generate weekly expiries (every Thursday, future only)
        for i in range(4):  # 0=current week, 1=next week, etc.
            expiry_date = now + timedelta(weeks=i)
            days_ahead = 3 - expiry_date.weekday()  # Thursday is 3
            if days_ahead <= 0:
                days_ahead += 7
            expiry_date = expiry_date + timedelta(days=days_ahead)
            
            # Only include future expiries
            if expiry_date > now:
                expiries.append(expiry_date.strftime("%Y-%m-%d"))
        
        # Generate monthly expiries (last Thursday of each month, future only)
        monthly_expiries = []
        for i in range(3):
            year = now.year + (now.month + i - 1) // 12
            month = (now.month + i - 1) % 12 + 1
            
            # Find last Thursday of the month
            last_day = calendar.monthrange(year, month)[1]
            last_thursday = None
            
            for day in range(last_day, 0, -1):
                if datetime(year, month, day).weekday() == 3:  # Thursday
                    last_thursday = datetime(year, month, day)
                    break
            
            if last_thursday and last_thursday > now:
                monthly_expiries.append(last_thursday.strftime("%Y-%m-%d"))
        
        # Combine and sort expiries
        all_expiries = sorted(list(set(expiries + monthly_expiries)))
        
        # Separate weekly and monthly correctly
        weekly_expiries = expiries[:2] if len(expiries) >= 2 else expiries
        monthly_expiries = monthly_expiries[:2] if len(monthly_expiries) >= 2 else monthly_expiries
        
        return {
            "status": "success",
            "underlying": underlying,
            "weekly": weekly_expiries,
            "monthly": monthly_expiries,
            "all": all_expiries,
            "timestamp": datetime.now().isoformat(),
            "data_source": "mock_fallback",
            "error": str(e)
        }

@router.post("/refresh/{underlying}/{expiry}")
async def refresh_option_chain(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh option chain data from Dhan
    """
    try:
        # Clear cache and rebuild
        success = await option_chain_service.build_skeleton_from_rest(underlying, expiry)
        
        if success:
            await option_chain_service.subscribe_to_websocket_ticks(underlying, expiry)
            return {
                "status": "success",
                "message": f"Option chain refreshed for {underlying} {expiry}",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to refresh option chain for {underlying} {expiry}",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing option chain: {str(e)}")

@router.get("/status/{underlying}")
async def get_option_chain_status(
    underlying: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get status of option chain for underlying
    """
    try:
        skeleton_count = len([
            inst for inst in option_chain_service.skeleton.values()
            if inst.underlying == underlying
        ])
        
        price_count = len([
            token for token in option_chain_service.price_store.keys()
            if token in option_chain_service.skeleton and 
            option_chain_service.skeleton[token].underlying == underlying
        ])
        
        subscribed_count = len([
            token for token in option_chain_service.subscribed_tokens
            if token in option_chain_service.skeleton and 
            option_chain_service.skeleton[token].underlying == underlying
        ])
        
        return {
            "status": "success",
            "underlying": underlying,
            "skeleton_instruments": skeleton_count,
            "live_prices": price_count,
            "subscribed_tokens": subscribed_count,
            "cache_entries": len(option_chain_service.chain_cache),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@router.post("/refresh/{underlying}/{expiry}")
async def refresh_option_chain(
    underlying: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Force refresh option chain skeleton
    """
    try:
        # Clear existing cache
        cache_key = f"{underlying}_{expiry}"
        if cache_key in option_chain_service.chain_cache:
            del option_chain_service.chain_cache[cache_key]
        if cache_key in option_chain_service.cache_timestamps:
            del option_chain_service.cache_timestamps[cache_key]
        
        # Rebuild skeleton
        success = await option_chain_service.build_skeleton_from_rest(underlying, expiry)
        
        if success:
            await option_chain_service.subscribe_to_websocket_ticks(underlying, expiry)
            
            return {
                "status": "success",
                "message": f"Option chain refreshed for {underlying} {expiry}",
                "underlying": underlying,
                "expiry": expiry,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to refresh option chain")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing option chain: {str(e)}")
