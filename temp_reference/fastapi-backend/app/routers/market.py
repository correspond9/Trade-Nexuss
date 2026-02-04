"""
Market Data Router
Handles market data endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, date

from app.database import get_db
from app.models.market import Instrument, Quote, MarketDepth, HistoricalDataRequest, HistoricalData, Watchlist
from app.dependencies import get_current_active_user

router = APIRouter()

# Mock data for development
MOCK_INSTRUMENT_DATA = {
    "NIFTY": {
        "symbol": "NIFTY",
        "lotSize": 50,
        "strikeInterval": 50,
        "hasOptions": True,
        "totalInstruments": 1500
    },
    "NIFTY BANK": {
        "symbol": "NIFTY BANK", 
        "lotSize": 25,
        "strikeInterval": 100,
        "hasOptions": True,
        "totalInstruments": 800
    },
    "SENSEX": {
        "symbol": "SENSEX",
        "lotSize": 10,
        "strikeInterval": 100,
        "hasOptions": True,
        "totalInstruments": 600
    }
}

MOCK_QUOTES = {
    "NIFTY": {
        "security_id": "NIFTY",
        "last_price": 19750.25,
        "bid_price": 19749.75,
        "ask_price": 19750.75,
        "bid_quantity": 100,
        "ask_quantity": 150,
        "volume": 125000,
        "open_price": 19674.75,
        "high_price": 19812.00,
        "low_price": 19650.25,
        "close_price": 19674.75,
        "change": 75.50,
        "timestamp": datetime.now()
    },
    "NIFTY BANK": {
        "security_id": "NIFTY BANK",
        "last_price": 44525.75,
        "bid_price": 44525.25,
        "ask_price": 44526.25,
        "bid_quantity": 80,
        "ask_quantity": 120,
        "volume": 85000,
        "open_price": 44400.50,
        "high_price": 44700.00,
        "low_price": 44325.25,
        "close_price": 44400.50,
        "change": 125.25,
        "timestamp": datetime.now()
    },
    "SENSEX": {
        "security_id": "SENSEX",
        "last_price": 66550.30,
        "bid_price": 66549.80,
        "ask_price": 66550.80,
        "bid_quantity": 60,
        "ask_quantity": 90,
        "volume": 45000,
        "open_price": 66329.50,
        "high_price": 66780.00,
        "low_price": 66250.75,
        "close_price": 66329.50,
        "change": 220.80,
        "timestamp": datetime.now()
    },
    "CRUDEOIL": {
        "security_id": "CRUDEOIL",
        "last_price": 6250.75,
        "bid_price": 6249.25,
        "ask_price": 6252.25,
        "bid_quantity": 40,
        "ask_quantity": 60,
        "volume": 25000,
        "open_price": 6225.50,
        "high_price": 6280.00,
        "low_price": 6210.25,
        "close_price": 6225.50,
        "change": 25.25,
        "timestamp": datetime.now()
    }
}

@router.get("/instruments/{exchange}", response_model=List[Instrument])
async def get_instruments(
    exchange: str,
    segment: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 1000,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get instruments by exchange"""
    # TODO: Implement instrument retrieval logic
    return []

@router.post("/quotes", response_model=List[Quote])
async def get_multiple_quotes(
    security_ids: List[str],
    db: AsyncSession = Depends(get_db)
):
    """Get multiple quotes"""
    # TODO: Implement multiple quotes logic
    return []

@router.get("/depth/{security_id}", response_model=MarketDepth)
async def get_market_depth(
    security_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get market depth for security"""
    # TODO: Implement market depth logic
    raise HTTPException(status_code=404, detail="Security not found")

@router.post("/historical", response_model=List[HistoricalData])
async def get_historical_data(
    request: HistoricalDataRequest,
    db: AsyncSession = Depends(get_db)
):
    """Get historical data"""
    # TODO: Implement historical data logic
    return []

@router.get("/search", response_model=List[Instrument])
async def search_instruments(
    query: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Search instruments by symbol or name"""
    # TODO: Implement instrument search logic
    return []

@router.get("/watchlist", response_model=List[Watchlist])
async def get_watchlists(
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user watchlists"""
    # TODO: Implement watchlist retrieval logic
    return []

@router.post("/watchlist", response_model=Watchlist)
async def create_watchlist(
    name: str,
    instruments: List[str],
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new watchlist"""
    # TODO: Implement watchlist creation logic
    return Watchlist(
        id=1,
        user_id=current_user["id"],
        name=name,
        instruments=instruments,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

@router.post("/watchlist/{watchlist_id}/instruments/{security_id}")
async def add_to_watchlist(
    watchlist_id: int,
    security_id: str,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Add instrument to watchlist"""
    # TODO: Implement add to watchlist logic
    return {"message": "Instrument added to watchlist"}

# Additional endpoints for Trade page functionality

@router.get("/debug/instrument/{symbol}")
async def debug_instrument(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
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
        return {
            "status": "success",
            "symbol": actual_symbol,
            **MOCK_INSTRUMENT_DATA[actual_symbol]
        }
    else:
        return {
            "status": "error",
            "message": f"Instrument {symbol} not found"
        }

@router.get("/quote/{symbol}")
async def get_market_quote(
    symbol: str,
    db: AsyncSession = Depends(get_db)
):
    """Get market quote for symbol"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY BANK": "NIFTY BANK", 
        "SENSEX": "SENSEX",
        "CRUDEOIL": "CRUDEOIL"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    if actual_symbol in MOCK_QUOTES:
        return {
            "status": "success",
            "data": MOCK_QUOTES[actual_symbol]
        }
    else:
        raise HTTPException(status_code=404, detail=f"Quote for {symbol} not found")

@router.get("/option-chain/atm-by-lowest-premium/{symbol}/{expiry}")
async def get_atm_by_lowest_premium(
    symbol: str,
    expiry: str,
    db: AsyncSession = Depends(get_db)
):
    """Get ATM strike based on lowest straddle premium"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    # Mock ATM calculation based on current price
    if actual_symbol in MOCK_QUOTES:
        current_price = MOCK_QUOTES[actual_symbol]["last_price"]
        # Calculate nearest strike based on lot size
        lot_size = MOCK_INSTRUMENT_DATA[actual_symbol]["lotSize"]
        strike_interval = MOCK_INSTRUMENT_DATA[actual_symbol]["strikeInterval"]
        
        # Find nearest strike
        atm_strike = round(current_price / strike_interval) * strike_interval
        
        return {
            "status": "success",
            "symbol": actual_symbol,
            "expiry": expiry,
            "atm_strike": int(atm_strike),
            "current_price": current_price,
            "calculation_method": "nearest_strike"
        }
    else:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

@router.get("/option-chain/straddle-range/{symbol}/{expiry}/{atm_strike}")
async def get_straddle_range(
    symbol: str,
    expiry: str,
    atm_strike: int,
    db: AsyncSession = Depends(get_db)
):
    """Get straddle range around ATM strike"""
    # Map display names to symbols
    symbol_map = {
        "NIFTY": "NIFTY",
        "NIFTY 50": "NIFTY",
        "NIFTY BANK": "NIFTY BANK",
        "SENSEX": "SENSEX"
    }
    
    actual_symbol = symbol_map.get(symbol, symbol)
    
    if actual_symbol not in MOCK_QUOTES:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    
    current_price = MOCK_QUOTES[actual_symbol]["last_price"]
    strike_interval = MOCK_INSTRUMENT_DATA[actual_symbol]["strikeInterval"]
    
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
