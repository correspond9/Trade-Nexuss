
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, Text, ForeignKey, UniqueConstraint
from datetime import datetime
from .db import Base

class DhanCredential(Base):
    __tablename__ = "dhan_credentials"
    id = Column(Integer, primary_key=True)
    client_id = Column(String)
    api_key = Column(String)
    api_secret = Column(String)
    auth_token = Column(String)
    daily_token = Column(String)
    auth_mode = Column(String)  # DAILY_TOKEN | STATIC_IP
    is_default = Column(Boolean, default=False)
    last_updated = Column(DateTime, default=datetime.utcnow)


class Watchlist(Base):
    """User watchlist for on-demand (Tier A) subscriptions"""
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)  # Optional user ID for future multi-user support
    symbol = Column(String, nullable=False)  # e.g., "RELIANCE", "NIFTY50"
    expiry_date = Column(String, nullable=False)  # e.g., "26FEB2026"
    instrument_type = Column(String, nullable=False)  # "EQUITY", "STOCK_OPTION", "INDEX_OPTION"
    added_at = Column(DateTime, default=datetime.utcnow)
    added_order = Column(Integer)  # For LRU eviction on rate limit
    __table_args__ = (UniqueConstraint('user_id', 'symbol', 'expiry_date', name='uq_user_symbol_expiry'),)


class Subscription(Base):
    """Track all active subscriptions (Tier A + Tier B)"""
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    instrument_token = Column(String, unique=True, nullable=False)  # e.g., "NIFTY50_26FEB_24000CE"
    symbol = Column(String, nullable=False)
    expiry_date = Column(String)
    strike_price = Column(Float)
    option_type = Column(String)  # "CE", "PE", None for futures/equity
    tier = Column(String, nullable=False)  # "TIER_A" or "TIER_B"
    subscribed_at = Column(DateTime, default=datetime.utcnow)
    ws_connection_id = Column(Integer)  # Which of 5 WS connections (1-5)
    active = Column(Boolean, default=True)


class ATMCache(Base):
    """Cache ATM strikes and generated chains"""
    __tablename__ = "atm_cache"
    id = Column(Integer, primary_key=True)
    underlying_symbol = Column(String, unique=True, nullable=False)
    current_ltp = Column(Float, nullable=False)
    atm_strike = Column(Float, nullable=False)
    strike_step = Column(Float, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)
    generated_strikes = Column(Text)  # JSON: {"26FEB": [2600, 2625, ...]}


class SubscriptionLog(Base):
    """Audit log for subscription/unsubscription events"""
    __tablename__ = "subscription_log"
    id = Column(Integer, primary_key=True)
    action = Column(String, nullable=False)  # "SUBSCRIBE", "UNSUBSCRIBE", "RATE_LIMIT_EVICT", "EOD_CLEANUP"
    instrument_token = Column(String)
    reason = Column(String)  # Why was it unsubscribed
    timestamp = Column(DateTime, default=datetime.utcnow)
