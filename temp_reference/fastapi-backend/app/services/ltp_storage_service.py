"""
LTP Storage Service
Manages storage and retrieval of instrument LTP data
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.models.ltp_storage import InstrumentLTP, LTPHistory
from app.database import get_db_session
from app.services.instrument_subscription_service import Instrument, InstrumentType
import logging

logger = logging.getLogger(__name__)

class LTPStorageService:
    """Service for managing LTP data storage and retrieval"""
    
    def __init__(self):
        self.ltp_cache: Dict[str, InstrumentLTP] = {}
        self.last_update = None
        
    async def initialize_database(self):
        """Initialize database tables"""
        from app.models.ltp_storage import Base
        from app.database import engine
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("LTP storage database tables initialized")
    
    async def store_ltp(self, instrument: Instrument, ltp: float, 
                        change: Optional[float] = None, 
                        change_percent: Optional[float] = None,
                        volume: Optional[int] = None,
                        oi: Optional[int] = None):
        """Store LTP for an instrument"""
        async with get_db_session() as db:
            # Check if instrument exists
            stmt = select(InstrumentLTP).where(InstrumentLTP.token == instrument.token)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                # Update existing record
                stmt = (
                    update(InstrumentLTP)
                    .where(InstrumentLTP.token == instrument.token)
                    .values(
                        ltp=ltp,
                        change=change,
                        change_percent=change_percent,
                        volume=volume,
                        oi=oi,
                        timestamp=datetime.utcnow()
                    )
                )
                await db.execute(stmt)
            else:
                # Create new record
                ltp_record = InstrumentLTP(
                    token=instrument.token,
                    symbol=instrument.symbol,
                    name=instrument.name,
                    exchange=instrument.exchange.value,
                    instrument_type=instrument.instrument_type.value,
                    ltp=ltp,
                    change=change,
                    change_percent=change_percent,
                    volume=volume,
                    oi=oi,
                    closing_price=ltp  # Initialize closing price with current LTP
                )
                db.add(ltp_record)
            
            await db.commit()
            
            # Update cache
            self.ltp_cache[instrument.token] = InstrumentLTP(
                token=instrument.token,
                symbol=instrument.symbol,
                name=instrument.name,
                exchange=instrument.exchange.value,
                instrument_type=instrument.instrument_type.value,
                ltp=ltp,
                change=change,
                change_percent=change_percent,
                volume=volume,
                oi=oi,
                timestamp=datetime.utcnow()
            )
    
    async def get_ltp(self, token: str) -> Optional[InstrumentLTP]:
        """Get LTP for a specific instrument"""
        # Check cache first
        if token in self.ltp_cache:
            return self.ltp_cache[token]
        
        # Fetch from database
        async with get_db_session() as db:
            stmt = select(InstrumentLTP).where(InstrumentLTP.token == token)
            result = await db.execute(stmt)
            ltp_record = result.scalar_one_or_none()
            
            if ltp_record:
                self.ltp_cache[token] = ltp_record
            
            return ltp_record
    
    async def get_all_ltp(self, instrument_type: Optional[InstrumentType] = None) -> List[InstrumentLTP]:
        """Get all LTP data, optionally filtered by instrument type"""
        async with get_db_session() as db:
            if instrument_type:
                stmt = select(InstrumentLTP).where(
                    InstrumentLTP.instrument_type == instrument_type.value
                )
            else:
                stmt = select(InstrumentLTP)
            
            result = await db.execute(stmt)
            return result.scalars().all()
    
    async def store_closing_prices(self):
        """Store current LTPs as closing prices for next day change calculation"""
        async with get_db_session() as db:
            # Get all current LTPs
            stmt = select(InstrumentLTP)
            result = await db.execute(stmt)
            current_ltps = result.scalars().all()
            
            for ltp_record in current_ltps:
                # Store in history
                history = LTPHistory(
                    token=ltp_record.token,
                    ltp=ltp_record.ltp,
                    timestamp=datetime.utcnow(),
                    session_type="CLOSE"
                )
                db.add(history)
                
                # Update closing price
                stmt = (
                    update(InstrumentLTP)
                    .where(InstrumentLTP.token == ltp_record.token)
                    .values(closing_price=ltp_record.ltp)
                )
                await db.execute(stmt)
            
            await db.commit()
            logger.info(f"Stored closing prices for {len(current_ltps)} instruments")
    
    async def calculate_opening_changes(self):
        """Calculate percentage changes from previous closing to current opening"""
        async with get_db_session() as db:
            # Get all instruments with current LTP and closing price
            stmt = select(InstrumentLTP).where(
                InstrumentLTP.closing_price.isnot(None),
                InstrumentLTP.ltp.isnot(None)
            )
            result = await db.execute(stmt)
            instruments = result.scalars().all()
            
            for instrument in instruments:
                if instrument.closing_price > 0:
                    change = instrument.ltp - instrument.closing_price
                    change_percent = (change / instrument.closing_price) * 100
                    
                    # Update the change values
                    stmt = (
                        update(InstrumentLTP)
                        .where(InstrumentLTP.token == instrument.token)
                        .values(
                            change=change,
                            change_percent=change_percent
                        )
                    )
                    await db.execute(stmt)
            
            await db.commit()
            logger.info(f"Calculated opening changes for {len(instruments)} instruments")
    
    async def get_top_gainers(self, limit: int = 10) -> List[InstrumentLTP]:
        """Get top gainers by percentage change"""
        async with get_db_session() as db:
            stmt = (
                select(InstrumentLTP)
                .where(InstrumentLTP.change_percent.isnot(None))
                .order_by(InstrumentLTP.change_percent.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return result.scalars().all()
    
    async def get_top_losers(self, limit: int = 10) -> List[InstrumentLTP]:
        """Get top losers by percentage change"""
        async with get_db_session() as db:
            stmt = (
                select(InstrumentLTP)
                .where(InstrumentLTP.change_percent.isnot(None))
                .order_by(InstrumentLTP.change_percent.asc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            return result.scalars().all()
    
    async def get_market_summary(self) -> Dict:
        """Get market summary statistics"""
        async with get_db_session() as db:
            # Get total instruments
            stmt = select(InstrumentLTP)
            result = await db.execute(stmt)
            all_instruments = result.scalars().all()
            
            if not all_instruments:
                return {"total_instruments": 0, "avg_change": 0, "gainers": 0, "losers": 0}
            
            total_instruments = len(all_instruments)
            avg_change = sum(inst.change_percent or 0 for inst in all_instruments) / total_instruments
            gainers = sum(1 for inst in all_instruments if (inst.change_percent or 0) > 0)
            losers = sum(1 for inst in all_instruments if (inst.change_percent or 0) < 0)
            
            return {
                "total_instruments": total_instruments,
                "avg_change": round(avg_change, 2),
                "gainers": gainers,
                "losers": losers,
                "unchanged": total_instruments - gainers - losers
            }
    
    async def cleanup_old_data(self, days: int = 30):
        """Clean up old historical data"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        async with get_db_session() as db:
            stmt = delete(LTPHistory).where(LTPHistory.timestamp < cutoff_date)
            result = await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Cleaned up {result.rowcount} old LTP history records")

# Global instance
ltp_service = LTPStorageService()
