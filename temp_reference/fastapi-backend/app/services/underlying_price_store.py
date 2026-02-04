"""
Underlying Price Store
Authoritative cache for INDEX UNDERLYING LTPs from Dhan WebSocket
Follows the mandatory data model from requirements
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class UnderlyingPrice:
    """Underlying price data model"""
    underlying_symbol: str      # NIFTY / BANKNIFTY / SENSEX
    instrument_token: str
    ltp: float
    timestamp: datetime        # exchange timestamp
    source: str = "WEBSOCKET"   # WEBSOCKET | LAST_CLOSE | UNAVAILABLE
    
    def is_valid(self, max_age_seconds: int = 300) -> bool:
        """Check if price is still valid (default 5 minutes)"""
        if self.source == "UNAVAILABLE":
            return False
        age_seconds = (datetime.now() - self.timestamp).total_seconds()
        return age_seconds <= max_age_seconds
    
    def get_price_type(self) -> str:
        """Get price type for frontend"""
        if self.source == "WEBSOCKET" and self.is_valid():
            return "LIVE"
        elif self.source == "LAST_CLOSE":
            return "LAST_CLOSE"
        else:
            return "UNAVAILABLE"

class UnderlyingPriceStore:
    """Dedicated authoritative store for index underlying prices"""
    
    __instance__ = None
    
    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__
    
    def __init__(self):
        self.prices: Dict[str, UnderlyingPrice] = {}  # symbol -> UnderlyingPrice
        self.last_tick_time: Dict[str, datetime] = {}  # symbol -> last tick time
        self.tick_frequency: Dict[str, float] = {}     # symbol -> ticks per minute
        
        # Index instrument tokens (from official Dhan instrument master)
        self.index_tokens = {
            "NIFTY": "13",         # NIFTY 50 - ID 13
            "BANKNIFTY": "25",     # BANKNIFTY - ID 25  
            "SENSEX": "51"         # SENSEX - ID 51
        }
        
        logger.info("UnderlyingPriceStore initialized")
        logger.info(f"Index tokens: {self.index_tokens}")
    
    def update_price(self, symbol: str, ltp: float, timestamp: datetime = None, source: str = "WEBSOCKET"):
        """Update underlying price immediately on WebSocket tick"""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Get instrument token
        instrument_token = self.index_tokens.get(symbol, f"UNKNOWN_{symbol}")
        
        # Create new price data
        price_data = UnderlyingPrice(
            underlying_symbol=symbol,
            instrument_token=instrument_token,
            ltp=ltp,
            timestamp=timestamp,
            source=source
        )
        
        # Update store immediately (no throttling)
        old_price = self.prices.get(symbol)
        self.prices[symbol] = price_data
        self.last_tick_time[symbol] = datetime.now()
        
        # Calculate tick frequency
        if old_price and symbol in self.tick_frequency:
            time_diff = (timestamp - old_price.timestamp).total_seconds()
            if time_diff > 0:
                self.tick_frequency[symbol] = 60.0 / time_diff  # ticks per minute
        
        # Log price update
        logger.info(f"📈 {symbol} LTP updated: {ltp} (source: {source}, token: {instrument_token})")
        
        # Detect stale data warnings
        if source == "WEBSOCKET" and not price_data.is_valid(300):  # 5 minutes
            logger.warning(f"⚠️ {symbol} WebSocket data appears stale: {timestamp}")
    
    def get_price(self, symbol: str) -> Optional[UnderlyingPrice]:
        """Get underlying price for symbol"""
        return self.prices.get(symbol)
    
    def get_ltp(self, symbol: str) -> Optional[float]:
        """Get just the LTP for symbol"""
        price_data = self.get_price(symbol)
        return price_data.ltp if price_data else None
    
    def is_available(self, symbol: str) -> bool:
        """Check if underlying price is available and valid"""
        price_data = self.get_price(symbol)
        return price_data is not None and price_data.is_valid()
    
    def get_underlying_ltp_api(self, symbol: str) -> Dict:
        """
        Authoritative API response for frontend
        """
        symbol = symbol.upper()
        
        if symbol not in self.prices:
            # Try to get from InstrumentLastClose table
            try:
                from app.models.instrument_last_close import InstrumentLastClose
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                # Create database session
                engine = create_engine(
                    "sqlite:///./trading_terminal.db",
                    pool_pre_ping=True,
                    echo=False
                )
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                
                try:
                    # Map symbol to instrument token
                    token_map = {
                        'NIFTY': '260105',
                        'BANKNIFTY': '260106',
                        'SENSEX': '260107'
                    }
                    
                    instrument_token = token_map.get(symbol)
                    if instrument_token:
                        last_close_record = db.query(InstrumentLastClose).filter(
                            InstrumentLastClose.instrument_token == instrument_token
                        ).first()
                        
                        if last_close_record and last_close_record.last_close_price > 0:
                            logger.info(f"  Using InstrumentLastClose for {symbol}: {last_close_record.last_close_price}")
                            
                            # Create price entry from last close data
                            now = datetime.now()
                            self.prices[symbol] = UnderlyingPrice(
                                underlying_symbol=symbol,
                                instrument_token=instrument_token,
                                ltp=last_close_record.last_close_price,
                                timestamp=last_close_record.exchange_timestamp or now,
                                source="INSTRUMENT_LAST_CLOSE"
                            )
                            
                            return {
                                'ltp': last_close_record.last_close_price,
                                'timestamp': last_close_record.exchange_timestamp.isoformat() if last_close_record.exchange_timestamp else now.isoformat(),
                                'price_type': 'LAST_CLOSE',
                                'instrument_token': instrument_token,
                                'source': 'INSTRUMENT_LAST_CLOSE',
                                'available': True
                            }
                
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"  Error accessing InstrumentLastClose for {symbol}: {e}")
            
            # If still not found, return unavailable
            return {
                'ltp': 0.0,
                'timestamp': datetime.now().isoformat(),
                'price_type': 'UNAVAILABLE',
                'instrument_token': self.index_tokens.get(symbol, ''),
                'source': 'UNAVAILABLE',
                'available': False
            }
        
        price_data = self.prices[symbol]
        
        # If price is 0, try to get from InstrumentLastClose
        if price_data.ltp == 0:
            try:
                from app.models.instrument_last_close import InstrumentLastClose
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                # Create database session
                engine = create_engine(
                    "sqlite:///./trading_terminal.db",
                    pool_pre_ping=True,
                    echo=False
                )
                SessionLocal = sessionmaker(bind=engine)
                db = SessionLocal()
                
                try:
                    instrument_token = price_data.instrument_token
                    if instrument_token:
                        last_close_record = db.query(InstrumentLastClose).filter(
                            InstrumentLastClose.instrument_token == instrument_token
                        ).first()
                        
                        if last_close_record and last_close_record.last_close_price > 0:
                            logger.info(f"  Fallback to InstrumentLastClose for {symbol}: {last_close_record.last_close_price}")
                            
                            # Update current price data
                            now = datetime.now()
                            self.prices[symbol] = UnderlyingPrice(
                                underlying_symbol=symbol,
                                instrument_token=instrument_token,
                                ltp=last_close_record.last_close_price,
                                timestamp=last_close_record.exchange_timestamp or now,
                                source="INSTRUMENT_LAST_CLOSE"
                            )
                            
                            price_data = self.prices[symbol]
                
                finally:
                    db.close()
                    
            except Exception as e:
                logger.error(f"  Error accessing InstrumentLastClose fallback for {symbol}: {e}")
        
        return {
            'ltp': price_data.ltp,
            'timestamp': price_data.timestamp.isoformat(),
            'price_type': 'LAST_CLOSE' if price_data.source == 'INSTRUMENT_LAST_CLOSE' else 'LIVE',
            'instrument_token': price_data.instrument_token,
            'source': price_data.source,
            'available': price_data.is_valid()
        }
    
    def get_debug_info(self, symbol: str) -> Dict:
        """Get debug information for monitoring"""
        price_data = self.get_price(symbol)
        last_tick = self.last_tick_time.get(symbol)
        frequency = self.tick_frequency.get(symbol, 0)
        
        if last_tick:
            tick_age_seconds = (datetime.now() - last_tick).total_seconds()
        else:
            tick_age_seconds = float('inf')
        
        # Handle infinity for JSON serialization
        if tick_age_seconds == float('inf'):
            tick_age_seconds_str = "infinity"
        else:
            tick_age_seconds_str = str(tick_age_seconds)
        
        return {
            "symbol": symbol,
            "available": self.is_available(symbol),
            "ltp": price_data.ltp if price_data else None,
            "price_type": price_data.get_price_type() if price_data else "UNAVAILABLE",
            "last_tick_time": last_tick.isoformat() if last_tick else None,
            "tick_age_seconds": tick_age_seconds_str,
            "tick_frequency_per_minute": frequency,
            "instrument_token": price_data.instrument_token if price_data else None,
            "source": price_data.source if price_data else None
        }
    
    def get_all_debug_info(self) -> Dict:
        """Get debug info for all underlyings"""
        return {
            symbol: self.get_debug_info(symbol)
            for symbol in self.index_tokens.keys()
        }
    
    def mark_unavailable(self, symbol: str, reason: str = "No WebSocket data"):
        """Mark underlying as unavailable"""
        self.prices[symbol] = UnderlyingPrice(
            underlying_symbol=symbol,
            instrument_token=self.index_tokens.get(symbol, f"UNKNOWN_{symbol}"),
            ltp=0.0,
            timestamp=datetime.now(),
            source="UNAVAILABLE"
        )
        logger.error(f"❌ {symbol} marked unavailable: {reason}")
    
    def force_last_close(self, symbol: str, ltp: float, timestamp: datetime = None):
        """Force set last close price (for market close scenarios)"""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.update_price(symbol, ltp, timestamp, "LAST_CLOSE")
        logger.info(f"📊 {symbol} last close set: {ltp}")

# Global instance
underlying_price_store = UnderlyingPriceStore()