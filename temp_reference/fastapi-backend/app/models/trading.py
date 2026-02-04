"""
Trading Models
Pydantic models for trading operations
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderType(str, Enum):
    """Order type enumeration"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    STOP_LOSS_MARKET = "STOP_LOSS_MARKET"

class TransactionType(str, Enum):
    """Transaction type enumeration"""
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(str, Enum):
    """Order status enumeration"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class ProductType(str, Enum):
    """Product type enumeration"""
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    MARGIN = "MARGIN"

class OrderBase(BaseModel):
    """Base order model"""
    security_id: str = Field(..., description="Security identifier")
    quantity: int = Field(..., gt=0, description="Order quantity")
    price: Optional[float] = Field(None, gt=0, description="Order price")
    order_type: OrderType = Field(..., description="Order type")
    transaction_type: TransactionType = Field(..., description="Buy/Sell")
    product_type: ProductType = Field(ProductType.INTRADAY, description="Product type")

class OrderCreate(OrderBase):
    """Order creation model"""
    pass

class OrderUpdate(BaseModel):
    """Order update model"""
    price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)

class Order(OrderBase):
    """Order response model"""
    id: int
    user_id: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime
    executed_at: Optional[datetime] = None
    executed_price: Optional[float] = None
    executed_quantity: Optional[int] = None

class Trade(BaseModel):
    """Trade model"""
    id: int
    order_id: int
    security_id: str
    quantity: int
    price: float
    transaction_type: TransactionType
    executed_at: datetime

class BasketOrder(BaseModel):
    """Basket order model"""
    name: str
    orders: List[OrderCreate]
    description: Optional[str] = None
