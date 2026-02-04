"""
Instrument Subscription Service
Manages instrument universe generation and subscription plans as per DhanHQ compliance
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class Exchange(Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"

class InstrumentType(Enum):
    EQUITY = "EQUITY"
    INDEX_OPTION = "INDEX_OPTION"
    STOCK_OPTION = "STOCK_OPTION"
    STOCK_FUTURE = "STOCK_FUTURE"
    COMMODITY_FUTURE = "COMMODITY_FUTURE"
    COMMODITY_OPTION = "COMMODITY_OPTION"

class OptionType(Enum):
    CALL = "CE"
    PUT = "PE"

@dataclass
class Instrument:
    symbol: str
    name: str
    exchange: Exchange
    instrument_type: InstrumentType
    token: str
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[OptionType] = None
    lot_size: Optional[int] = None

@dataclass
class SubscriptionPlan:
    websocket_id: int
    instruments: List[str]
    count: int

@dataclass
class DhanInstrument:
    exchange_segment: str
    security_id: str

@dataclass
class DhanCredentials:
    client_id: str
    api_key: str
    access_token: str
    auth_type: str

class InstrumentSubscriptionService:
    """Service for managing instrument subscription universe"""
    
    def __init__(self):
        self.master_instrument_registry: Dict[str, Instrument] = {}
        self.symbol_to_tokens: Dict[str, List[str]] = {}
        self.instruments: Dict[str, Instrument] = {}
        self.token_to_websocket: Dict[str, int] = {}
        self.subscription_plans: List[SubscriptionPlan] = []
        self.search_index: Dict[str, List[str]] = {}
        self.current_atm_strikes: Dict[str, float] = {}
        self.generated_strikes: Dict[str, List[float]] = {}
        
        # Initialize approved universe
        self.approved_universe = self._initialize_approved_universe()
    
    def _initialize_approved_universe(self) -> Dict[str, Any]:
        """Initialize the approved instrument universe as per requirements"""
        return {
            "index_options": {
                "NIFTY 50": {
                    "exchange": Exchange.NSE,
                    "expiries": 12,  # 8 weekly + 4 quarterly
                    "strikes_per_expiry": 100,
                    "strike_range": 50  # 50 below + ATM + 49 above
                },
                "BANKNIFTY": {
                    "exchange": Exchange.NSE,
                    "expiries": 5,  # current monthly + next 4 quarterly
                    "strikes_per_expiry": 100,
                    "strike_range": 50
                },
                "SENSEX": {
                    "exchange": Exchange.BSE,
                    "expiries": 5,  # current 4 weekly + next 1 monthly
                    "strikes_per_expiry": 100,
                    "strike_range": 50
                },
                "FINNIFTY": {
                    "exchange": Exchange.NSE,
                    "expiries": 4,  # current monthly + next 3 quarterly
                    "strikes_per_expiry": 50,
                    "strike_range": 25  # 25 below + ATM + 24 above
                },
                "MIDCPNIFTY": {
                    "exchange": Exchange.NSE,
                    "expiries": 4,
                    "strikes_per_expiry": 50,
                    "strike_range": 25
                },
                "BANKEX": {
                    "exchange": Exchange.BSE,
                    "expiries": 4,
                    "strikes_per_expiry": 50,
                    "strike_range": 25
                }
            },
            "stock_options": {
                "count": 100,  # Top 100 NSE F&O stocks (dynamic list)
                "expiries": 2,  # current monthly + next monthly
                "strikes_per_expiry": 25,
                "strike_range": 12,  # 12 below + ATM + 12 above
                "dynamic": True  # Prepare for dynamic NSE F&O list changes
            },
            "stock_futures": {
                "count": 100,  # Top 100 NSE F&O stocks
                "expiries": 2,  # current monthly + next monthly
                "dynamic": True
            },
            "equity": {
                "count": 1500,  # Top 1500 NSE stocks
                "dynamic": True
            },
            "mcx_futures": {
                "commodities": ["CRUDEOIL", "NATURALGAS", "GOLD", "SILVER", "COPPER", "ZINC", "LEAD", "NICKEL", "ALUMINIUM"],
                "expiries": 2
            },
            "mcx_options": {
                "commodities": ["CRUDEOIL", "NATURALGAS"],
                "expiries": 2,
                "strikes_per_expiry": 10,
                "strike_range": 5  # 5 below + 5 above
            }
        }
    
    async def generate_instrument_universe(self) -> bool:
        """Generate the complete instrument universe as per DhanHQ compliance"""
        try:
            logger.info("Starting instrument universe generation...")
            
            total_count = 0
            
            # 1. Generate Index Options
            total_count += await self._generate_index_options()
            
            # 2. Generate Stock Options
            total_count += await self._generate_stock_options()
            
            # 3. Generate Stock Futures
            total_count += await self._generate_stock_futures()
            
            # 4. Generate Equity
            total_count += await self._generate_equity()
            
            # 5. Generate MCX Futures
            total_count += await self._generate_mcx_futures()
            
            # 6. Generate MCX Options
            total_count += await self._generate_mcx_options()
            
            # Validate against expected counts
            expected_total = 16900  # As per requirements
            if total_count < expected_total * 0.8:  # At least 80% of expected
                logger.error(f"Instrument count too low: {total_count} vs expected {expected_total}")
                return False
            elif total_count > expected_total * 1.2:  # More than 120% of expected
                logger.error(f"Instrument count too high: {total_count} vs expected {expected_total}")
                return False
            
            logger.info(f"Generated {total_count} instruments successfully")
            
            # Build search index
            await self._build_search_index()
            
            # Create subscription plans
            await self._create_subscription_plans()
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating instrument universe: {e}")
            return False
    
    async def _generate_index_options(self) -> int:
        """Generate index options as per rules"""
        # TODO: Implement real index options generation using Dhan API
        logger.info("Real index options generation not yet implemented")
        return 0
    
    async def _generate_stock_options(self) -> int:
        """Generate stock options for top 100 NSE F&O stocks"""
        # TODO: Implement real stock options generation using Dhan API
        logger.info("Real stock options generation not yet implemented")
        return 0
    
    async def _generate_stock_futures(self) -> int:
        """Generate stock futures for top 100 NSE F&O stocks"""
        # TODO: Implement real stock futures generation using Dhan API
        logger.info("Real stock futures generation not yet implemented")
        return 0
    
    async def _generate_equity(self) -> int:
        """Generate equity instruments for top 1000 NSE stocks"""
        # TODO: Implement real equity generation using Dhan API
        logger.info("Real equity generation not yet implemented")
        return 0
    
    async def _generate_mcx_futures(self) -> int:
        """Generate MCX futures"""
        # TODO: Implement real MCX futures generation using Dhan API
        logger.info("Real MCX futures generation not yet implemented")
        return 0
    
    async def _generate_mcx_options(self) -> int:
        """Generate MCX options"""
        # TODO: Implement real MCX options generation using Dhan API
        logger.info("Real MCX options generation not yet implemented")
        return 0
    
    async def _build_search_index(self) -> None:
        """Build search index for fast instrument lookup"""
        logger.info("Building search index...")
        self.search_index = {}
        
        for token, instrument in self.instruments.items():
            # Index by symbol
            symbol_lower = instrument.symbol.lower()
            if symbol_lower not in self.search_index:
                self.search_index[symbol_lower] = []
            self.search_index[symbol_lower].append(token)
            
            # Index by name
            name_lower = instrument.name.lower()
            if name_lower not in self.search_index:
                self.search_index[name_lower] = []
            self.search_index[name_lower].append(token)
    
    async def _create_subscription_plans(self) -> None:
        """Create WebSocket subscription plans as per DhanHQ limits"""
        logger.info("Creating subscription plans...")
        
        max_instruments_per_websocket = 5000
        max_websocket_connections = 5
        
        self.subscription_plans = []
        all_tokens = list(self.instruments.keys())
        
        # Distribute instruments across WebSocket connections
        for i in range(0, len(all_tokens), max_instruments_per_websocket):
            websocket_id = len(self.subscription_plans)
            if websocket_id >= max_websocket_connections:
                logger.warning(f"Reached max WebSocket connections ({max_websocket_connections}), skipping remaining instruments")
                break
            
            batch_tokens = all_tokens[i:i + max_instruments_per_websocket]
            plan = SubscriptionPlan(
                websocket_id=websocket_id,
                instruments=batch_tokens,
                count=len(batch_tokens)
            )
            self.subscription_plans.append(plan)
            
            # Map tokens to WebSocket
            for token in batch_tokens:
                self.token_to_websocket[token] = websocket_id
        
        logger.info(f"Created {len(self.subscription_plans)} subscription plans")
    
    def search_instruments(self, query: str, limit: int = 50) -> List[Instrument]:
        """Search instruments by query with relevance ranking"""
        query_lower = query.lower()
        results = []
        scored_results = []
        
        # Search in index
        for term, tokens in self.search_index.items():
            if query_lower in term:
                for token in tokens:
                    if token in self.instruments:
                        instrument = self.instruments[token]
                        score = self._calculate_relevance_score(query_lower, instrument)
                        scored_results.append((score, instrument))
        
        # Sort by score (descending) and take top results
        scored_results.sort(key=lambda x: x[0], reverse=True)
        results = [instrument for _, instrument in scored_results[:limit]]
        
        return results
    
    def _calculate_relevance_score(self, query_lower: str, instrument: Instrument) -> float:
        """Calculate relevance score for search ranking"""
        score = 0.0
        
        # Exact symbol match
        if query_lower == instrument.symbol.lower():
            score += 100.0
        
        # Symbol starts with query
        elif instrument.symbol.lower().startswith(query_lower):
            score += 50.0
        
        # Symbol contains query
        elif query_lower in instrument.symbol.lower():
            score += 30.0
        
        # Name starts with query
        elif instrument.name.lower().startswith(query_lower):
            score += 40.0
        
        # Name contains query
        elif query_lower in instrument.name.lower():
            score += 20.0
        
        # Instrument type match
        elif query_lower == instrument.instrument_type.value.lower():
            score += 25.0
        
        # Option type match
        elif instrument.option_type and query_lower == instrument.option_type.value.lower():
            score += 20.0
        
        # Bonus for shorter symbols (more precise)
        if len(instrument.symbol) <= 10:
            score += 10.0
        
        return score
    
    def get_subscription_plan(self, websocket_id: int) -> Optional[SubscriptionPlan]:
        """Get subscription plan for WebSocket connection"""
        for plan in self.subscription_plans:
            if plan.websocket_id == websocket_id:
                return plan
        return None
    
    def get_websocket_for_token(self, token: str) -> Optional[int]:
        """Get WebSocket ID for a specific instrument token"""
        return self.token_to_websocket.get(token)
    
    def get_instrument_by_token(self, token: str) -> Optional[Instrument]:
        """Get instrument by token"""
        return self.instruments.get(token)
    
    def get_instruments_by_symbol(self, symbol: str) -> List[Instrument]:
        """Get all instruments for a symbol"""
        tokens = self.symbol_to_tokens.get(symbol, [])
        return [self.instruments[token] for token in tokens if token in self.instruments]
    
    def get_subscription_stats(self) -> Dict[str, Any]:
        """Get subscription statistics"""
        return {
            "total_instruments": len(self.instruments),
            "total_symbols": len(self.symbol_to_tokens),
            "subscription_plans": len(self.subscription_plans),
            "search_index_size": len(self.search_index),
            "instruments_per_websocket": [plan.count for plan in self.subscription_plans],
            "instrument_types": self._get_instrument_type_stats()
        }
    
    def _get_instrument_type_stats(self) -> Dict[str, int]:
        """Get statistics by instrument type"""
        stats = {}
        for instrument in self.instruments.values():
            type_name = instrument.instrument_type.value
            stats[type_name] = stats.get(type_name, 0) + 1
        return stats

# Global instance
instrument_subscription_service = InstrumentSubscriptionService()
