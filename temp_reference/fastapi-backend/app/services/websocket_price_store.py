"""
WebSocket Price Store
Real-time price storage for option chain data
Follows the architecture from prompt files
"""

from typing import Dict, Optional
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class WebSocketPriceStore:
    """Real-time price store for WebSocket data"""
    
    __instance__ = None
    
    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = super().__new__(cls)
        return cls.__instance__
    
    def __init__(self):
        self.prices: Dict[str, Dict] = {}
        self.last_update: Dict[str, datetime] = {}
        self.subscribed_tokens: set = set()
        
    def update_price(self, token: str, data: Dict):
        """Update price for a token"""
        self.prices[token] = {
            **data,
            "timestamp": datetime.now().isoformat(),
            "last_updated": datetime.now()
        }
        self.last_update[token] = datetime.now()
        
    def get_price(self, token: str) -> Optional[Dict]:
        """Get price for a token"""
        return self.prices.get(token)
    
    def get_underlying_price(self, symbol: str) -> Optional[float]:
        """Get underlying price from cached data"""
        # Look for underlying token in price store
        for token, data in self.prices.items():
            if data.get("symbol") == symbol and data.get("instrument_type") == "UNDERLYING":
                return data.get("ltp")
        return None
    
    def subscribe_token(self, token: str):
        """Subscribe to a token"""
        self.subscribed_tokens.add(token)
        logger.info(f"Subscribed to token: {token}")
    
    def unsubscribe_token(self, token: str):
        """Unsubscribe from a token"""
        self.subscribed_tokens.discard(token)
        if token in self.prices:
            del self.prices[token]
        if token in self.last_update:
            del self.last_update[token]
        logger.info(f"Unsubscribed from token: {token}")
    
    def get_all_prices(self) -> Dict[str, Dict]:
        """Get all cached prices"""
        return self.prices.copy()
    
    def get_subscribed_tokens(self) -> set:
        """Get all subscribed tokens"""
        return self.subscribed_tokens.copy()
    
    def get_price_by_symbol(self, symbol: str, strike: float, option_type: str) -> Optional[Dict]:
        """Get price by symbol, strike, and option type"""
        for token, data in self.prices.items():
            if (data.get("symbol") == symbol and 
                data.get("strike") == strike and 
                data.get("option_type") == option_type.upper()):
                return data
        return None
    
    def get_option_chain_prices(self, symbol: str, expiry: str) -> Dict:
        """Get all option chain prices for a symbol and expiry"""
        option_prices = {}
        
        for token, data in self.prices.items():
            if (data.get("symbol") == symbol and 
                data.get("expiry") == expiry and 
                data.get("instrument_type") in ["CE", "PE"]):
                strike = data.get("strike")
                option_type = data.get("option_type")
                if strike is not None and option_type is not None:
                    key = f"{strike}_{option_type}"
                    option_prices[key] = data
        
        return option_prices

# Global instance
price_store = WebSocketPriceStore()
