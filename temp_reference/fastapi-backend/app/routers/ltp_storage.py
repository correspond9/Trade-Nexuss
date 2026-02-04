"""
LTP Storage API Endpoints
Manages storage and retrieval of instrument LTP data
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.services.ltp_storage_service import ltp_service
from app.models.ltp_storage import InstrumentLTP
from app.services.instrument_subscription_service import instrument_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ltp", tags=["LTP Storage"])

@router.post("/initialize")
async def initialize_ltp_storage():
    """Initialize LTP storage database"""
    try:
        await ltp_service.initialize_database()
        return {"status": "success", "message": "LTP storage initialized"}
    except Exception as e:
        logger.error(f"Error initializing LTP storage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store/{token}")
async def store_ltp(
    token: str,
    ltp: float,
    change: Optional[float] = None,
    change_percent: Optional[float] = None,
    volume: Optional[int] = None,
    oi: Optional[int] = None
):
    """Store LTP for a specific instrument"""
    try:
        # Get instrument details
        instrument = await instrument_service.get_instrument_by_token(token)
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Instrument {token} not found")
        
        await ltp_service.store_ltp(
            instrument=instrument,
            ltp=ltp,
            change=change,
            change_percent=change_percent,
            volume=volume,
            oi=oi
        )
        
        return {"status": "success", "message": f"LTP stored for {token}"}
    except Exception as e:
        logger.error(f"Error storing LTP for {token}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{token}")
async def get_ltp(token: str):
    """Get LTP for a specific instrument"""
    try:
        ltp_record = await ltp_service.get_ltp(token)
        if not ltp_record:
            raise HTTPException(status_code=404, detail=f"LTP not found for {token}")
        
        return {
            "token": ltp_record.token,
            "symbol": ltp_record.symbol,
            "name": ltp_record.name,
            "exchange": ltp_record.exchange,
            "instrument_type": ltp_record.instrument_type,
            "ltp": ltp_record.ltp,
            "change": ltp_record.change,
            "change_percent": ltp_record.change_percent,
            "volume": ltp_record.volume,
            "oi": ltp_record.oi,
            "timestamp": ltp_record.timestamp,
            "closing_price": ltp_record.closing_price
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting LTP for {token}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_all_ltp(
    instrument_type: Optional[str] = Query(None, description="Filter by instrument type"),
    limit: int = Query(100, description="Maximum number of records"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get all LTP data, optionally filtered by instrument type"""
    try:
        # Convert string to enum if provided
        inst_type = None
        if instrument_type:
            from app.services.instrument_subscription_service import InstrumentType
            try:
                inst_type = InstrumentType(instrument_type.upper())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid instrument type: {instrument_type}")
        
        ltp_records = await ltp_service.get_all_ltp(inst_type)
        
        # Apply pagination
        total = len(ltp_records)
        paginated_records = ltp_records[offset:offset + limit]
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": [
                {
                    "token": record.token,
                    "symbol": record.symbol,
                    "name": record.name,
                    "exchange": record.exchange,
                    "instrument_type": record.instrument_type,
                    "ltp": record.ltp,
                    "change": record.change,
                    "change_percent": record.change_percent,
                    "volume": record.volume,
                    "oi": record.oi,
                    "timestamp": record.timestamp
                }
                for record in paginated_records
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all LTP data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store-closing-prices")
async def store_closing_prices():
    """Store current LTPs as closing prices for next day"""
    try:
        await ltp_service.store_closing_prices()
        return {"status": "success", "message": "Closing prices stored"}
    except Exception as e:
        logger.error(f"Error storing closing prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/calculate-opening-changes")
async def calculate_opening_changes():
    """Calculate percentage changes from previous closing to current opening"""
    try:
        await ltp_service.calculate_opening_changes()
        return {"status": "success", "message": "Opening changes calculated"}
    except Exception as e:
        logger.error(f"Error calculating opening changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-gainers")
async def get_top_gainers(limit: int = Query(10, description="Number of top gainers")):
    """Get top gainers by percentage change"""
    try:
        gainers = await ltp_service.get_top_gainers(limit)
        return {
            "gainers": [
                {
                    "token": record.token,
                    "symbol": record.symbol,
                    "name": record.name,
                    "ltp": record.ltp,
                    "change": record.change,
                    "change_percent": record.change_percent,
                    "timestamp": record.timestamp
                }
                for record in gainers
            ]
        }
    except Exception as e:
        logger.error(f"Error getting top gainers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/top-losers")
async def get_top_losers(limit: int = Query(10, description="Number of top losers")):
    """Get top losers by percentage change"""
    try:
        losers = await ltp_service.get_top_losers(limit)
        return {
            "losers": [
                {
                    "token": record.token,
                    "symbol": record.symbol,
                    "name": record.name,
                    "ltp": record.ltp,
                    "change": record.change,
                    "change_percent": record.change_percent,
                    "timestamp": record.timestamp
                }
                for record in losers
            ]
        }
    except Exception as e:
        logger.error(f"Error getting top losers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market-summary")
async def get_market_summary():
    """Get market summary statistics"""
    try:
        summary = await ltp_service.get_market_summary()
        return summary
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cleanup")
async def cleanup_old_data(days: int = Query(30, description="Days of data to keep")):
    """Clean up old historical data"""
    try:
        await ltp_service.cleanup_old_data(days)
        return {"status": "success", "message": f"Cleaned up data older than {days} days"}
    except Exception as e:
        logger.error(f"Error cleaning up old data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch-store")
async def batch_store_ltp(ltp_data: List[dict]):
    """Store LTP data for multiple instruments"""
    try:
        stored_count = 0
        errors = []
        
        for data in ltp_data:
            try:
                token = data.get("token")
                ltp = data.get("ltp")
                
                if not token or ltp is None:
                    errors.append(f"Missing token or ltp in data: {data}")
                    continue
                
                instrument = await instrument_service.get_instrument_by_token(token)
                if not instrument:
                    errors.append(f"Instrument {token} not found")
                    continue
                
                await ltp_service.store_ltp(
                    instrument=instrument,
                    ltp=ltp,
                    change=data.get("change"),
                    change_percent=data.get("change_percent"),
                    volume=data.get("volume"),
                    oi=data.get("oi")
                )
                stored_count += 1
                
            except Exception as e:
                errors.append(f"Error storing {token}: {str(e)}")
        
        return {
            "status": "success",
            "stored_count": stored_count,
            "total_requested": len(ltp_data),
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error in batch store LTP: {e}")
        raise HTTPException(status_code=500, detail=str(e))
