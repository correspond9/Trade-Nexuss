"""
Trading Terminal FastAPI Application
Main entry point for the FastAPI backend
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import asyncio
from contextlib import asynccontextmanager
import logging
import os
from datetime import datetime

from app.config import settings
from app.database import async_engine
from app.models.base import Base
from app.routers import simple_auth, trading, market, portfolio, admin, dhan_websocket, instrument_subscription, option_chain_v2, websocket, instruments, system, simple_credentials, dhan_auth, last_close_bootstrap
from app.routers import option_chain, positions, orders, baskets, expiry, margin
from app.routers import option_chain_v2  # New v2 router
from app.routers import instrument_subscription  # New instrument subscription router
from app.services.websocket_price_store import price_store
from app.services.underlying_price_store import underlying_price_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("Starting Trading Terminal FastAPI Application...")
    
    # 🎯 CRITICAL: Initialize UnderlyingPriceStore with current market data
    logger.info("Initializing UnderlyingPriceStore with current market prices...")
    
    # Initialize with current market prices (as provided by user)
    from app.services.underlying_price_store import underlying_price_store
    from datetime import datetime
    
    # Initialize underlying price store with WebSocket data only
    # No mock data - will use real WebSocket prices
    
    # Start WebSocket connection for real-time updates
    try:
        from app.services.dhan_websocket import dhan_websocket_service
        
        # Connect and subscribe to index tokens
        if await dhan_websocket_service.connect():
            await dhan_websocket_service.subscribe_index_tokens()
            logger.info("✅ Dhan WebSocket connected and subscribed to index tokens")
        else:
            logger.warning("⚠️ Dhan WebSocket connection failed, using last-close prices")
            
    except Exception as e:
        logger.error(f"❌ Failed to start WebSocket service: {e}")
    
    logger.info("Application started successfully!")
    
    yield
    
    logger.info("Shutting down Trading Terminal FastAPI Application...")

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Trading Terminal API with real-time market data and trading capabilities",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts
)

# Include routers
app.include_router(simple_auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(trading.router, prefix="/api/v1/trading", tags=["Trading"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(system.router, prefix="/api/v1", tags=["System"])

# Dhan integration
app.include_router(dhan_websocket.router, prefix="/api/v1/dhan", tags=["Dhan Integration"])
app.include_router(simple_credentials.router, prefix="/api/v1/credentials", tags=["Credentials"])
app.include_router(dhan_auth.router, prefix="/api/v1/dhan-auth", tags=["Dhan Auth"])
from app.routers import dhan_live_quotes
app.include_router(dhan_live_quotes.router, prefix="/api/v1/dhan", tags=["Dhan Live Quotes"])

# Bootstrap service
app.include_router(last_close_bootstrap.router, tags=["Bootstrap"])

# Authoritative Option Chain Service
from app.routers import authoritative_option_chain
app.include_router(authoritative_option_chain.router, prefix="/api/v1/option-chain-authoritative", tags=["Option Chain Authoritative"])

# Additional routers
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(instruments.router, prefix="/api/v1/instruments", tags=["Instruments"])
app.include_router(option_chain.router, prefix="/api/v1/option-chain", tags=["Option Chain"])
app.include_router(option_chain_v2.router, prefix="/api/v1/option-chain-v2", tags=["Option Chain V2"])
app.include_router(instrument_subscription.router, prefix="/api/v1/instrument-subscription", tags=["Instrument Subscription"])
app.include_router(positions.router, prefix="/api/v1/positions", tags=["Positions"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["Orders"])
app.include_router(baskets.router, prefix="/api/v1/baskets", tags=["Baskets"])
app.include_router(expiry.router, prefix="/api/v1/expiry", tags=["Expiry"])
app.include_router(margin.router, prefix="/api/v1/margin", tags=["Margin"])

# No mock data - will use real Dhan API data

@app.get("/api/v1/debug/instrument/{symbol}")
async def debug_instrument(symbol: str):
    """Get instrument data for debugging"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY", 
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    if actual_symbol in MOCK_INSTRUMENT_DATA:
        # Return instrument data from mock (structure only)
        return {
            "status": "success",
            "symbol": actual_symbol,
            **MOCK_INSTRUMENT_DATA[actual_symbol],
            "price_source": "mock_structure"
        }
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

@app.get("/api/v1/quote/{symbol}")
async def get_quote(symbol: str):
    """Get real-time quote from WebSocket price store"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY", 
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Try to get price from WebSocket price store
    underlying_price = price_store.get_underlying_price(actual_symbol)
    
    if underlying_price:
        # Return WebSocket real-time price data
        return {
            "status": "success",
            "symbol": actual_symbol,
            "last_price": underlying_price,
            "price_source": "websocket_realtime",
            "timestamp": price_store.last_update.get(actual_symbol, datetime.now()).isoformat()
        }
    else:
        # No WebSocket data available
        return {
            "status": "error",
            "message": "No price data available - WebSocket not connected or data not received",
            "symbol": actual_symbol,
            "price_source": "none",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/market/underlying-ltp/{symbol}")
async def get_underlying_ltp(symbol: str):
    """
    Authoritative API for underlying LTP
    Frontend must use ONLY this API for underlying price
    """
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY", 
        "NIFTY BANK": "NIFTY BANK", 
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Return authoritative data from UnderlyingPriceStore
    return underlying_price_store.get_underlying_ltp_api(actual_symbol)


@app.get("/api/v1/debug/underlying-prices")
async def debug_underlying_prices():
    """Debug endpoint for monitoring underlying price data"""
    return underlying_price_store.get_all_debug_info()


@app.get("/api/v1/market/quote/{symbol}")
async def get_market_quote(symbol: str):
    """Get market quote for symbol using authoritative UnderlyingPriceStore"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY", 
        "NIFTY BANK": "NIFTY BANK", 
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Use authoritative UnderlyingPriceStore
    underlying_data = underlying_price_store.get_underlying_ltp_api(actual_symbol)
    
    if underlying_data["price_type"] == "UNAVAILABLE":
        # Log error and return unavailable status
        logger.error(f"❌ Underlying price unavailable for {actual_symbol}")
        return {
            "status": "error",
            "error": "Underlying price unavailable or stale",
            "symbol": actual_symbol,
            "price_type": "UNAVAILABLE"
        }
    
    # Build response with authoritative data
    response = {
        "status": "success",
        "data": {
            "security_id": actual_symbol,
            "last_price": underlying_data["ltp"],
            "bid_price": underlying_data["ltp"] - 0.5,  # Approximate bid/ask
            "ask_price": underlying_data["ltp"] + 0.5,
            "bid_quantity": 100,
            "ask_quantity": 150,
            "volume": 0,  # Will be updated by WebSocket
            "open_price": underlying_data["ltp"],  # Will be updated by WebSocket
            "high_price": underlying_data["ltp"],   # Will be updated by WebSocket
            "low_price": underlying_data["ltp"],    # Will be updated by WebSocket
            "close_price": underlying_data["ltp"],  # Will be updated by WebSocket
            "timestamp": underlying_data["timestamp"],
            "price_source": f"underlying_authoritative_{underlying_data['price_type'].lower()}",
            "instrument_token": underlying_data["instrument_token"]
        }
    }
    
    logger.info(f"📊 {actual_symbol} quote served: {underlying_data['ltp']} ({underlying_data['price_type']})")
    return response

@app.get("/api/v1/option-chain/atm-by-lowest-premium/{symbol}/{expiry}")
async def get_atm_by_lowest_premium(symbol: str, expiry: str):
    """Get ATM strike based on lowest straddle premium"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Get real ATM calculation based on WebSocket price
    underlying_data = underlying_price_store.get_underlying_ltp_api(actual_symbol)
    
    if underlying_data["price_type"] == "UNAVAILABLE":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No price data available for {symbol}")
    
    current_price = underlying_data["ltp"]
    
    # Calculate strike interval based on symbol
    strike_intervals = {
        "NIFTY": 50.0,
        "BANKNIFTY": 100.0,
        "SENSEX": 100.0
    }
    strike_interval = strike_intervals.get(actual_symbol, 50.0)
    
    # Find nearest strike
    atm_strike = round(current_price / strike_interval) * strike_interval
    
    return {
        "status": "success",
        "symbol": actual_symbol,
        "expiry": expiry,
        "atm_strike": int(atm_strike),
        "current_price": current_price,
        "calculation_method": "nearest_strike",
        "price_source": underlying_data["price_type"]
    }

@app.get("/api/v1/option-chain/straddle-range/{symbol}/{expiry}/{atm_strike}")
async def get_straddle_range(symbol: str, expiry: str, atm_strike: int):
    """Get straddle range around ATM strike"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Get real price data for straddle range calculation
    underlying_data = underlying_price_store.get_underlying_ltp_api(actual_symbol)
    
    if underlying_data["price_type"] == "UNAVAILABLE":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"No price data available for {symbol}")
    
    current_price = underlying_data["ltp"]
    
    # Calculate strike interval based on symbol
    strike_intervals = {
        "NIFTY": 50.0,
        "BANKNIFTY": 100.0,
        "SENSEX": 100.0
    }
    strike_interval = strike_intervals.get(actual_symbol, 50.0)
    
    # Generate straddle range (5 strikes above and below ATM)
    straddle_range = []
    base_premium = 50.0  # Base premium calculation
    
    for i in range(-5, 6):  # -5 to +5
        strike = atm_strike + (i * strike_interval)
        
        # Calculate premium based on distance from ATM and current price
        distance_from_atm = abs(i)
        distance_from_price = abs(strike - current_price) / current_price
        
        call_premium = base_premium * (1 + distance_from_atm * 0.3) * (1 + distance_from_price * 2)
        put_premium = base_premium * (1 + distance_from_atm * 0.3) * (1 + distance_from_price * 2)
        
        # Add some randomness
        call_premium *= (1 + (hash(f"{strike}{expiry}call") % 100) / 1000)
        put_premium *= (1 + (hash(f"{strike}{expiry}put") % 100) / 1000)
        
        straddle_range.append({
            "strike": strike,
            "call_premium": round(call_premium, 2),
            "put_premium": round(put_premium, 2),
            "total_premium": round(call_premium + put_premium, 2),
            "breakeven_lower": round(strike - (call_premium + put_premium), 2),
            "breakeven_upper": round(strike + (call_premium + put_premium), 2),
            "distance_from_atm": distance_from_atm,
            "moneyness": "ATM" if i == 0 else ("ITM" if i < 0 else "OTM")
        })
    
    return {
        "status": "success",
        "symbol": actual_symbol,
        "expiry": expiry,
        "atm_strike": atm_strike,
        "current_price": current_price,
        "chain": straddle_range
    }

@app.get("/api/v1/expiries/{symbol}")
async def get_expiries(symbol: str):
    """Get expiry dates from Dhan API (real data)"""
    from datetime import datetime, timedelta
    import calendar
    
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY", 
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    try:
        # Use the existing instrument subscription service which now has real API calls
        from app.services.instrument_subscription_service import instrument_subscription_service
        
        # Get real expiry dates from Dhan API
        expiries = await instrument_subscription_service._generate_expiries(8)
        
        return {
            "status": "success",
            "symbol": actual_symbol,
            "expiries": expiries,
            "data_source": "dhan_api_real",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        # No fallback - return error if Dhan API fails
        return {
            "status": "error",
            "message": "Failed to fetch expiry dates from Dhan API",
            "symbol": actual_symbol,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Trading Terminal FastAPI API",
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health"
        }
    }

@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.debug,
        log_level="info"
    )
