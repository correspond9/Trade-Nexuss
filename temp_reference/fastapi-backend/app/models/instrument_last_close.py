"""
Instrument Last Close Price Model
Stores last known close prices for instruments when market is closed
"""

from datetime import datetime, date
from sqlalchemy import Column, String, Float, Date, DateTime, Text, Boolean, Index, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class InstrumentLastClose(Base):
    """Last close price for an instrument"""
    __tablename__ = "instrument_last_close"
    
    # Primary key
    instrument_token = Column(String(50), primary_key=True)
    
    # Price data
    last_close_price = Column(Float, nullable=False)
    trading_date = Column(Date, nullable=False)
    
    # Metadata
    source = Column(String(50), nullable=False, default="REST_BOOTSTRAP")
    exchange_timestamp = Column(DateTime, nullable=True)
    
    # Audit fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Bootstrap tracking
    bootstrap_completed = Column(Boolean, default=False, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_instrument_last_close_token', 'instrument_token'),
        Index('idx_instrument_last_close_date', 'trading_date'),
        Index('idx_instrument_last_close_source', 'source'),
    )
    
    def __repr__(self):
        return f"<InstrumentLastClose(token={self.instrument_token}, price={self.last_close_price}, date={self.trading_date})>"
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'instrument_token': self.instrument_token,
            'last_close_price': self.last_close_price,
            'trading_date': self.trading_date.isoformat() if self.trading_date else None,
            'source': self.source,
            'exchange_timestamp': self.exchange_timestamp.isoformat() if self.exchange_timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'bootstrap_completed': self.bootstrap_completed
        }
