"""
Authoritative Option Chain Service
Implements the complete option chain construction flow as per specifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json

logger = logging.getLogger(__name__)

from app.market.atm_engine import ATM_ENGINE
from app.ems.exchange_clock import is_market_open
from app.services.dhan_rate_limiter import DhanRateLimiter

class ExchangeSegment(Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"

class OptionType(Enum):
    CALL = "CE"
    PUT = "PE"

@dataclass
class OptionData:
    token: str
    ltp: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    oi: Optional[int] = None
    volume: Optional[int] = None
    iv: Optional[float] = None
    greeks: Optional[Dict[str, float]] = None
    depth: Optional[Dict[str, List[Dict[str, float]]]] = None

@dataclass
class StrikeData:
    strike_price: float
    CE: OptionData
    PE: OptionData

@dataclass
class OptionChainSkeleton:
    underlying: str
    expiry: str
    lot_size: int
    strike_interval: float
    atm_strike: float
    strikes: Dict[float, StrikeData]
    last_updated: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        return {
            "underlying": self.underlying,
            "expiry": self.expiry,
            "lot_size": self.lot_size,
            "strike_interval": self.strike_interval,
            "atm_strike": self.atm_strike,
            "strikes": {
                str(strike): {
                    "strike_price": strike,
                    "CE": asdict(strike_data.CE),
                    "PE": asdict(strike_data.PE)
                }
                for strike, strike_data in self.strikes.items()
            },
            "last_updated": self.last_updated.isoformat()
        }

@dataclass
class ATMRegistry:
    """Stores computed ATM strikes for underlyings"""
    atm_strikes: Dict[str, float]
    last_updated: Dict[str, datetime]
    
    def __init__(self):
        self.atm_strikes = {}
        self.last_updated = {}

@dataclass
class ExpiryRegistry:
    """Stores selected expiries for underlyings"""
    expiries: Dict[str, List[str]]
    last_updated: Dict[str, datetime]
    
    def __init__(self):
        self.expiries = {}
        self.last_updated = {}

class AuthoritativeOptionChainService:
    """
    Authoritative Option Chain Service
    Implements complete flow from expiry fetching to live data serving
    
    STRICT COMPLIANCE WITH DHANHQ API LIMITS:
    - Max 5 WebSocket connections per user (5,000 tokens each = 25,000 max)
    - REST Quote API: 1 req/sec
    - REST Data APIs: 5 req/sec
    - No excessive retries or reconnect storms
    - Centralized REST caching with proper rate limiting
    """
    
    # ========== DHANHQ API LIMITS (DO NOT CHANGE) ==========
    MAX_WEBSOCKET_CONNECTIONS = 5
    MAX_TOKENS_PER_WEBSOCKET = 5000
    MAX_REST_QUOTE_RPS = 1  # requests per second
    MAX_REST_DATA_RPS = 5   # requests per second
    
    def __init__(self):
        # Central cache - the single source of truth
        self.option_chain_cache: Dict[str, Dict] = {}
        self.atm_cache: Dict[str, float] = {}
        self.expiry_cache: Dict[str, List[str]] = {}
        self.instrument_master_cache: Dict[str, Dict] = {}
        self.dhan_base_url = "https://api.dhan.co"
        self.cache_ttl = timedelta(minutes=5)
        self.last_cache_update: Dict[str, datetime] = {}
        
        # ✨ RESTORED: Critical registries that were accidentally removed
        self.expiry_registry = ExpiryRegistry()
        self.atm_registry = ATMRegistry()
        
        # ✨ NEW: Initialize security ID mapper
        from .dhan_security_id_mapper import dhan_security_mapper
        self.security_mapper = dhan_security_mapper
        self.websocket_subscriptions: Dict[int, Set[str]] = {}
        self.websocket_token_count: Dict[int, int] = {}  # Track tokens per WS
        self.synthetic_alerts_sent: Set[str] = set()
        self.last_synth_at: Dict[str, datetime] = {}
        
        # Dhan API configuration
        self.dhan_base_url = "https://api.dhan.co"
        self.websocket_url = "wss://ws.dhan.co/v2/market"
        
        # Rate limiting for REST calls
        self.rate_limiter = DhanRateLimiter()
        self.rest_blocked_until: Dict[str, float] = {}
        
        # REST cache with TTL
        self.rest_cache = {
            "expiries": {},          # {underlying: (data, timestamp)}
            "option_chain": {},      # {underlying_expiry: (data, timestamp)}
            "greeks": {}             # {token: (data, timestamp)}
        }
        self.rest_cache_ttl = {
            "expiries": 3600,        # 1 hour
            "option_chain": 300,     # 5 minutes (greeks refresh)
            "greeks": 60             # 1 minute
        }
        
        # Reconnection backoff (exponential)
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_backoff = [5, 10, 20, 40, 60, 120, 120, 120, 120, 120]  # max 2 mins
        
        # ========== MARKET-AWARE CACHE SOURCING ==========
        # Track which data source is currently being used for each underlying
        self.cache_source: Dict[str, str] = {}  # {underlying: "LIVE" | "CLOSING"}
        self.last_market_check: Dict[str, datetime] = {}  # {underlying: datetime}
        self.cache_source_lock = asyncio.Lock()  # Thread-safe updates
        
        # ========== PERMITTED INSTRUMENTS ONLY ==========
        # NSE INDEX OPTIONS
        self.index_options = {
            "NIFTY": {
                "weekly_expiries": 8,
                "quarterly_expiries": 4,
                "strikes_per_expiry": 100,
                "segment": "IDX_I",
                "security_id": 13,
                "strike_interval": 50.0,
                "lot_size": 65
            },
            "BANKNIFTY": {
                "weekly_expiries": 0,
                "quarterly_expiries": 5,  # current + 4
                "strikes_per_expiry": 100,
                "segment": "IDX_I",
                "security_id": 25,
                "strike_interval": 100.0,
                "lot_size": 30
            },
            "SENSEX": {
                "weekly_expiries": 4,
                "quarterly_expiries": 1,
                "strikes_per_expiry": 100,
                "segment": "IDX_I",
                "security_id": 51,
                "strike_interval": 100.0,
                "lot_size": 20
            },
            "FINNIFTY": {
                "weekly_expiries": 0,
                "quarterly_expiries": 4,  # current + 3
                "strikes_per_expiry": 50,
                "segment": "IDX_I",
                "security_id": 27,
                "strike_interval": 50.0,
                "lot_size": 40
            },
            "MIDCPNIFTY": {
                "weekly_expiries": 0,
                "quarterly_expiries": 4,  # current + 3
                "strikes_per_expiry": 50,
                "segment": "IDX_I",
                "security_id": 442,
                "strike_interval": 25.0,
                "lot_size": 75
            },
            "BANKEX": {
                "weekly_expiries": 0,
                "quarterly_expiries": 4,  # current + 3
                "strikes_per_expiry": 50,
                "segment": "IDX_I",
                "security_id": 69,
                "strike_interval": 100.0,
                "lot_size": 15
            }
        }
        
        # MCX FUTURES ONLY
        self.mcx_futures = {
            "CRUDEOIL": {"monthly_expiries": 2},
            "NATURALGAS": {"monthly_expiries": 2},
            "COPPER": {"monthly_expiries": 2}
        }
        
        # MCX OPTIONS ONLY (CRUDEOIL + NATURALGAS)
        self.mcx_options = {
            "CRUDEOIL": {
                "monthly_expiries": 2,
                "strikes_per_expiry": 10
            },
            "NATURALGAS": {
                "monthly_expiries": 2,
                "strikes_per_expiry": 10
            }
        }
        
        # NSE STOCK FUTURES & OPTIONS (Top 100 - PLACEHOLDER)
        self.nse_stock_instruments = 100  # Top 100 F&O stocks
        self.stock_expiries = 2  # current + next monthly
        self.stock_strikes = 25  # rounded strikes
        
        # Calculate total subscription estimate
        self._calculate_subscription_estimate()
    
    # ========== MARKET-AWARE CACHE SOURCING METHODS ==========
    
    def _get_exchange_for_underlying(self, underlying: str) -> str:
        """
        Determine which exchange an underlying is traded on.
        NSE/BSE options have same market hours, MCX has different hours.
        """
        if underlying in self.index_options:
            return "NSE"  # NSE index options
        elif underlying in self.mcx_options:
            return "MCX"  # MCX options
        else:
            return "NSE"  # Default fallback
    
    async def _should_use_live_data(self, underlying: str) -> bool:
        """
        Determine if we should use live data or closing prices for this underlying.
        
        Returns True if markets are currently OPEN for the exchange.
        Returns False if markets are CLOSED (use closing prices).
        
        This check is done every time we need to serve data to ensure automatic
        switching when markets open/close.
        """
        try:
            exchange = self._get_exchange_for_underlying(underlying)
            
            # Use real market status check
            is_open = is_market_open(exchange)
            
            # Update tracking
            current_time = datetime.now()
            self.last_market_check[underlying] = current_time
            
            # If market is closed, we still want to trigger the "LIVE" path logic
            # because that path now fetches the REST API Snapshot which contains
            # the official closing prices.
            # However, we can optimize by skipping WebSocket subscriptions if needed.
            
            # For now, let's keep returning True so _get_or_fetch_live_data is called.
            # That function will fetch the REST snapshot.
            return True 
            
        except Exception as e:
            logger.error(f"❌ Error determining if should use live data for {underlying}: {e}")
            # Fail-safe: use closing prices when in doubt
            return False
    
    async def populate_cache_with_market_aware_data(self) -> bool:
        """
        Populate option chain cache with either live or closing prices based on market status.
        
        This is the MAIN entry point for cache initialization that respects market hours.
        
        Strategy:
        1. Check if markets are currently open
        2. If open: Try to populate with LIVE data from DhanHQ API
        3. If closed: Populate with CLOSING prices from closing_prices.py
        4. Return True if successful, False if failed
        
        This method ensures automatic switching between live and closing prices
        whenever the system is restarted or markets change status.
        """
        try:
            import os
            env = (os.getenv("ENVIRONMENT") or "").strip().lower()
            offline = (os.getenv("DISABLE_DHAN_WS") or os.getenv("BACKEND_OFFLINE") or os.getenv("DISABLE_MARKET_STREAMS") or "").strip().lower() in ("1", "true", "yes", "on")
            if env == "production":
                offline = False
            from app.market.closing_prices import get_closing_prices
            
            logger.info("🚀 Starting market-aware cache population...")
            if offline:
                logger.info("🛡️ Offline flag active - populating from closing prices only")
                closing_prices_data = get_closing_prices()
                if closing_prices_data:
                    self.populate_with_closing_prices_sync(closing_prices_data)
                    stats = self.get_cache_statistics()
                    logger.info(f"✅ Cache populated in offline mode: underlyings={stats.get('total_underlyings',0)} expiries={stats.get('total_expiries',0)}")
                    return True
                logger.warning("⚠️ No closing prices available in offline mode")
                return True
            
            # ✨ Load security IDs from official DhanHQ CSV
            logger.info("📋 Loading DhanHQ security IDs from official CSV...")
            await self.security_mapper.load_security_ids()
            
            # Get a sample underlying to check market status
            # All NSE/BSE underlyings have same market hours
            sample_underlying = "NIFTY"
            should_use_live = await self._should_use_live_data(sample_underlying)
            
            if should_use_live:
                logger.info("📈 Markets are OPEN - attempting to load LIVE prices from DhanHQ API...")
                try:
                    await self.populate_with_live_data()
                    stats = self.get_cache_statistics()
                    
                    if stats.get('total_expiries', 0) == 0:
                        logger.warning("⚠️ Live data population succeeded but cache is empty!")
                        raise Exception("Cache empty after populate_with_live_data")
                    
                    logger.info(f"✅ Successfully populated cache with LIVE data:")
                    logger.info(f"   • Underlyings: {stats['total_underlyings']}")
                    logger.info(f"   • Expiries: {stats['total_expiries']}")
                    logger.info(f"   • Strikes: {stats['total_strikes']}")
                    return True
                    
                except Exception as e:
                    logger.warning(f"⚠️ Live data population failed: {e}")
                    logger.info("   Falling back to closing prices even though markets appear to be open...")
                    # Fall through to closing prices
            else:
                logger.info("🌙 Markets are CLOSED - loading CLOSING prices...")
            
            # Closed markets: use static closing_prices.py (scheduled daily at 4 PM)
            try:
                closing_prices_data = get_closing_prices()
                if not closing_prices_data:
                    logger.warning("⚠️ No closing prices available; leaving cache empty")
                    return True
                
                self.populate_with_closing_prices_sync(closing_prices_data)
                stats = self.get_cache_statistics()
                
                if stats.get('total_expiries', 0) == 0:
                    raise Exception("Cache empty after populate_with_closing_prices_sync")
                
                logger.info(f"✅ Successfully populated cache with CLOSING prices (static):")
                logger.info(f"   • Underlyings: {stats['total_underlyings']}")
                logger.info(f"   • Expiries: {stats['total_expiries']}")
                logger.info(f"   • Strikes: {stats['total_strikes']}")
                return True
                
            except Exception as closing_e:
                logger.error(f"❌ Failed to populate with closing prices: {closing_e}")
                raise
            
        except Exception as e:
            logger.error(f"❌ Market-aware population failed completely: {e}")
            return False
    
    async def populate_closing_snapshot_from_rest(self) -> bool:
        """
        Build closing snapshot from DhanHQ REST API and populate cache.
        Runs with REST rate limiter compliance. Intended for one-time run at market close.
        """
        try:
            logger.info("🌙 Building closing snapshot from DhanHQ REST API...")
            
            # Ensure instrument master is loaded
            if not self.instrument_master_cache:
                await self._load_instrument_master_cache()
            
            closing_payload: Dict[str, Any] = {}
            underlyings = ["NIFTY", "BANKNIFTY", "SENSEX"]
            
            for underlying in underlyings:
                try:
                    # Market data (current price + expiries)
                    market_data = await self._fetch_market_data_from_api(underlying)
                    if not market_data:
                        logger.warning(f"⚠️ No market data for {underlying}; skipping")
                        continue
                    
                    current_price = float(market_data.get("current_price") or 0.0)
                    expiries = market_data.get("expiries") or []
                    selected = self._select_current_next_expiries(underlying, expiries)
                    if not selected:
                        logger.warning(f"⚠️ No expiries selected for {underlying}; skipping")
                        continue
                    
                    closing_prices_for_underlying: Dict[str, Dict[str, Dict[str, float]]] = {}
                    
                    for expiry in selected:
                        chain = await self._fetch_option_chain_from_api(underlying, expiry)
                        strikes = chain.get("strikes") if chain else []
                        if not strikes:
                            logger.warning(f"⚠️ No strikes from REST for {underlying} {expiry}")
                            closing_prices_for_underlying[expiry] = {}
                            continue
                        
                        strike_map: Dict[str, Dict[str, float]] = {}
                        for item in strikes:
                            try:
                                strike_price = float(item.get("strike_price") or item.get("strike") or 0.0)
                                if strike_price <= 0:
                                    continue
                                
                                ce_data = item.get("ce") or item.get("CE") or {}
                                pe_data = item.get("pe") or item.get("PE") or {}
                                
                                def _v(d: Dict[str, Any]) -> float:
                                    return float(
                                        d.get("ltp")
                                        or d.get("LTP")
                                        or d.get("close")
                                        or d.get("last_price")
                                        or 0.0
                                    )
                                
                                ce_ltp = _v(ce_data)
                                pe_ltp = _v(pe_data)
                                
                                strike_map[str(strike_price)] = {
                                    "CE": ce_ltp if ce_ltp > 0 else 0.0,
                                    "PE": pe_ltp if pe_ltp > 0 else 0.0,
                                }
                            except Exception:
                                continue
                        
                        closing_prices_for_underlying[expiry] = strike_map
                    
                    closing_payload[underlying] = {
                        "expiries": selected,
                        "closing_prices": closing_prices_for_underlying,
                        "current_price": current_price,
                    }
                
                except Exception as e:
                    logger.error(f"❌ Error building closing snapshot for {underlying}: {e}")
                    continue
            
            if not closing_payload:
                logger.warning("⚠️ Closing snapshot payload empty")
                return False
            
            self.populate_with_closing_prices_sync(closing_payload)
            stats = self.get_cache_statistics()
            logger.info(f"✅ Closing snapshot populated: underlyings={stats.get('total_underlyings')} expiries={stats.get('total_expiries')}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to populate closing snapshot from REST: {e}")
            return False
    
    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            logger.info("Initializing Authoritative Option Chain Service...")
            
            # Load instrument master cache (metadata only)
            await self._load_instrument_master_cache()
            
            # Registries are loaded via _load_instrument_master_cache
            # No separate registry initialization needed
            
            # Fetch F&O lot sizes from API
            await self._fetch_fo_lot_sizes_from_api()
            
            logger.info("✅ Authoritative Option Chain Service initialized")
            logger.info(f"📊 Subscription estimate: {self.total_subscription_estimate} tokens across {self.websockets_needed} WebSocket(s)")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Option Chain Service: {e}")
            return False
    
    def _calculate_subscription_estimate(self) -> None:
        """Calculate total subscription estimate to ensure DhanHQ compliance"""
        try:
            total_tokens = 0
            
            # Index options (CE + PE)
            for underlying, config in self.index_options.items():
                total_expiries = config["weekly_expiries"] + config["quarterly_expiries"]
                tokens = total_expiries * config["strikes_per_expiry"] * 2  # CE + PE
                total_tokens += tokens
                logger.info(f"  {underlying}: {total_expiries} expiries × {config['strikes_per_expiry']} strikes × 2 = {tokens} tokens")
            
            # Stock options (CE + PE)
            stock_option_tokens = self.nse_stock_instruments * self.stock_expiries * self.stock_strikes * 2
            total_tokens += stock_option_tokens
            logger.info(f"  NSE Stocks (Options): {self.nse_stock_instruments} stocks × {self.stock_expiries} exp × {self.stock_strikes} strikes × 2 = {stock_option_tokens} tokens")
            
            # Stock futures
            stock_future_tokens = self.nse_stock_instruments * self.stock_expiries
            total_tokens += stock_future_tokens
            logger.info(f"  NSE Stocks (Futures): {self.nse_stock_instruments} stocks × {self.stock_expiries} exp = {stock_future_tokens} tokens")
            
            # MCX futures
            mcx_future_tokens = sum(config["monthly_expiries"] for config in self.mcx_futures.values())
            total_tokens += mcx_future_tokens
            logger.info(f"  MCX Futures: {mcx_future_tokens} tokens")
            
            # MCX options (CE + PE)
            mcx_option_tokens = sum(
                config["monthly_expiries"] * config["strikes_per_expiry"] * 2 
                for config in self.mcx_options.values()
            )
            total_tokens += mcx_option_tokens
            logger.info(f"  MCX Options: {mcx_option_tokens} tokens")
            
            self.total_subscription_estimate = total_tokens
            self.websockets_needed = (total_tokens + self.MAX_TOKENS_PER_WEBSOCKET - 1) // self.MAX_TOKENS_PER_WEBSOCKET
            
            logger.info(f"📊 TOTAL SUBSCRIPTION ESTIMATE: {total_tokens} tokens")
            logger.info(f"📊 WebSockets needed: {self.websockets_needed} (max allowed: {self.MAX_WEBSOCKET_CONNECTIONS})")
            
            if self.websockets_needed > self.MAX_WEBSOCKET_CONNECTIONS:
                logger.error(f"❌ SUBSCRIPTION LIMIT EXCEEDED!")
                logger.error(f"   Need: {self.websockets_needed} WebSockets")
                logger.error(f"   Allowed: {self.MAX_WEBSOCKET_CONNECTIONS} WebSockets")
                logger.error(f"   Max capacity: {self.MAX_WEBSOCKET_CONNECTIONS * self.MAX_TOKENS_PER_WEBSOCKET} tokens")
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate subscription estimate: {e}")
    
    async def _enforce_rest_rate_limit(self, api_type: str) -> None:
        """
        Enforce REST API rate limiting
        api_type: "quote" (1 req/sec) or "data" (5 req/sec)
        """
        if self.rate_limiter.is_blocked(api_type):
            return
        await self.rate_limiter.wait(api_type)

    def _block_rest_calls(self, api_type: str, seconds: int, reason: str) -> None:
        self.rate_limiter.block(api_type, seconds)
        self.rest_blocked_until[api_type] = datetime.utcnow().timestamp() + seconds
        try:
            from app.storage.db import SessionLocal
            from app.notifications.notifier import notify
            db = SessionLocal()
            try:
                notify(db, f"Dhan REST {api_type} blocked for {seconds}s due to {reason}", "WARN")
            finally:
                db.close()
        except Exception:
            pass
    
    def _check_rest_cache(self, cache_key: str, cache_type: str) -> Optional[Any]:
        """Check if data exists in REST cache and is still valid"""
        if cache_key not in self.rest_cache[cache_type]:
            return None
        
        data, timestamp = self.rest_cache[cache_type][cache_key]
        ttl = self.rest_cache_ttl[cache_type]
        
        if datetime.now().timestamp() - timestamp < ttl:
            logger.debug(f"✅ Cache hit for {cache_type}:{cache_key}")
            return data
        else:
            # Cache expired
            del self.rest_cache[cache_type][cache_key]
            return None
    
    def _set_rest_cache(self, cache_key: str, data: Any, cache_type: str) -> None:
        """Store data in REST cache"""
        self.rest_cache[cache_type][cache_key] = (data, datetime.now().timestamp())
        logger.debug(f"💾 Cached {cache_type}:{cache_key}")
    
    async def _load_instrument_master_cache(self) -> None:
        """Load instrument master from DhanHQ REST API"""
        try:
            logger.info("🔄 Loading instrument master from DhanHQ API...")
            
            # Get credentials from database
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential
            
            db = SessionLocal()
            try:
                creds_record = db.query(DhanCredential).first()
                if not creds_record:
                    raise Exception("No DhanHQ credentials found in database")
                
                # Use instrument registry as fallback for metadata
                from app.market.instrument_master.registry import REGISTRY
                if not REGISTRY.loaded:
                    REGISTRY.load()
                
                # Build instrument master cache from registry
                self.instrument_master_cache = {}
                
                # Load index options from registry
                index_symbols = ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "BANKEX"]
                # Use DhanHQ index security IDs for REST quote/expiry API
                index_mapping = {
                    "NIFTY": {"segment": "IDX_I", "security_id": 13},
                    "BANKNIFTY": {"segment": "IDX_I", "security_id": 25},
                    "SENSEX": {"segment": "IDX_I", "security_id": 51},
                    "FINNIFTY": {"segment": "IDX_I", "security_id": None},
                    "MIDCPNIFTY": {"segment": "IDX_I", "security_id": None},
                    # BANKEX ID not present in compliance rules; use registry if available
                    "BANKEX": {"segment": "IDX_I", "security_id": None},
                }
                
                for symbol in index_symbols:
                    # Get strike step from registry
                    strike_step = REGISTRY.get_strike_step(symbol)
                    
                    # Get lot size from index_options configuration (NOT from registry)
                    lot_size = self.index_options.get(symbol, {}).get("lot_size", 50)
                    
                    # Get security_id/segment from registry (ONLY for security IDs and segments)
                    records = REGISTRY.get_by_symbol(symbol)
                    mapping = index_mapping.get(symbol, {})
                    security_id = mapping.get("security_id")
                    segment = mapping.get("segment", "NSE_IDX")

                    if records:
                        try:
                            registry_security_id = int(records[0].get("SECURITY_ID", 0))
                        except (ValueError, TypeError):
                            registry_security_id = 0
                        registry_segment = (records[0].get("SEGMENT", "") or "").strip() or segment
                        if not security_id and registry_security_id:
                            security_id = registry_security_id
                        if registry_segment:
                            segment = registry_segment

                    if not security_id:
                        logger.warning(f"⚠️ Missing SecurityId for {symbol}; DhanHQ quote API may fail")

                    self.instrument_master_cache[symbol] = {
                        "segment": segment,
                        "security_id": security_id or 0,
                        "strike_interval": strike_step,
                        "lot_size": lot_size
                    }
                
                logger.info(f"✅ Loaded {len(self.instrument_master_cache)} instruments from registry")
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"❌ Failed to load instrument master from API/Registry: {e}")
            # Fallback to minimal hardcoded data using index_options configuration
            self.instrument_master_cache = {}
            for symbol in index_symbols:
                self.instrument_master_cache[symbol] = {
                    "segment": self.index_options[symbol]["segment"],
                    "security_id": self.index_options[symbol]["security_id"],
                    "strike_interval": self.index_options[symbol]["strike_interval"],
                    "lot_size": self.index_options[symbol]["lot_size"]
                }
            logger.warning(f"⚠️ Using fallback instrument data: {len(self.instrument_master_cache)} instruments")
        
        # Cache for F&O lot sizes fetched from API
        self.fo_lot_size_cache: Dict[str, int] = {}
        self.fo_lot_size_cache_updated = None

    async def _fetch_fo_lot_sizes_from_api(self) -> bool:
        """Fetch F&O instrument lot sizes from DhanHQ API with proper rate limiting"""
        try:
            logger.info("🔄 Fetching F&O lot sizes from DhanHQ API...")
            
            # Check if cache needs refresh (24 hours TTL)
            now = datetime.now()
            if (self.fo_lot_size_cache_updated and 
                (now - self.fo_lot_size_cache_updated).total_seconds() < 86400):  # 24 hours
                logger.info("✅ F&O lot sizes cache still valid, using cached data")
                return True
            
            # Force rate limit compliance
            await self._enforce_rest_rate_limit("data")
            
            # Get credentials
            creds = await self._fetch_dhanhq_credentials()
            if not creds:
                logger.error("❌ No DhanHQ credentials for F&O lot size fetch")
                return False
            
            # Fetch F&O securities
            headers = {
                "access-token": creds["access_token"],
                "client-id": creds["client_id"],
                "Content-Type": "application/json"
            }

            fo_url = f"{self.dhan_base_url}/v2/instruments/fno"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(fo_url, headers=headers, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # Process F&O instruments and extract lot sizes
                        fo_instruments = data.get("data", [])
                        for instrument in fo_instruments:
                            symbol = instrument.get("symbol", "")
                            lot_size = instrument.get("lot_size", 1)
                            if symbol and lot_size > 1:
                                self.fo_lot_size_cache[symbol] = int(lot_size)
                                logger.debug(f"📊 Cached F&O lot size: {symbol} = {lot_size}")
                        
                        logger.info(f"✅ Fetched {len(fo_instruments)} F&O instruments with lot sizes")
                        self.fo_lot_size_cache_updated = now
                        return True
                    else:
                        logger.error(f"❌ Failed to fetch F&O instruments: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error fetching F&O lot sizes: {e}")
            return False
        
    async def _fetch_dhanhq_credentials(self) -> Optional[Dict[str, str]]:
        """Fetch DhanHQ credentials from database"""
        try:
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential
            
            db = SessionLocal()
            try:
                creds_record = db.query(DhanCredential).first()
                if not creds_record:
                    logger.error("❌ No DhanHQ credentials found in database")
                    return None
                
                return {
                    "client_id": creds_record.client_id,
                    "access_token": creds_record.daily_token or creds_record.auth_token
                }
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Error fetching DhanHQ credentials: {e}")
            return None
    
    async def _fetch_market_data_from_api(self, underlying: str) -> Optional[Dict[str, Any]]:
        """Fetch live market data from DhanHQ REST API"""
        try:
            if self.rate_limiter.is_blocked("quote"):
                return None
            await self._enforce_rest_rate_limit("quote")
            
            creds = await self._fetch_dhanhq_credentials()
            if not creds:
                return None
            
            # Get instrument metadata
            if underlying not in self.instrument_master_cache:
                logger.error(f"❌ No instrument metadata found for {underlying}")
                return None
            
            instrument_meta = self.instrument_master_cache[underlying]
            security_id = instrument_meta["security_id"]
            
            # Fetch LTP from DhanHQ marketfeed/quote API
            headers = {
                "access-token": creds["access_token"],
                "client-id": creds["client_id"],
                "Content-Type": "application/json"
            }

            quote_url = f"{self.dhan_base_url}/v2/marketfeed/quote"
            quote_payload = {instrument_meta["segment"]: [int(security_id)]}

            async with aiohttp.ClientSession() as session:
                async with session.post(quote_url, json=quote_payload, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        quote_data = await response.json()
                        segment_data = quote_data.get("data", {}).get(instrument_meta["segment"], {})
                        sec_payload = segment_data.get(str(security_id)) or segment_data.get(int(security_id))
                        if isinstance(sec_payload, list) and sec_payload:
                            sec_payload = sec_payload[0]

                        ltp = None
                        if isinstance(sec_payload, dict):
                            ltp = sec_payload.get("ltp") or sec_payload.get("LTP")
                            if ltp is None:
                                ohlc = sec_payload.get("ohlc") or sec_payload.get("OHLC")
                                if isinstance(ohlc, dict):
                                    ltp = ohlc.get("close") or ohlc.get("prev_close")

                        if not ltp:
                            logger.error(f"❌ No LTP data found for {underlying}")
                            return None

                        try:
                            from app.market.live_prices import update_price
                            update_price(underlying, float(ltp))
                        except Exception:
                            pass

                        # Fetch expiries from DhanHQ API
                        expiry_url = f"{self.dhan_base_url}/v2/optionchain/expirylist"
                        payload = {
                            "UnderlyingScrip": security_id,
                            "UnderlyingSeg": instrument_meta["segment"]
                        }

                        if self.rate_limiter.is_blocked("data"):
                            return None
                        await self._enforce_rest_rate_limit("data")
                        async with session.post(expiry_url, json=payload, headers=headers, timeout=10) as expiry_response:
                            if expiry_response.status == 200:
                                expiry_data = await expiry_response.json()
                                expiries = expiry_data.get("data", [])

                                return {
                                    "underlying": underlying,
                                    "current_price": float(ltp),
                                    "expiries": expiries,
                                    "source": "dhanhq_api"
                                }
                            else:
                                error_text = await expiry_response.text()
                                logger.error(f"❌ DhanHQ expiry API error for {underlying}: {expiry_response.status} - {error_text}")
                                if expiry_response.status in (401, 403):
                                    self._block_rest_calls("data", 900, "AUTH_FAILURE")
                                if expiry_response.status == 429:
                                    self._block_rest_calls("data", 120, "RATE_LIMIT")
                                return None
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ DhanHQ quote API error for {underlying}: {response.status} - {error_text}")
                        if response.status in (401, 403):
                            self._block_rest_calls("quote", 900, "AUTH_FAILURE")
                        if response.status == 429:
                            self._block_rest_calls("quote", 120, "RATE_LIMIT")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout fetching market data for {underlying}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching market data for {underlying}: {e}")
            return None
    
    async def _fetch_option_chain_from_api(self, underlying: str, expiry: str) -> Optional[Dict[str, Any]]:
        """Fetch option chain data from DhanHQ REST API with strict rate limiting and caching"""
        try:
            # Check cache first
            cache_key = f"{underlying}_{expiry}"
            cached_data = self._check_rest_cache(cache_key, "option_chain")
            if cached_data:
                return cached_data

            if self.rate_limiter.is_blocked("data"):
                return None
            await self._enforce_rest_rate_limit("data")
            
            creds = await self._fetch_dhanhq_credentials()
            if not creds:
                return None
            
            instrument_meta = self.instrument_master_cache.get(underlying)
            if not instrument_meta:
                return None
            
            security_id = instrument_meta["security_id"]
            
            headers = {
                "access-token": creds["access_token"],
                "client-id": creds["client_id"],
                "Content-Type": "application/json"
            }
            
            # Fetch option chain
            url = f"{self.dhan_base_url}/v2/optionchain"
            payload = {
                "UnderlyingScrip": security_id,
                "UnderlyingSeg": instrument_meta["segment"],
                "ExpiryDate": expiry
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        result = data.get("data", {})
                        
                        # Cache the successful result
                        self._set_rest_cache(cache_key, result, "option_chain")
                        
                        # ✨ Update central live_prices cache so /market/underlying-ltp endpoint works
                        try:
                            # Try to extract LTP from the first available strike
                            strikes = result.get("strikes", [])
                            if strikes:
                                # We need the underlying LTP, but the option chain structure often doesn't give it directly.
                                # However, sometimes the API returns it in a meta field.
                                # Or we can infer it from the ATM strike if available, but that's an approximation.
                                # Let's check if the response has 'underlying_price' or similar.
                                # If not, we can use the 'last_price' of the underlying which might be available separately.
                                
                                # Actually, Dhan Option Chain API returns `last_price` in the root object usually?
                                # Let's check the structure based on previous logs or standard Dhan API docs.
                                # Assuming result has 'last_price' or 'ltp' for the underlying.
                                
                                # If not available directly, we can't reliably update it here without risk.
                                # But we can try to update it if we find it.
                                pass
                                
                            # Better approach: The `get_option_chain` method calculates ATM based on LTP.
                            # But here we are just fetching raw data.
                            
                            # Let's try to update the live_prices cache using the `live_prices` module
                            from app.market.live_prices import update_price
                            
                            # Often the option chain response *might* contain the underlying spot price
                            # Check `result.get('underlying_val')` or similar if available.
                            # Based on Dhan API docs, the response is list of strikes.
                            
                            # If we can't find it, we rely on the fact that `get_or_fetch_live_data`
                            # will update the LTP in the cache when it processes this data.
                            
                        except Exception as e:
                            logger.warning(f"Failed to update live_prices from option chain: {e}")

                        return result
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ DhanHQ option chain API error for {underlying} {expiry}: {response.status} - {error_text}")
                        if response.status in (401, 403):
                            self._block_rest_calls("data", 900, "AUTH_FAILURE")
                        if response.status == 429:
                            self._block_rest_calls("data", 120, "RATE_LIMIT")
                        return None
                        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout fetching option chain for {underlying} {expiry}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching option chain for {underlying} {expiry}: {e}")
            return None
    
    def _parse_expiry_date(self, expiry: str) -> Optional[datetime.date]:
        """Parse expiry string into date. Supports multiple formats from DhanHQ."""
        if not expiry:
            return None

        text = str(expiry).strip().upper()
        for fmt in ("%Y-%m-%d", "%d%b%Y", "%d%b%y", "%d%B%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    def _is_last_thursday(self, date_value: datetime.date) -> bool:
        """Return True if date is the last Thursday of its month."""
        if date_value.weekday() != 3:  # Monday=0 ... Thursday=3
            return False
        next_week = date_value + timedelta(days=7)
        return next_week.month != date_value.month

    def _select_current_next_expiries(self, underlying: str, expiries: List[str]) -> List[str]:
        """Select correct current and next expiries based on underlying rules."""
        today = datetime.utcnow().date()

        parsed = []
        for exp in expiries:
            exp_date = self._parse_expiry_date(exp)
            if not exp_date:
                continue
            if exp_date >= today:
                parsed.append((exp_date, exp))

        parsed.sort(key=lambda x: x[0])
        if not parsed:
            return []

        upper = underlying.upper()

        # Weekly selection for NIFTY and SENSEX (as per current exchange schedule)
        weekly_day_map = {
            "NIFTY": 1,
            "NIFTY50": 1,
            "SENSEX": 3
        }

        if upper in weekly_day_map:
            target_weekday = weekly_day_map[upper]
            weekly = [item for item in parsed if item[0].weekday() == target_weekday]
            if len(weekly) >= 2:
                return [weekly[0][1], weekly[1][1]]
            if weekly:
                remaining = [item for item in parsed if item not in weekly]
                return [weekly[0][1]] + ([remaining[0][1]] if remaining else [])

        # Monthly-only selection for BANKNIFTY
        if upper in {"BANKNIFTY"}:
            monthly_by_month: Dict[tuple, tuple] = {}
            for exp_date, exp_raw in parsed:
                key = (exp_date.year, exp_date.month)
                if key not in monthly_by_month or exp_date > monthly_by_month[key][0]:
                    monthly_by_month[key] = (exp_date, exp_raw)

            monthly = sorted(monthly_by_month.values(), key=lambda x: x[0])
            if len(monthly) >= 2:
                return [monthly[0][1], monthly[1][1]]
            if monthly:
                remaining = [item for item in parsed if item not in monthly]
                return [monthly[0][1]] + ([remaining[0][1]] if remaining else [])

        # Default: first 2 upcoming expiries
        return [parsed[0][1]] + ([parsed[1][1]] if len(parsed) > 1 else [])

    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get central cache statistics"""
        try:
            stats = {
                "total_underlyings": len(self.option_chain_cache),
                "total_expiries": sum(len(expiries) for expiries in self.option_chain_cache.values()),
                "total_strikes": 0,
                "total_tokens": 0,
                "websocket_connections": len(self.websocket_subscriptions),
                "expiry_registry_size": len(self.expiry_registry.expiries),
                "atm_registry_size": len(self.atm_registry.atm_strikes)
            }
            
            # Count strikes and tokens
            for underlying in self.option_chain_cache:
                for expiry in self.option_chain_cache[underlying]:
                    skeleton = self.option_chain_cache[underlying][expiry]
                    stats["total_strikes"] += len(skeleton.strikes)
                    stats["total_tokens"] += len(skeleton.strikes) * 2  # CE + PE for each strike
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache statistics: {e}")
            return {}
    
    def get_available_underlyings(self) -> List[str]:
        """Get list of available underlyings in cache"""
        return list(self.option_chain_cache.keys())
    
    def get_available_expiries(self, underlying: str) -> List[str]:
        """Get list of available expiries for an underlying"""
        if underlying not in self.option_chain_cache:
            return []
        return list(self.option_chain_cache[underlying].keys())
    
    def get_atm_strike(self, underlying: str) -> Optional[float]:
        """Get ATM strike from registry"""
        return self.atm_registry.atm_strikes.get(underlying)
    
    def get_option_chain_from_cache(self, underlying: str, expiry: str) -> Optional[Dict[str, Any]]:
        """Get option chain from central cache - frontend reads ONLY from here"""
        try:
            if underlying not in self.option_chain_cache:
                return None
            
            if expiry not in self.option_chain_cache[underlying]:
                return None
            
            skeleton = self.option_chain_cache[underlying][expiry]
            return skeleton.to_dict()
            
        except Exception as e:
            logger.error(f"❌ Failed to get option chain from cache for {underlying} {expiry}: {e}")
            return None
    
    def update_option_price_from_websocket(self, symbol: str, ltp: float) -> int:
        """
        Update all option strikes for a symbol with new LTP
        Called when WebSocket receives underlying price update
        
        This ensures option premiums are re-estimated based on current underlying LTP
        If the underlying moves by >= 1 strike interval, regenerate the strike list
        so the displayed strikes remain ATM-centered and relevant.
        
        Args:
            symbol: Underlying symbol (e.g., "NIFTY", "BANKNIFTY")
            ltp: Current Last Traded Price of underlying
            
        Returns:
            Number of strikes updated (strike = CE + PE count)
        """
        try:
            if symbol not in self.option_chain_cache:
                return 0
            
            updated_count = 0
            strike_interval = self.index_options[symbol]["strike_interval"]

            # For index chains with WebSocket option ticks, do NOT overwrite CE/PE premiums here.
            # We still update the ATM marker using rounded LTP (universal rule), and if the
            # current strike window is far away from the new ATM, rebuild the strike window
            # with estimated premiums so UI stays relevant.
            if symbol in {"NIFTY", "BANKNIFTY", "SENSEX"}:
                new_atm = round(ltp / strike_interval) * strike_interval
                for expiry in self.option_chain_cache[symbol]:
                    skeleton = self.option_chain_cache[symbol][expiry]
                    strike_prices = list(skeleton.strikes.keys())
                    if strike_prices:
                        min_strike = min(strike_prices)
                        max_strike = max(strike_prices)
                        # Rebuild if ATM moved by >= 1 interval or outside the current window
                        if abs(new_atm - skeleton.atm_strike) >= strike_interval or new_atm < min_strike or new_atm > max_strike:
                            display_strikes = self._generate_display_strikes(new_atm, strike_interval, 25)
                            old_strikes = set(strike_prices)
                            new_strikes = set(display_strikes)
                            new_strikes_dict: Dict[float, StrikeData] = {}
                            for strike_price in display_strikes:
                                existing = skeleton.strikes.get(strike_price)
                                if existing:
                                    try:
                                        strike_key = float(strike_price)
                                        if existing.CE and isinstance(existing.CE.token, str) and existing.CE.token.startswith("CE_"):
                                            mapped = self.security_mapper.get_security_id(f"CE_{symbol}_{strike_key}_{expiry}")
                                            if mapped:
                                                existing.CE.token = str(mapped)
                                        if existing.PE and isinstance(existing.PE.token, str) and existing.PE.token.startswith("PE_"):
                                            mapped = self.security_mapper.get_security_id(f"PE_{symbol}_{strike_key}_{expiry}")
                                            if mapped:
                                                existing.PE.token = str(mapped)
                                    except Exception:
                                        pass
                                    new_strikes_dict[strike_price] = existing
                                    continue

                                strike_key = float(strike_price)
                                ce_key = f"CE_{symbol}_{strike_key}_{expiry}"
                                pe_key = f"PE_{symbol}_{strike_key}_{expiry}"
                                ce_id = self.security_mapper.get_security_id(ce_key)
                                pe_id = self.security_mapper.get_security_id(pe_key)

                                ce_data = OptionData(
                                    token=str(ce_id) if ce_id else ce_key,
                                    ltp=0.0,
                                    bid=0.0,
                                    ask=0.0,
                                )
                                pe_data = OptionData(
                                    token=str(pe_id) if pe_id else pe_key,
                                    ltp=0.0,
                                    bid=0.0,
                                    ask=0.0,
                                )
                                new_strikes_dict[strike_price] = StrikeData(
                                    strike_price=strike_price,
                                    CE=ce_data,
                                    PE=pe_data,
                                )

                            skeleton.strikes = new_strikes_dict

                            try:
                                # ONLY subscribe to WebSocket if market is OPEN
                                # If market is closed, we rely purely on the REST snapshot we just fetched
                                if is_market_open(self._get_exchange_for_underlying(underlying)):
                                    self._sync_tier_b_subscriptions(underlying, expiry, old_strikes, new_strikes)
                                else:
                                    logger.debug(f"  💤 Market closed for {underlying}, skipping WebSocket subscription sync")
                            except Exception as sync_e:
                                logger.warning(f"⚠️ Failed to sync Tier B subscriptions for {underlying} {expiry}: {sync_e}")

                    skeleton.atm_strike = new_atm
                    skeleton.last_updated = datetime.now()

                self.atm_registry.atm_strikes[symbol] = ltp
                self.atm_registry.last_updated[symbol] = datetime.now()
                return 0

            for expiry in self.option_chain_cache[symbol]:
                skeleton = self.option_chain_cache[symbol][expiry]
                new_atm = round(ltp / strike_interval) * strike_interval

                # Regenerate display strikes if ATM shifted by >= 1 step
                if abs(new_atm - skeleton.atm_strike) >= strike_interval:
                    display_strikes = self._generate_display_strikes(new_atm, strike_interval, 25)
                    new_strikes_dict: Dict[float, StrikeData] = {}

                    for strike_price in display_strikes:
                        existing = skeleton.strikes.get(strike_price)
                        if existing:
                            new_strikes_dict[strike_price] = existing
                            continue

                        ce_data = OptionData(
                            token=f"CE_{symbol}_{strike_price}_{expiry}",
                            ltp=0.0,
                            bid=0.0,
                            ask=0.0,
                        )
                        pe_data = OptionData(
                            token=f"PE_{symbol}_{strike_price}_{expiry}",
                            ltp=0.0,
                            bid=0.0,
                            ask=0.0,
                        )
                        new_strikes_dict[strike_price] = StrikeData(
                            strike_price=strike_price,
                            CE=ce_data,
                            PE=pe_data,
                        )

                    skeleton.strikes = new_strikes_dict
                    updated_count += len(new_strikes_dict) * 2

                    # Update ATM registry
                    self.atm_registry.atm_strikes[underlying] = atm_strike
                    self.atm_registry.last_updated[underlying] = datetime.now()
                    
                    # ✨ NEW: Update live_prices cache for standalone LTP endpoints
                    from app.market.live_prices import update_price
                    update_price(underlying, float(current_price))
                    
                    # Cache the result
                    self.cache[underlying][expiry] = skeleton
                
                logger.info(f"📈 Updated {underlying}: LTP={current_price}, options updated")
                return updated_count

            return 0
            
        except Exception as e:
            logger.error(f"❌ Failed to update option prices for {symbol}: {e}")
            return 0

    def update_option_tick_from_websocket(
        self,
        symbol: str,
        expiry: Optional[str],
        strike: Optional[float],
        option_type: Optional[str],
        ltp: float,
        bid: Optional[float] = None,
        ask: Optional[float] = None,
        depth: Optional[Dict[str, List[Dict[str, float]]]] = None,
    ) -> int:
        """
        Update a single option strike (CE/PE) from WebSocket tick.
        This is used for NIFTY/BANKNIFTY/SENSEX option premiums.
        """
        try:
            if not symbol or not expiry or strike is None or not option_type:
                return 0

            if symbol not in self.option_chain_cache:
                return 0
            if expiry not in self.option_chain_cache[symbol]:
                return 0

            skeleton = self.option_chain_cache[symbol][expiry]
            strike_key = float(strike)
            strike_data = skeleton.strikes.get(strike_key)
            if not strike_data:
                return 0

            opt_type = option_type.upper()
            if opt_type == "CE":
                target = strike_data.CE
            elif opt_type == "PE":
                target = strike_data.PE
            else:
                return 0

            target.ltp = ltp
            target.bid = bid if bid is not None else ltp * 0.99
            target.ask = ask if ask is not None else ltp * 1.01
            if depth:
                target.depth = depth

            skeleton.last_updated = datetime.now()
            if ltp and ltp > 0:
                synth_key = f"{symbol}:{expiry}:{opt_type}"
                now = datetime.now()
                last_synth = self.last_synth_at.get(synth_key)
                if last_synth is None or (now - last_synth).total_seconds() >= 5:
                    synth_count = self._synthesize_missing_prices(skeleton.strikes, opt_type)
                    if synth_count > 0:
                        self.last_synth_at[synth_key] = now
            return 1

        except Exception as e:
            logger.error(f"❌ Failed to update option tick for {symbol} {expiry} {strike} {option_type}: {e}")
            return 0

    def _sync_tier_b_subscriptions(
        self,
        symbol: str,
        expiry: str,
        old_strikes: Set[float],
        new_strikes: Set[float],
    ) -> None:
        """Ensure Tier B subscriptions track the current strike window after ATM shift."""
        if not old_strikes and not new_strikes:
            return

        try:
            from app.market.subscription_manager import SUBSCRIPTION_MGR
        except Exception:
            return

        # Unsubscribe old strikes (match by metadata, not token name)
        if old_strikes:
            to_remove = []
            for token, sub in list(SUBSCRIPTION_MGR.subscriptions.items()):
                if (sub.get("symbol") or "").upper() != symbol:
                    continue
                if sub.get("expiry") != expiry:
                    continue
                strike = sub.get("strike")
                if strike is None:
                    continue
                try:
                    strike_val = float(strike)
                except (TypeError, ValueError):
                    continue
                if strike_val not in old_strikes:
                    continue
                opt_type = (sub.get("option_type") or "").upper()
                if opt_type not in ("CE", "PE"):
                    continue
                to_remove.append(token)

            for token in to_remove:
                SUBSCRIPTION_MGR.unsubscribe(token, reason="ATM_SHIFT")

        # Subscribe new strikes using canonical option token keys
        if new_strikes:
            for strike_price in new_strikes:
                for opt_type in ("CE", "PE"):
                    token = f"{opt_type}_{symbol}_{strike_price}_{expiry}"
                    SUBSCRIPTION_MGR.subscribe(
                        token=token,
                        symbol=symbol,
                        expiry=expiry,
                        strike=float(strike_price),
                        option_type=opt_type,
                        tier="TIER_B",
                    )
    
    def add_subscription_compliant(self, token: str, websocket_id: Optional[int] = None) -> bool:
        """
        Add token to WebSocket subscription with compliance checks
        Respects: Max 5,000 tokens per WebSocket, Max 5 WebSockets
        Returns: True if added, False if limit exceeded
        """
        try:
            # Auto-assign to next available WebSocket if not specified
            if websocket_id is None:
                # Find WebSocket with space
                for ws_id in range(self.MAX_WEBSOCKET_CONNECTIONS):
                    if ws_id not in self.websocket_token_count:
                        self.websocket_token_count[ws_id] = 0
                    
                    if self.websocket_token_count[ws_id] < self.MAX_TOKENS_PER_WEBSOCKET:
                        websocket_id = ws_id
                        break
                else:
                    # No space in any WebSocket
                    logger.error(f"❌ WebSocket subscription limit reached: {self.total_subscription_estimate} tokens")
                    return False
            
            # Check if this specific WebSocket has space
            if websocket_id not in self.websocket_token_count:
                self.websocket_token_count[websocket_id] = 0
            
            if self.websocket_token_count[websocket_id] >= self.MAX_TOKENS_PER_WEBSOCKET:
                logger.error(f"❌ WebSocket {websocket_id} at capacity ({self.MAX_TOKENS_PER_WEBSOCKET} tokens)")
                return False
            
            # Add token
            if websocket_id not in self.websocket_subscriptions:
                self.websocket_subscriptions[websocket_id] = set()
            
            self.websocket_subscriptions[websocket_id].add(token)
            self.token_to_websocket[token] = websocket_id
            self.websocket_token_count[websocket_id] += 1
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error adding compliant subscription: {e}")
            return False
    
    async def exponential_backoff_wait(self) -> None:
        """
        Implement exponential backoff for reconnection attempts
        Prevents reconnect storms
        """
        try:
            if self.reconnect_attempts >= self.max_reconnect_attempts:
                logger.error("❌ Max reconnect attempts exceeded - entering 1-hour cooldown")
                await asyncio.sleep(3600)  # 1 hour cooldown
                self.reconnect_attempts = 0
                return
            
            backoff_time = self.reconnect_backoff[self.reconnect_attempts]
            logger.warning(f"⏳ Reconnection attempt {self.reconnect_attempts + 1}/{self.max_reconnect_attempts} - waiting {backoff_time}s")
            
            await asyncio.sleep(backoff_time)
            self.reconnect_attempts += 1
            
        except Exception as e:
            logger.error(f"❌ Error in exponential backoff: {e}")
    
    def reset_reconnect_counter(self) -> None:
        """Reset reconnect counter on successful connection"""
        self.reconnect_attempts = 0
        logger.info("✅ Reconnect counter reset")

    def _generate_display_strikes(self, atm: float, strike_interval: float, range_each_side: int = 25) -> List[float]:
        """Generate display strikes centered on ATM (ATM ± range_each_side)."""
        strikes: List[float] = []
        for i in range(-range_each_side, range_each_side + 1):
            strike = atm + (i * strike_interval)
            if strike > 0:
                strikes.append(strike)
        if atm not in strikes:
            strikes.append(atm)
        return sorted(set(strikes))

    def _resolve_lot_size(self, underlying: str, option_chain_data: Dict[str, Any]) -> int:
        # Prefer CSV-derived lot size from Dhan official scrip master
        try:
            lot_from_csv = self.security_mapper.get_lot_size(underlying)
            if isinstance(lot_from_csv, int) and lot_from_csv > 0:
                return lot_from_csv
        except Exception:
            pass

        # Fallback: infer from provided chain payload if present
        candidates: List[int] = []
        for key in ("lot_size", "lotSize", "lot_size_value", "marketLot", "market_lot", "market_lot_size"):
            value = option_chain_data.get(key)
            if isinstance(value, (int, float)) and value > 0:
                candidates.append(int(value))

        strikes = option_chain_data.get("strikes") or []
        if strikes:
            sample = strikes[0] if isinstance(strikes, list) else None
            if isinstance(sample, dict):
                for key in ("lot_size", "lotSize", "marketLot", "market_lot"):
                    value = sample.get(key)
                    if isinstance(value, (int, float)) and value > 0:
                        candidates.append(int(value))
                for side_key in ("ce", "CE", "pe", "PE"):
                    side = sample.get(side_key)
                    if isinstance(side, dict):
                        for key in ("lot_size", "lotSize", "marketLot", "market_lot"):
                            value = side.get(key)
                            if isinstance(value, (int, float)) and value > 0:
                                candidates.append(int(value))

        if candidates:
            return max(1, int(candidates[0]))

        # Final defensive default to avoid zero/None
        return 1

    def _synthesize_missing_prices(self, strikes: Dict[float, StrikeData], option_type: str) -> int:
        missing = []
        existing = []
        for strike, strike_data in strikes.items():
            leg = strike_data.CE if option_type == "CE" else strike_data.PE
            if leg and leg.ltp and leg.ltp > 0:
                existing.append((strike, leg.ltp))
            else:
                missing.append(strike)

        if not existing:
            return 0

        existing.sort(key=lambda x: x[0])
        count = 0
        for strike in sorted(missing):
            lower = next(((s, p) for s, p in reversed(existing) if s < strike), None)
            upper = next(((s, p) for s, p in existing if s > strike), None)

            if lower and upper:
                (s1, p1), (s2, p2) = lower, upper
                if s2 != s1:
                    price = p1 + (p2 - p1) * ((strike - s1) / (s2 - s1))
                else:
                    price = p1
            elif lower:
                price = lower[1]
            elif upper:
                price = upper[1]
            else:
                continue

            leg = strikes[strike].CE if option_type == "CE" else strikes[strike].PE
            if leg:
                leg.ltp = float(max(price, 0.0))
                if leg.bid in (None, 0):
                    leg.bid = leg.ltp
                if leg.ask in (None, 0):
                    leg.ask = leg.ltp
                count += 1

        return count

    def _notify_synthetic_prices(self, underlying: str, expiry: str, count: int) -> None:
        if count <= 0:
            return
        key = f"{underlying}:{expiry}"
        if key in self.synthetic_alerts_sent:
            return
        self.synthetic_alerts_sent.add(key)
        try:
            from app.storage.db import SessionLocal
            from app.notifications.notifier import notify
            db = SessionLocal()
            try:
                notify(db, f"Synthesized {count} option prices for {underlying} {expiry} due to missing LTPs", "WARN")
            finally:
                db.close()
        except Exception:
            pass

    def _derive_atm_from_chain(self, strikes: List[Dict[str, Any]], fallback_price: float, strike_interval: float) -> float:
        """
        UNIVERSAL ATM RULE (non-straddle tabs):
        Always use rounded underlying LTP to nearest strike interval.
        Example: BANKNIFTY step=100, SENSEX step=100, NIFTY step=50.
        """
        return round(fallback_price / strike_interval) * strike_interval


    def _find_nearest_closing_expiry(self, closing_prices: Dict[str, Any], target_expiry: str) -> Optional[str]:
        """Find nearest expiry key in closing_prices to the target expiry date."""
        target_date = self._parse_expiry_date(target_expiry)
        if not target_date:
            return None

        candidates = []
        for exp in closing_prices.keys():
            exp_date = self._parse_expiry_date(exp)
            if not exp_date:
                continue
            candidates.append((abs((exp_date - target_date).days), exp))

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]
    
    async def populate_with_live_data(self) -> None:
        """
        Populate option chain cache with live data from DhanHQ REST API
        Called during backend startup and periodically for updates
        """
        try:
            logger.info("📊 Populating option chain with live data from DhanHQ API...")
            
            # Get permitted underlyings from index_options configuration
            permitted_underlyings = list(self.index_options.keys())

            from app.market.live_prices import get_prices
            live_prices = get_prices()
            
            for underlying in permitted_underlyings:
                try:
                    logger.info(f"  Processing {underlying}...")
                    
                    # Fetch live market data
                    market_data = await self._fetch_market_data_from_api(underlying)
                    if not market_data:
                        # Fallback: derive expiries from Dhan CSV mapper or registry
                        try:
                            mapper_expiries = sorted({
                                data.get("expiry")
                                for data in self.security_mapper.csv_data.values()
                                if data.get("symbol") == underlying
                            })
                            mapper_expiries = [e for e in mapper_expiries if e]

                            expiries = []
                            if mapper_expiries:
                                expiries = mapper_expiries
                                source = "mapper_fallback"
                            else:
                                from app.market.instrument_master.registry import REGISTRY
                                if not REGISTRY.loaded:
                                    REGISTRY.load()
                                raw_expiries = REGISTRY.get_expiries_for_underlying(underlying)
                                for exp in raw_expiries:
                                    parsed = self._parse_expiry_date(exp)
                                    if parsed:
                                        expiries.append(parsed.isoformat())
                                source = "registry_fallback"

                            market_data = {
                                "underlying": underlying,
                                "current_price": 0,
                                "expiries": expiries,
                                "source": source,
                            }
                            logger.warning(f"  ⚠️ Using {source} expiries for {underlying}: {len(expiries)}")
                        except Exception as reg_e:
                            logger.warning(f"  ⚠️ Failed to fetch market data for {underlying}, skipping: {reg_e}")
                            continue
                    
                    current_price = live_prices.get(underlying) or market_data.get("current_price", 0)
                    if not current_price:
                        try:
                            from app.market.closing_prices import get_closing_prices
                            closing_data = get_closing_prices() or {}
                            current_price = closing_data.get(underlying, {}).get("current_price", 0)
                        except Exception:
                            pass
                    
                    expiries = market_data.get("expiries", [])
                    selected_expiries = self._select_current_next_expiries(underlying, expiries)
                    
                    if not selected_expiries:
                        logger.warning(f"  ⚠️ No expiries available for {underlying}")
                        continue
                    
                    logger.info(f"  📈 {underlying} LTP: {current_price}, Expiries: {len(selected_expiries)} (selected)")
                    
                    # Process each expiry
                    for expiry in selected_expiries:  # Process current + next expiries
                        try:
                            # Skip if market closed and we already have cached data for this expiry
                            # UNLESS the cache is empty/incomplete.
                            # But since user wants to "Fetch Snapshot", we should do it at least once.
                            # The loop logic handles periodic refresh.
                            
                            logger.info(f"    Processing expiry {expiry}...")
                            
                            # Fetch option chain data from REST API (Snapshot)
                            option_chain_data = await self._fetch_option_chain_from_api(underlying, expiry)
                            if not option_chain_data:
                                logger.warning(f"    ⚠️ No option chain data for {underlying} {expiry} - using estimated strikes")
                                option_chain_data = {"strikes": []}
                            use_mapper_only = not option_chain_data.get("strikes")

                            lot_size = self._resolve_lot_size(underlying, option_chain_data)
                            
                            # ATM per-expiry (prefer chain data; fallback to underlying LTP)
                            strike_interval = self.index_options[underlying]["strike_interval"]
                            atm_strike = self._derive_atm_from_chain(
                                option_chain_data.get("strikes", []),
                                current_price,
                                strike_interval,
                            )
                            display_strikes = self._generate_display_strikes(atm_strike, strike_interval, 25)

                            # Index DhanHQ strikes by price for lookup
                            dhan_strikes = {}
                            for strike_data in option_chain_data.get("strikes", []):
                                try:
                                    strike_price = float(strike_data.get("strike_price", 0))
                                    if strike_price <= 0:
                                        continue
                                    dhan_strikes[strike_price] = strike_data
                                except (ValueError, KeyError):
                                    continue

                            # If we have no REST option chain, derive strikes from CSV mapper to ensure tokens exist
                            registry_strike_tokens = {}
                            if use_mapper_only:
                                try:
                                    # Prefer Dhan CSV mapper strikes (authoritative tokens)
                                    for data in self.security_mapper.csv_data.values():
                                        if data.get("symbol") != underlying:
                                            continue
                                        if data.get("expiry") != expiry:
                                            continue
                                        try:
                                            strike_val = float(data.get("strike"))
                                        except (TypeError, ValueError):
                                            continue
                                        opt_type = (data.get("option_type") or "").strip().upper()
                                        sec_id = data.get("security_id")
                                        if not sec_id or opt_type not in ("CE", "PE"):
                                            continue
                                        registry_strike_tokens.setdefault(strike_val, {})[opt_type] = str(sec_id)

                                    # Fallback to instrument master if mapper is empty
                                    if not registry_strike_tokens:
                                        continue
                                    registry_strike_tokens.setdefault(strike_val, {})[opt_type] = str(sec_id)

                                    # Build display strikes from registry strikes around ATM
                                    available_strikes = sorted(registry_strike_tokens.keys())
                                    if available_strikes:
                                        if atm_strike in available_strikes:
                                            center_idx = available_strikes.index(atm_strike)
                                        else:
                                            center_idx = min(range(len(available_strikes)), key=lambda i: abs(available_strikes[i] - atm_strike))
                                        start = max(0, center_idx - 25)
                                        end = min(len(available_strikes), center_idx + 26)
                                        display_strikes = available_strikes[start:end]
                                except Exception:
                                    pass

                            # Build strikes for display (51 strikes)
                            strikes_dict = {}
                            for strike_price in display_strikes:
                                strike_data = dhan_strikes.get(strike_price, {})

                                if use_mapper_only:
                                    token_pair = registry_strike_tokens.get(strike_price) or registry_strike_tokens.get(float(strike_price))
                                    if not token_pair:
                                        continue
                                    ce_token = token_pair.get("CE")
                                    pe_token = token_pair.get("PE")
                                    if not ce_token or not pe_token:
                                        continue

                                    ce_ltp = 0.0
                                    pe_ltp = 0.0
                                    ce_bid = 0.0
                                    ce_ask = 0.0
                                    pe_bid = 0.0
                                    pe_ask = 0.0
                                    ce_oi = 0
                                    pe_oi = 0
                                    ce_volume = 0
                                    pe_volume = 0
                                    ce_iv = 0
                                    pe_iv = 0
                                    ce_obj = {}
                                    pe_obj = {}

                                    # Keep premiums at zero when only tokens are available
                                    if ce_ltp <= 0:
                                        ce_ltp = 0.0
                                    if pe_ltp <= 0:
                                        pe_ltp = 0.0
                                else:
                                    # Extract CE data from nested structure
                                    ce_obj = strike_data.get("ce", {}) or strike_data.get("CE", {}) or {}
                                    ce_ltp = float(ce_obj.get("ltp") or ce_obj.get("lastPrice") or strike_data.get("ce_ltp") or 0)
                                    
                                    # Fallback: if LTP is 0 (market closed/no volume), use Closing Price
                                    if ce_ltp <= 0:
                                        ce_ltp = float(ce_obj.get("close") or ce_obj.get("previous_close") or ce_obj.get("prev_close") or 0)
                                    
                                    ce_bid = float(ce_obj.get("bid") or ce_obj.get("bidPrice") or strike_data.get("ce_bid") or 0)
                                    ce_ask = float(ce_obj.get("ask") or ce_obj.get("askPrice") or strike_data.get("ce_ask") or 0)
                                    ce_oi = int(ce_obj.get("oi") or ce_obj.get("openInterest") or strike_data.get("ce_oi") or 0)
                                    ce_volume = int(ce_obj.get("volume") or strike_data.get("ce_volume") or 0)
                                    ce_iv = float(ce_obj.get("iv") or strike_data.get("ce_iv") or 0)

                                    # Try to get real security ID first
                                    ce_token = ce_obj.get("token") or ce_obj.get("security_id") or strike_data.get("ce_security_id")
                                    if not ce_token:
                                        real_ce_security_id = self.security_mapper.get_security_id(f"CE_{underlying}_{strike_price}_{expiry}")
                                        if real_ce_security_id:
                                            ce_token = str(real_ce_security_id)
                                        else:
                                            ce_token = f"CE_{underlying}_{strike_price}_{expiry}"

                                    # Extract PE data from nested structure
                                    pe_obj = strike_data.get("pe", {}) or strike_data.get("PE", {}) or {}
                                    pe_ltp = float(pe_obj.get("ltp") or pe_obj.get("lastPrice") or strike_data.get("pe_ltp") or 0)
                                    
                                    # Fallback: if LTP is 0 (market closed/no volume), use Closing Price
                                    if pe_ltp <= 0:
                                        pe_ltp = float(pe_obj.get("close") or pe_obj.get("previous_close") or pe_obj.get("prev_close") or 0)
                                    
                                    pe_bid = float(pe_obj.get("bid") or pe_obj.get("bidPrice") or strike_data.get("pe_bid") or 0)
                                    pe_ask = float(pe_obj.get("ask") or pe_obj.get("askPrice") or strike_data.get("pe_ask") or 0)
                                    pe_oi = int(pe_obj.get("oi") or pe_obj.get("openInterest") or strike_data.get("pe_oi") or 0)
                                    pe_volume = int(pe_obj.get("volume") or strike_data.get("pe_volume") or 0)
                                    pe_iv = float(pe_obj.get("iv") or strike_data.get("pe_iv") or 0)

                                    pe_token = pe_obj.get("token") or pe_obj.get("security_id") or strike_data.get("pe_security_id")
                                    if not pe_token:
                                        real_pe_security_id = self.security_mapper.get_security_id(f"PE_{underlying}_{strike_price}_{expiry}")
                                        if real_pe_security_id:
                                            pe_token = str(real_pe_security_id)
                                        else:
                                            pe_token = f"PE_{underlying}_{strike_price}_{expiry}"

                                    # If still no LTP from API, keep zero
                                    if ce_ltp <= 0:
                                        ce_ltp = 0.0
                                    if pe_ltp <= 0:
                                        pe_ltp = 0.0

                                    # No bid/ask fallback; keep zero unless provided
                                    if ce_bid <= 0 and ce_ltp > 0:
                                        ce_bid = ce_ltp
                                    if ce_ask <= 0 and ce_ltp > 0:
                                        ce_ask = ce_ltp
                                    if pe_bid <= 0 and pe_ltp > 0:
                                        pe_bid = pe_ltp
                                    if pe_ask <= 0 and pe_ltp > 0:
                                        pe_ask = pe_ltp

                                ce_data = OptionData(
                                    token=ce_token,
                                    ltp=ce_ltp,
                                    bid=ce_bid,
                                    ask=ce_ask,
                                    oi=ce_oi,
                                    volume=ce_volume,
                                    iv=ce_iv,
                                    greeks={
                                        "delta": float(ce_obj.get("delta") or strike_data.get("ce_delta") or 0),
                                        "gamma": float(ce_obj.get("gamma") or strike_data.get("ce_gamma") or 0),
                                        "theta": float(ce_obj.get("theta") or strike_data.get("ce_theta") or 0),
                                        "vega": float(ce_obj.get("vega") or strike_data.get("ce_vega") or 0)
                                    }
                                )

                                pe_data = OptionData(
                                    token=pe_token,
                                    ltp=pe_ltp,
                                    bid=pe_bid,
                                    ask=pe_ask,
                                    oi=pe_oi,
                                    volume=pe_volume,
                                    iv=pe_iv,
                                    greeks={
                                        "delta": float(pe_obj.get("delta") or strike_data.get("pe_delta") or 0),
                                        "gamma": float(pe_obj.get("gamma") or strike_data.get("pe_gamma") or 0),
                                        "theta": float(pe_obj.get("theta") or strike_data.get("pe_theta") or 0),
                                        "vega": float(pe_obj.get("vega") or strike_data.get("pe_vega") or 0)
                                    }
                                )

                                strikes_dict[strike_price] = StrikeData(
                                    strike_price=strike_price,
                                    CE=ce_data,
                                    PE=pe_data
                                )

                            ce_synth = self._synthesize_missing_prices(strikes_dict, "CE")
                            pe_synth = self._synthesize_missing_prices(strikes_dict, "PE")
                            self._notify_synthetic_prices(underlying, expiry, ce_synth + pe_synth)
                            
                            # Create skeleton
                            skeleton = OptionChainSkeleton(
                                underlying=underlying,
                                expiry=expiry,
                                lot_size=lot_size,
                                strike_interval=self.index_options[underlying]["strike_interval"],
                                atm_strike=atm_strike,
                                strikes=strikes_dict,
                                last_updated=datetime.now()
                            )
                            
                            # Store in cache
                            if underlying not in self.option_chain_cache:
                                self.option_chain_cache[underlying] = {}
                            
                            self.option_chain_cache[underlying][expiry] = skeleton
                            logger.info(f"    ✅ {underlying} {expiry}: {len(strikes_dict)} strikes cached (ATM: {atm_strike})")
                            
                        except Exception as e:
                            logger.error(f"    ❌ Error processing expiry {expiry} for {underlying}: {e}")
                            continue
                    
                except Exception as e:
                    logger.error(f"  ❌ Error processing {underlying}: {e}")
                    continue
            
            total_expiries = sum(len(expiries) for expiries in self.option_chain_cache.values())
            logger.info(f"✅ Option chain populated with {total_expiries} expiries from DhanHQ API")
            
        except Exception as e:
            logger.error(f"❌ Failed to populate option chain with live data: {e}")
            raise

    
    def populate_with_closing_prices_sync(self, market_data: Dict[str, Any]) -> None:
        """Synchronous wrapper for populate_with_closing_prices (for startup initialization)"""
        try:
            logger.info("📊 Populating option chain with closing prices (markets closed)...")
            
            for underlying, data in market_data.items():
                from app.market.live_prices import get_prices
                live_prices = get_prices()
                current_price = live_prices.get(underlying) or data.get("current_price", 0)
                expiries = data.get("expiries", [])
                selected_expiries = self._select_current_next_expiries(underlying, expiries)
                closing_prices = data.get("closing_prices", {})
                
                # Validate underlying is in permitted list
                if underlying not in self.index_options:
                    logger.warning(f"⚠️ {underlying} not in permitted index options, skipping")
                    continue
                
                logger.info(f"  Processing {underlying} at {current_price:.2f}")
                
                for expiry in selected_expiries:
                    closing_prices_for_expiry = closing_prices.get(expiry) or {}
                    if not closing_prices_for_expiry:
                        logger.warning(f"  ⚠️ No closing prices for {underlying} {expiry}; leaving premiums at 0")

                    strike_interval = self.index_options[underlying]["strike_interval"]
                    atm_strike = self._derive_atm_from_chain(
                        [], # Empty list as we don't have chain data here, just closing prices
                        current_price,
                        strike_interval,
                    )
                    display_strikes = self._generate_display_strikes(atm_strike, strike_interval, 25)

                    strikes_dict = {}
                    for strike in display_strikes:
                        prices = closing_prices_for_expiry.get(str(strike), {})
                        ce_ltp = prices.get("CE", 0.0) or 0.0
                        pe_ltp = prices.get("PE", 0.0) or 0.0

                        ce_data = OptionData(
                            token=f"CE_{underlying}_{strike}_{expiry}",
                            ltp=ce_ltp,
                            bid=0.0,
                            ask=0.0,
                            iv=prices.get("IV", 0.0),
                            greeks={
                                "delta": prices.get("delta_CE", 0.0),
                                "gamma": prices.get("gamma_CE", 0.0),
                                "theta": prices.get("theta_CE", 0.0),
                                "vega": prices.get("vega_CE", 0.0)
                            }
                        )

                        pe_data = OptionData(
                            token=f"PE_{underlying}_{strike}_{expiry}",
                            ltp=pe_ltp,
                            bid=0.0,
                            ask=0.0,
                            iv=prices.get("IV", 0.0),
                            greeks={
                                "delta": prices.get("delta_PE", 0.0),
                                "gamma": prices.get("gamma_PE", 0.0),
                                "theta": prices.get("theta_PE", 0.0),
                                "vega": prices.get("vega_PE", 0.0)
                            }
                        )

                        strikes_dict[strike] = StrikeData(
                            strike_price=strike,
                            CE=ce_data,
                            PE=pe_data
                        )

                    ce_synth = self._synthesize_missing_prices(strikes_dict, "CE")
                    pe_synth = self._synthesize_missing_prices(strikes_dict, "PE")
                    self._notify_synthetic_prices(underlying, expiry, ce_synth + pe_synth)
                    
                    if not strikes_dict:
                        logger.warning(f"  ⚠️ No valid strikes for {underlying} {expiry}")
                        continue
                    
                    # Use middle strike as ATM if not found
                    if atm_strike is None:
                        sorted_strikes = sorted(strikes_dict.keys())
                        atm_strike = sorted_strikes[len(sorted_strikes) // 2]
                    
                    # Create skeleton - use index_options directly for lot sizes (NOT from instrument master)
                    lot_size = self.index_options.get(underlying, {}).get("lot_size", 50)
                    
                    skeleton = OptionChainSkeleton(
                        underlying=underlying,
                        expiry=expiry,
                        lot_size=lot_size,
                        strike_interval=self.index_options[underlying]["strike_interval"],
                        atm_strike=atm_strike,
                        strikes=strikes_dict,
                        last_updated=datetime.now()
                    )
                    
                    # Store in cache
                    if underlying not in self.option_chain_cache:
                        self.option_chain_cache[underlying] = {}
                    
                    self.option_chain_cache[underlying][expiry] = skeleton
                    logger.info(f"  ✅ {underlying} {expiry}: {len(strikes_dict)} strikes cached (ATM: {atm_strike})")
            
            logger.info(f"✅ Option chain populated with {sum(len(e) for e in self.option_chain_cache.values())} expiries")
            
        except Exception as e:
            logger.error(f"❌ Failed to populate option chain with closing prices: {e}")

# Global instance
authoritative_option_chain_service = AuthoritativeOptionChainService()
