"""
LTP Storage Database Models
Stores Last Traded Prices for all subscribed instruments
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

from app.models.base import Base

class InstrumentLTP(Base):
    """Store LTP for all subscribed instruments"""
    __tablename__ = "instrument_ltp"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(50), unique=True, index=True, nullable=False)
    symbol = Column(String(50), index=True, nullable=False)
    name = Column(String(100), nullable=False)
    exchange = Column(String(20), nullable=False)
    instrument_type = Column(String(20), nullable=False)
    ltp = Column(Float, nullable=False)
    change = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    oi = Column(Integer, nullable=True)  # Open Interest
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    closing_price = Column(Float, nullable=True)  # Previous day closing
    
    # Create composite index for faster queries
    __table_args__ = (
        Index('idx_symbol_exchange', 'symbol', 'exchange'),
        Index('idx_instrument_type', 'instrument_type'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<InstrumentLTP(token={self.token}, symbol={self.symbol}, ltp={self.ltp})>"

class LTPHistory(Base):
    """Store historical LTP data for change calculations"""
    __tablename__ = "ltp_history"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(50), index=True, nullable=False)
    ltp = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    session_type = Column(String(20), nullable=True)  # OPEN, CLOSE, etc.
    
    __table_args__ = (
        Index('idx_token_timestamp', 'token', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<LTPHistory(token={self.token}, ltp={self.ltp}, timestamp={self.timestamp})>"
