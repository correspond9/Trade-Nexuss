"""
Option Chain Service
Builds and maintains real-time option chains using REST skeleton + WebSocket prices
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, date
from dataclasses import dataclass, asdict
import json
import asyncio
from enum import Enum

class OptionType(Enum):
    CALL = "CE"
    PUT = "PE"

class Exchange(Enum):
    NSE = "NSE"
    BSE = "BSE"

@dataclass
class OptionInstrument:
    """Single option instrument in the skeleton"""
    symbol: str
    underlying: str
    expiry: str
    strike: float
    option_type: OptionType
    instrument_token: str
    exchange: Exchange
    lot_size: int
    tick_size: float

@dataclass
class OptionPrice:
    """Live price data from WebSocket"""
    ltp: float
    best_bid: float
    best_ask: float
    bid_qty: int
    ask_qty: int
    timestamp: datetime
    volume: int = 0
    oi: int = 0

@dataclass
class OptionChainData:
    """Complete option chain data with skeleton + live prices"""
    symbol: str
    underlying: str
    expiry: str
    strike: float
    option_type: OptionType
    instrument_token: str
    exchange: Exchange
    lot_size: int
    tick_size: float
    # Live prices
    ltp: Optional[float] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None
    bid_qty: Optional[int] = None
    ask_qty: Optional[int] = None
    volume: Optional[int] = None
    oi: Optional[int] = None
    timestamp: Optional[datetime] = None
    # Calculated fields
    spread: Optional[float] = None
    mid_price: Optional[float] = None

class OptionChainService:
    """
    Builds and maintains real-time option chains
    Architecture: REST Skeleton + WebSocket Prices
    """
    
    def __init__(self):
        # 1️⃣ Option Chain Skeleton (built once from REST)
        self.skeleton: Dict[str, OptionInstrument] = {}  # token -> instrument
        
        # 2️⃣ Live Price Store (updated via WebSocket)
        self.price_store: Dict[str, OptionPrice] = {}  # token -> price
        
        # 3️⃣ Subscription tracking
        self.subscribed_tokens: Set[str] = set()
        
        # 4️⃣ Cache for assembled chains
        self.chain_cache: Dict[str, List[OptionChainData]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        
        # 5️⃣ Supported instruments
        self.index_instruments = {
            "NIFTY": {"exchange": Exchange.NSE, "token_prefix": "NIFTY"},
            "BANKNIFTY": {"exchange": Exchange.NSE, "token_prefix": "BANKNIFTY"},
            "SENSEX": {"exchange": Exchange.BSE, "token_prefix": "SENSEX"}
        }
    
    async def build_skeleton_from_rest(self, underlying: str, expiry: str) -> bool:
        """
        Build option chain skeleton from REST API
        This is called once per expiry at market open
        """
        try:
            # TODO: Replace with actual Dhan REST API calls
            # Generate option chain skeleton from real data
            
            if underlying not in self.index_instruments:
                print(f"Unsupported underlying: {underlying}")
                return False
            
            exchange = self.index_instruments[underlying]["exchange"]
            token_prefix = self.index_instruments[underlying]["token_prefix"]
            
            # Generate strike range (mock data)
            base_price = await self._get_underlying_price(underlying)
            if not base_price:
                print(f"Could not get base price for {underlying}")
                return False
            
            strikes = self._generate_strike_range(base_price, underlying)
            
            # Build skeleton for both CE and PE
            for strike in strikes:
                for option_type in [OptionType.CALL, OptionType.PUT]:
                    token = f"{token_prefix}_{expiry}_{strike}_{option_type.value}"
                    
                    instrument = OptionInstrument(
                        symbol=f"{underlying}_{strike}_{option_type.value}",
                        underlying=underlying,
                        expiry=expiry,
                        strike=strike,
                        option_type=option_type,
                        instrument_token=token,
                        exchange=exchange,
                        lot_size=self._get_lot_size(underlying),
                        tick_size=self._get_tick_size(underlying)
                    )
                    
                    self.skeleton[token] = instrument
            
            print(f"Built skeleton for {underlying} {expiry}: {len(self.skeleton)} instruments")
            return True
            
        except Exception as e:
            print(f"Error building skeleton: {e}")
            return False
    
    async def subscribe_to_websocket_ticks(self, underlying: str, expiry: str) -> bool:
        """
        Subscribe to WebSocket ticks for all instruments in skeleton
        This is called once after skeleton is built
        """
        try:
            # Extract all tokens from skeleton for this underlying/expiry
            tokens_to_subscribe = [
                token for token, instrument in self.skeleton.items()
                if instrument.underlying == underlying and instrument.expiry == expiry
            ]
            
            if not tokens_to_subscribe:
                print(f"No tokens found for {underlying} {expiry}")
                return False
            
            # TODO: Replace with actual Dhan WebSocket subscription
            # For now, simulate subscription
            self.subscribed_tokens.update(tokens_to_subscribe)
            
            print(f"Subscribed to {len(tokens_to_subscribe)} WebSocket tokens for {underlying} {expiry}")
            
            return True
            
        except Exception as e:
            print(f"Error subscribing to WebSocket: {e}")
            return False
    
    def update_price_from_websocket(self, token: str, price_data: Dict[str, Any]) -> None:
        """
        Update price store from WebSocket tick
        This is called for every incoming WebSocket tick
        """
        try:
            if token not in self.skeleton:
                return  # Ignore unknown tokens
            
            price = OptionPrice(
                ltp=price_data.get('ltp', 0.0),
                best_bid=price_data.get('best_bid', 0.0),
                best_ask=price_data.get('best_ask', 0.0),
                bid_qty=price_data.get('bid_qty', 0),
                ask_qty=price_data.get('ask_qty', 0),
                timestamp=datetime.now(),
                volume=price_data.get('volume', 0),
                oi=price_data.get('oi', 0)
            )
            
            self.price_store[token] = price
            
        except Exception as e:
            print(f"Error updating price for {token}: {e}")
    
    def get_option_chain(self, underlying: str, expiry: str) -> List[OptionChainData]:
        """
        Assemble complete option chain on demand
        Merges skeleton + live prices
        This is called when frontend requests option chain
        """
        try:
            cache_key = f"{underlying}_{expiry}"
            
            # Check cache (valid for 1 second)
            if (cache_key in self.chain_cache and 
                cache_key in self.cache_timestamps and
                (datetime.now() - self.cache_timestamps[cache_key]).total_seconds() < 1):
                return self.chain_cache[cache_key]
            
            # Assemble chain
            chain = []
            
            for token, instrument in self.skeleton.items():
                if instrument.underlying == underlying and instrument.expiry == expiry:
                    # Get live prices
                    price = self.price_store.get(token)
                    
                    # Build complete chain data
                    chain_data = OptionChainData(
                        # Skeleton data
                        symbol=instrument.symbol,
                        underlying=instrument.underlying,
                        expiry=instrument.expiry,
                        strike=instrument.strike,
                        option_type=instrument.option_type,
                        instrument_token=instrument.instrument_token,
                        exchange=instrument.exchange,
                        lot_size=instrument.lot_size,
                        tick_size=instrument.tick_size,
                        # Live prices
                        ltp=price.ltp if price else None,
                        best_bid=price.best_bid if price else None,
                        best_ask=price.best_ask if price else None,
                        bid_qty=price.bid_qty if price else None,
                        ask_qty=price.ask_qty if price else None,
                        volume=price.volume if price else None,
                        oi=price.oi if price else None,
                        timestamp=price.timestamp if price else None
                    )
                    
                    # Calculate derived fields
                    if chain_data.best_bid is not None and chain_data.best_ask is not None:
                        chain_data.spread = chain_data.best_ask - chain_data.best_bid
                        chain_data.mid_price = (chain_data.best_bid + chain_data.best_ask) / 2
                    
                    chain.append(chain_data)
            
            # Sort by strike
            chain.sort(key=lambda x: x.strike)
            
            # Cache result
            self.chain_cache[cache_key] = chain
            self.cache_timestamps[cache_key] = datetime.now()
            
            return chain
            
        except Exception as e:
            print(f"Error assembling option chain: {e}")
            return []
    
    def get_straddle_chain(self, underlying: str, expiry: str) -> List[Dict[str, Any]]:
        """
        Get straddle-specific data for the frontend
        Combines CE and PE at same strike
        """
        try:
            chain = self.get_option_chain(underlying, expiry)
            
            # Group by strike
            strikes = {}
            for option in chain:
                if option.strike not in strikes:
                    strikes[option.strike] = {}
                strikes[option.strike][option.option_type] = option
            
            # Build straddle data
            straddles = []
            for strike, options in strikes.items():
                ce = options.get(OptionType.CALL)
                pe = options.get(OptionType.PUT)
                
                if ce and pe:
                    straddle_data = {
                        "strike": strike,
                        "ce_ltp": ce.ltp or 0.0,
                        "pe_ltp": pe.ltp or 0.0,
                        "ce_best_bid": ce.best_bid or 0.0,
                        "pe_best_bid": pe.best_bid or 0.0,
                        "ce_best_ask": ce.best_ask or 0.0,
                        "pe_best_ask": pe.best_ask or 0.0,
                        "straddle_premium": (ce.ltp or 0.0) + (pe.ltp or 0.0),
                        "spread": (ce.spread or 0.0) + (pe.spread or 0.0),
                        "mid_price": (ce.mid_price or 0.0) + (pe.mid_price or 0.0),
                        "volume": (ce.volume or 0) + (pe.volume or 0),
                        "oi": (ce.oi or 0) + (pe.oi or 0),
                        "timestamp": max(ce.timestamp or datetime.min, pe.timestamp or datetime.min),
                        "lot_size": ce.lot_size
                    }
                    straddles.append(straddle_data)
            
            # Sort by strike
            straddles.sort(key=lambda x: x["strike"])
            
            return straddles
            
        except Exception as e:
            print(f"Error building straddle chain: {e}")
            return []
    
    # Helper methods
    async def _get_underlying_price(self, underlying: str) -> Optional[float]:
        """Get current underlying price from UnderlyingPriceStore"""
        try:
            from app.services.underlying_price_store import underlying_price_store
            price_data = underlying_price_store.get_underlying_ltp_api(underlying)
            if price_data and 'ltp' in price_data:
                return float(price_data['ltp'])
            return None
        except Exception as e:
            print(f"Error getting underlying price for {underlying}: {e}")
            return None
    
    def _generate_strike_range(self, base_price: float, underlying: str) -> List[float]:
        """Generate strike range around current price"""
        # TODO: Replace with actual Dhan instrument API
        strike_interval = self._get_strike_interval(underlying)
        num_strikes = 20  # 10 above, 10 below ATM
        
        # Calculate ATM strike
        atm_strike = round(base_price / strike_interval) * strike_interval
        
        # Generate range
        strikes = []
        for i in range(-num_strikes//2, num_strikes//2 + 1):
            strike = atm_strike + (i * strike_interval)
            if strike > 0:
                strikes.append(strike)
        
        return strikes
    
    def _get_strike_interval(self, underlying: str) -> float:
        """Get strike interval for underlying"""
        intervals = {
            "NIFTY": 50.0,
            "BANKNIFTY": 100.0,
            "SENSEX": 100.0
        }
        return intervals.get(underlying, 50.0)
    
    def _get_lot_size(self, underlying: str) -> int:
        """Get lot size for underlying"""
        lot_sizes = {
            "NIFTY": 50,
            "BANKNIFTY": 25,
            "SENSEX": 10
        }
        return lot_sizes.get(underlying, 50)
    
    def _get_tick_size(self, underlying: str) -> float:
        """Get tick size for underlying"""
        tick_sizes = {
            "NIFTY": 0.05,
            "BANKNIFTY": 0.05,
            "SENSEX": 0.05
        }
        return tick_sizes.get(underlying, 0.05)
    
    # Global instance
option_chain_service = OptionChainService()
