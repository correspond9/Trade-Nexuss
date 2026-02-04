"""
Portfolio Models
Pydantic models for portfolio operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class PositionType(str, Enum):
    """Position type enumeration"""
    LONG = "LONG"
    SHORT = "SHORT"

class Position(BaseModel):
    """Position model"""
    id: int
    user_id: int
    security_id: str
    quantity: int
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    position_type: PositionType
    product_type: str
    created_at: datetime
    updated_at: datetime

class Holding(BaseModel):
    """Holding model"""
    id: int
    user_id: int
    security_id: str
    quantity: int
    average_cost: float
    current_price: float
    market_value: float
    pnl: float
    pnl_percentage: float
    created_at: datetime
    updated_at: datetime

class WalletBalance(BaseModel):
    """Wallet balance model"""
    user_id: int
    total_balance: Decimal
    available_balance: Decimal
    used_balance: Decimal
    margin_used: Decimal
    opening_balance: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    last_updated: datetime

class PortfolioSummary(BaseModel):
    """Portfolio summary model"""
    user_id: int
    total_investment: Decimal
    current_value: Decimal
    total_pnl: Decimal
    pnl_percentage: float
    total_positions: int
    active_positions: int
    total_holdings: int
    last_updated: datetime

class PnLReport(BaseModel):
    """P&L report model"""
    user_id: int
    period_start: datetime
    period_end: datetime
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_pnl: Decimal
    trades_count: int
    winning_trades: int
    losing_trades: int
    win_rate: float
