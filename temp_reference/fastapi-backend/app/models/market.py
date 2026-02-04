"""
Market Data Models
Pydantic models for market data operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class Instrument(BaseModel):
    """Instrument model"""
    security_id: str
    symbol: str
    name: str
    exchange: str
    segment: str
    lot_size: Optional[int] = None
    tick_size: Optional[float] = None
    isin: Optional[str] = None

class Quote(BaseModel):
    """Quote model"""
    security_id: str
    last_price: float
    bid_price: Optional[float] = None
    ask_price: Optional[float] = None
    bid_quantity: Optional[int] = None
    ask_quantity: Optional[int] = None
    volume: Optional[int] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    timestamp: datetime

class MarketDepth(BaseModel):
    """Market depth model"""
    security_id: str
    bids: List[Dict[str, Any]]
    asks: List[Dict[str, Any]]
    timestamp: datetime

class HistoricalDataRequest(BaseModel):
    """Historical data request model"""
    security_id: str
    interval: str = Field(..., description="Time interval (1m, 5m, 15m, 1h, 1d)")
    start_date: datetime
    end_date: datetime

class HistoricalData(BaseModel):
    """Historical data model"""
    security_id: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: int
    open_interest: Optional[int] = None

class Watchlist(BaseModel):
    """Watchlist model"""
    id: int
    user_id: int
    name: str
    instruments: List[str]
    created_at: datetime
    updated_at: datetime
