
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


# ==================== MOCK EXCHANGE MODELS ====================

class BrokeragePlan(Base):
    __tablename__ = "brokerage_plans"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    flat_fee = Column(Float, default=20.0)  # flat per order
    percent_fee = Column(Float, default=0.0)  # optional percent of turnover
    max_fee = Column(Float, default=20.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=True)
    password_salt = Column(String, nullable=True)
    password_hash = Column(String, nullable=True)
    role = Column(String, default="USER")  # USER | ADMIN | SUPER_ADMIN
    status = Column(String, default="ACTIVE")  # ACTIVE | BLOCKED | INACTIVE
    allowed_segments = Column(String, default="NSE,NFO,BSE,MCX")
    wallet_balance = Column(Float, default=0.0)
    brokerage_plan_id = Column(Integer, ForeignKey("brokerage_plans.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MarginAccount(Base):
    __tablename__ = "margin_accounts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, unique=True)
    available_margin = Column(Float, default=0.0)
    used_margin = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MockOrder(Base):
    __tablename__ = "mock_orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    symbol = Column(String, nullable=False)
    security_id = Column(String, nullable=True)
    exchange_segment = Column(String, default="NSE_EQ")
    transaction_type = Column(String, nullable=False)  # BUY | SELL
    quantity = Column(Integer, nullable=False)
    filled_qty = Column(Integer, default=0)
    order_type = Column(String, default="MARKET")  # MARKET | LIMIT | SL-M | SL-L | GTT | TRIGGER
    product_type = Column(String, default="MIS")  # MIS | NORMAL
    price = Column(Float, default=0.0)
    trigger_price = Column(Float, nullable=True)
    status = Column(String, default="PENDING")  # PENDING | EXECUTED | PARTIAL | CANCELLED | REJECTED
    basket_id = Column(Integer, ForeignKey("mock_baskets.id"), nullable=True)
    is_super = Column(Boolean, default=False)
    target_price = Column(Float, nullable=True)
    stop_loss_price = Column(Float, nullable=True)
    trailing_jump = Column(Float, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MockTrade(Base):
    __tablename__ = "mock_trades"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("mock_orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    price = Column(Float, nullable=False)
    qty = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("mock_orders.id"), nullable=True)
    user_id = Column(Integer, nullable=True)
    symbol = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # ORDER_ACCEPTED | PARTIAL_FILL | FULL_FILL | ORDER_REJECTED | ORDER_CANCELLED
    decision_time_price = Column(Float, nullable=True)
    fill_price = Column(Float, nullable=True)
    fill_quantity = Column(Integer, nullable=True)
    reason = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    slippage = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MockPosition(Base):
    __tablename__ = "mock_positions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    symbol = Column(String, nullable=False)
    exchange_segment = Column(String, default="NSE_EQ")
    product_type = Column(String, default="MIS")
    quantity = Column(Integer, default=0)
    avg_price = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    status = Column(String, default="OPEN")  # OPEN | CLOSED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'symbol', 'product_type', name='uq_user_symbol_product'),)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    entry_type = Column(String, nullable=False)  # PAYIN | PAYOUT | TRADE_PNL | MARGIN | ADJUST
    credit = Column(Float, default=0.0)
    debit = Column(Float, default=0.0)
    balance = Column(Float, default=0.0)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MockBasket(Base):
    __tablename__ = "mock_baskets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)
    name = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")  # ACTIVE | EXECUTED | CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)


class MockBasketLeg(Base):
    __tablename__ = "mock_basket_legs"
    id = Column(Integer, primary_key=True)
    basket_id = Column(Integer, ForeignKey("mock_baskets.id"), nullable=False)
    symbol = Column(String, nullable=False)
    security_id = Column(String, nullable=True)
    exchange_segment = Column(String, default="NSE_EQ")
    transaction_type = Column(String, nullable=False)  # BUY | SELL
    quantity = Column(Integer, nullable=False)
    order_type = Column(String, default="MARKET")
    product_type = Column(String, default="MIS")
    price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
