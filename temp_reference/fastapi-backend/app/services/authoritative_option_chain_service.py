"""
Authoritative Option Chain Service
Implements the complete option chain construction flow as per specifications
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
import json

logger = logging.getLogger(__name__)

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
                    "CE": asdict(ce_data),
                    "PE": asdict(pe_data)
                }
                for strike, (ce_data, pe_data) in [(s.strike_price, (s.CE, s.PE)) for s in self.strikes.values()]
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
    """
    
    def __init__(self):
        # Central cache - the single source of truth
        self.option_chain_cache: Dict[str, Dict[str, OptionChainSkeleton]] = {}
        
        # Registries
        self.expiry_registry = ExpiryRegistry()
        self.atm_registry = ATMRegistry()
        
        # Instrument master cache (for metadata only)
        self.instrument_master_cache: Dict[str, Dict[str, Any]] = {}
        
        # WebSocket token mapping
        self.token_to_websocket: Dict[str, int] = {}
        self.websocket_subscriptions: Dict[int, Set[str]] = {}
        
        # Dhan API configuration
        self.dhan_base_url = "https://api.dhan.co"
        self.websocket_url = "wss://ws.dhan.co/v2/market"
        
        # Strike rules per specification
        self.strike_rules = {
            "NIFTY": {"below": 50, "above": 49, "total": 100},
            "BANKNIFTY": {"below": 50, "above": 49, "total": 100}, 
            "SENSEX": {"below": 50, "above": 49, "total": 100},
            "FINNIFTY": {"below": 25, "above": 24, "total": 50},
            "MIDCPNIFTY": {"below": 25, "above": 24, "total": 50},
            "BANKEX": {"below": 25, "above": 24, "total": 50},
            # Stock options default
            "STOCK_DEFAULT": {"below": 12, "above": 12, "total": 25},
            # MCX options
            "MCX_DEFAULT": {"below": 5, "above": 5, "total": 10}
        }
        
        # Expiry selection rules
        self.expiry_rules = {
            "weekly_indices": ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"],
            "monthly_indices": ["SENSEX", "BANKEX"],
            "quarterly_indices": [],  # Add if needed
            "mcx_commodities": ["CRUDEOIL", "NATURALGAS", "GOLD", "SILVER", "COPPER", "ZINC", "LEAD", "NICKEL", "ALUMINIUM"]
        }
    
    async def initialize(self) -> bool:
        """Initialize the service"""
        try:
            logger.info("Initializing Authoritative Option Chain Service...")
            
            # Load instrument master cache (metadata only)
            await self._load_instrument_master_cache()
            
            # Initialize registries
            await self._initialize_registries()
            
            logger.info("✅ Authoritative Option Chain Service initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Option Chain Service: {e}")
            return False
    
    async def _load_instrument_master_cache(self) -> None:
        """Load instrument master for metadata (strike intervals, lot sizes, etc.)"""
        try:
            # TODO: Load from Dhan instrument master API
            # For now, use minimal required metadata
            self.instrument_master_cache = {
                "NIFTY": {
                    "segment": "IDX_I",
                    "security_id": 13,
                    "strike_interval": 50.0,
                    "lot_size": 50
                },
                "BANKNIFTY": {
                    "segment": "IDX_I", 
                    "security_id": 23,
                    "strike_interval": 100.0,
                    "lot_size": 25
                },
                "SENSEX": {
                    "segment": "IDX_I",
                    "security_id": 22,
                    "strike_interval": 100.0,
                    "lot_size": 10
                },
                "FINNIFTY": {
                    "segment": "IDX_I",
                    "security_id": 260106,
                    "strike_interval": 50.0,
                    "lot_size": 40
                },
                "MIDCPNIFTY": {
                    "segment": "IDX_I",
                    "security_id": 260107,
                    "strike_interval": 25.0,
                    "lot_size": 75
                },
                "BANKEX": {
                    "segment": "IDX_I",
                    "security_id": 24,
                    "strike_interval": 100.0,
                    "lot_size": 15
                }
            }
            logger.info(f"✅ Loaded {len(self.instrument_master_cache)} instruments from master cache")
            
        except Exception as e:
            logger.error(f"❌ Failed to load instrument master cache: {e}")
            raise
    
    async def _initialize_registries(self) -> None:
        """Initialize expiry and ATM registries"""
        # Initialize empty registries - will be populated dynamically
        logger.info("✅ Initialized expiry and ATM registries")
    
    # STEP 1: AUTHORITATIVE EXPIRY SOURCE
    async def fetch_authoritative_expiries(self, underlying: str) -> List[str]:
        """
        Fetch expiries dynamically from Dhan Option Chain APIs
        NEVER from instrument master
        """
        try:
            logger.info(f"📅 Fetching authoritative expiries for {underlying}")
            
            # Get Security ID from instrument master (metadata only)
            security_id = self.instrument_master_cache.get(underlying, {}).get("security_id")
            segment = self.instrument_master_cache.get(underlying, {}).get("segment", "NSE_IDX")
            
            if not security_id:
                logger.error(f"❌ No Security ID found for {underlying} in instrument master")
                return []
            
            # Call Dhan Option Chain Expiry List API
            async with aiohttp.ClientSession() as session:
                url = f"{self.dhan_base_url}/v2/optionchain/expirylist"
                
                # Add required headers
                headers = {
                    "access-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5OTQ4MTUzLCJpYXQiOjE3Njk4NjE3NTMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.RQxkoN0av9K0R5zkccN062l0IK53ooY30ocuWK2kUC7rfQas3kSiXBU4EHTMZ5Qv73j7JX97OmeRiBIdQcbN7w",
                    "client-id": "1100353799",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"🔄 Fetching expiries from Dhan API for {underlying} (Security ID: {security_id})")
                
                payload = {
                    "UnderlyingScrip": security_id,
                    "UnderlyingSeg": segment
                }
                
                async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Received expiry data for {underlying}: {data}")
                        
                        # Extract expiries from response
                        expiries = self._extract_expiries_from_response(data)
                        
                        # Store in expiry registry
                        self.expiry_registry.expiries[underlying] = expiries
                        self.expiry_registry.last_updated[underlying] = datetime.now()
                        
                        logger.info(f"✅ Stored {len(expiries)} expiries for {underlying}")
                        return expiries
                    else:
                        logger.error(f"❌ Dhan API returned status {response.status} for {underlying}")
                        logger.error(f"Response: {await response.text()}")
                        return []
                        
        except Exception as e:
            logger.error(f"❌ Failed to fetch authoritative expiries for {underlying}: {e}")
            return []
    
    def _extract_expiries_from_response(self, data: Dict[str, Any]) -> List[str]:
        """Extract expiry dates from Dhan API response"""
        try:
            # Handle Dhan API response format: {"data": ["2026-02-03", ...], "status": "success"}
            if "data" in data and isinstance(data["data"], list):
                expiries = data["data"]
                logger.info(f"📅 Extracted {len(expiries)} expiries from Dhan API: {expiries[:5]}...")
                return expiries
            elif "expiries" in data and isinstance(data["expiries"], list):
                return data["expiries"]
            elif isinstance(data, list):
                return data
            else:
                logger.warning(f"⚠️ Unexpected expiry response format: {data}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Error extracting expiries from response: {e}")
            return []
    
    # STEP 2: DETERMINE EXPIRY DATES (SMARTLY)
    async def select_expiries_smartly(self, underlying: str) -> List[str]:
        """
        Select expiries based on rules from authoritative source
        """
        try:
            logger.info(f"🎯 Selecting expiries smartly for {underlying}")
            
            # Get all available expiries from authoritative source
            all_expiries = await self.fetch_authoritative_expiries(underlying)
            
            if not all_expiries:
                logger.error(f"❌ No expiries available for {underlying}")
                return []
            
            # Apply selection rules
            selected_expiries = self._apply_expiry_selection_rules(underlying, all_expiries)
            
            logger.info(f"✅ Selected {len(selected_expiries)} expiries for {underlying}: {selected_expiries}")
            return selected_expiries
            
        except Exception as e:
            logger.error(f"❌ Failed to select expiries for {underlying}: {e}")
            return []
    
    def _apply_expiry_selection_rules(self, underlying: str, all_expiries: List[str]) -> List[str]:
        """Apply expiry selection rules based on underlying type"""
        try:
            # Convert string dates to datetime for sorting
            expiry_dates = []
            for expiry_str in all_expiries:
                try:
                    expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d")
                    expiry_dates.append((expiry_date, expiry_str))
                except ValueError:
                    logger.warning(f"⚠️ Invalid expiry format: {expiry_str}")
                    continue
            
            # Sort by date
            expiry_dates.sort(key=lambda x: x[0])
            
            now = datetime.now()
            future_expiries = [(date, date_str) for date, date_str in expiry_dates if date > now]
            
            if not future_expiries:
                logger.warning(f"⚠️ No future expiries available for {underlying}")
                return []
            
            # Apply rules based on underlying type
            if underlying in self.expiry_rules["weekly_indices"]:
                # Weekly indices → next N weeklies (select next 4 weekly expiries)
                return self._select_weekly_expiries(future_expiries, count=4)
            
            elif underlying in self.expiry_rules["monthly_indices"]:
                # Monthly instruments → current + next monthly
                return self._select_monthly_expiries(future_expiries, count=2)
            
            elif underlying in self.expiry_rules["mcx_commodities"]:
                # MCX → current + next monthly
                return self._select_monthly_expiries(future_expiries, count=2)
            
            else:
                # Default for stocks - current + next monthly
                return self._select_monthly_expiries(future_expiries, count=2)
                
        except Exception as e:
            logger.error(f"❌ Error applying expiry selection rules for {underlying}: {e}")
            return []
    
    def _select_weekly_expiries(self, future_expiries: List[tuple], count: int) -> List[str]:
        """Select next N weekly expiries"""
        selected = []
        for date, date_str in future_expiries:
            if len(selected) >= count:
                break
            selected.append(date_str)
        return selected
    
    def _select_monthly_expiries(self, future_expiries: List[tuple], count: int) -> List[str]:
        """Select current + next monthly expiries"""
        selected = []
        seen_months = set()
        
        for date, date_str in future_expiries:
            if len(selected) >= count:
                break
            
            month_key = (date.year, date.month)
            if month_key not in seen_months:
                selected.append(date_str)
                seen_months.add(month_key)
        
        return selected
    
    # STEP 3: COMPUTE ATM (AUTOMATICALLY)
    async def compute_atm_automatic(self, underlying: str) -> Optional[float]:
        """
        Compute ATM automatically from WebSocket LTP
        NEVER manual input
        """
        try:
            logger.info(f"🎯 Computing ATM automatically for {underlying}")
            
            # Fetch LTP from WebSocket first
            ltp = await self._fetch_ltp_from_websocket(underlying)
            
            if ltp is None:
                # Fallback to Market Quote REST
                logger.warning(f"⚠️ WebSocket LTP not available for {underlying}, using REST fallback")
                ltp = await self._fetch_ltp_from_rest(underlying)
            
            if ltp is None:
                logger.error(f"❌ LTP unavailable for {underlying} - cannot compute ATM")
                return None
            
            # Read strike interval from instrument master cache
            strike_interval = self.instrument_master_cache.get(underlying, {}).get("strike_interval", 50.0)
            
            # Compute ATM using exact formula
            atm_strike = round(ltp / strike_interval) * strike_interval
            
            # Store in ATM registry
            self.atm_registry.atm_strikes[underlying] = atm_strike
            self.atm_registry.last_updated[underlying] = datetime.now()
            
            logger.info(f"✅ Computed ATM for {underlying}: LTP={ltp}, interval={strike_interval}, ATM={atm_strike}")
            return atm_strike
            
        except Exception as e:
            logger.error(f"❌ Failed to compute ATM for {underlying}: {e}")
            return None
    
    async def _fetch_ltp_from_websocket(self, underlying: str) -> Optional[float]:
        """Fetch LTP from WebSocket (prefered method)"""
        try:
            # TODO: Implement WebSocket LTP fetch
            # For now, return None to trigger REST fallback
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch WebSocket LTP for {underlying}: {e}")
            return None
    
    async def _fetch_ltp_from_rest(self, underlying: str) -> Optional[float]:
        """Fallback to Market Quote REST API"""
        try:
            # Use existing underlying price store
            from app.services.underlying_price_store import underlying_price_store
            
            underlying_data = underlying_price_store.get_underlying_ltp_api(underlying)
            
            if underlying_data["price_type"] == "UNAVAILABLE":
                return None
            
            return underlying_data["ltp"]
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch REST LTP for {underlying}: {e}")
            return None
    
    # STEP 4: GENERATE STRIKES (RULE-BASED)
    def generate_strikes_rule_based(self, underlying: str, atm_strike: float) -> List[float]:
        """
        Generate strikes ONLY relative to ATM using rules
        """
        try:
            logger.info(f"🎯 Generating strikes for {underlying} around ATM {atm_strike}")
            
            # Get strike rules for underlying
            if underlying in self.strike_rules:
                rules = self.strike_rules[underlying]
            else:
                # Default for stocks
                rules = self.strike_rules["STOCK_DEFAULT"]
            
            # Get strike interval from instrument master
            strike_interval = self.instrument_master_cache.get(underlying, {}).get("strike_interval", 50.0)
            
            # Generate strikes below ATM
            strikes = []
            for i in range(rules["below"], 0, -1):
                strike = atm_strike - (i * strike_interval)
                strikes.append(strike)
            
            # Add ATM strike
            strikes.append(atm_strike)
            
            # Generate strikes above ATM
            for i in range(1, rules["above"] + 1):
                strike = atm_strike + (i * strike_interval)
                strikes.append(strike)
            
            logger.info(f"✅ Generated {len(strikes)} strikes for {underlying} ({rules['below']} below + ATM + {rules['above']} above)")
            return strikes
            
        except Exception as e:
            logger.error(f"❌ Failed to generate strikes for {underlying}: {e}")
            return []
    
    # STEP 5: BUILD OPTION CHAIN SKELETON (REST)
    async def build_option_chain_skeleton_rest(self, underlying: str, expiry: str) -> bool:
        """
        Build option chain skeleton by calling DhanHQ REST Option Chain API
        """
        try:
            logger.info(f"🏗️ Building option chain skeleton for {underlying} {expiry}")
            
            # Compute ATM first (required for strike generation)
            atm_strike = await self.compute_atm_automatic(underlying)
            if atm_strike is None:
                logger.error(f"❌ Cannot build skeleton - ATM unavailable for {underlying}")
                return False
            
            # Generate strikes based on ATM
            strikes = self.generate_strikes_rule_based(underlying, atm_strike)
            if not strikes:
                logger.error(f"❌ Cannot build skeleton - no strikes generated for {underlying}")
                return False
            
            # Get segment and lot size from instrument master
            instrument_info = self.instrument_master_cache.get(underlying, {})
            segment = instrument_info.get("segment", "NSE")
            lot_size = instrument_info.get("lot_size", 50)
            strike_interval = instrument_info.get("strike_interval", 50.0)
            security_id = instrument_info.get("security_id")
            
            if not security_id:
                logger.error(f"❌ No Security ID found for {underlying}")
                return False
            
            # Call DhanHQ REST Option Chain API
            async with aiohttp.ClientSession() as session:
                url = f"{self.dhan_base_url}/v2/optionchain"
                payload = {
                    "UnderlyingScrip": security_id,
                    "UnderlyingSeg": segment,
                    "Expiry": expiry
                }
                
                # Add required headers
                headers = {
                    "access-token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5OTQ4MTUzLCJpYXQiOjE3Njk4NjE3NTMsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.RQxkoN0av9K0R5zkccN062l0IK53ooY30ocuWK2kUC7rfQas3kSiXBU4EHTMZ5Qv73j7JX97OmeRiBIdQcbN7w",
                    "client-id": "1100353799",
                    "Content-Type": "application/json"
                }
                
                logger.info(f"🔄 Calling Dhan Option Chain API for {underlying} {expiry}")
                
                async with session.post(url, json=payload, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Received option chain data for {underlying} {expiry}")
                        
                        # Build skeleton from REST response
                        skeleton = await self._build_skeleton_from_rest_response(
                            underlying, expiry, data, atm_strike, strikes, lot_size, strike_interval
                        )
                        
                        if skeleton:
                            # Store in central cache
                            if underlying not in self.option_chain_cache:
                                self.option_chain_cache[underlying] = {}
                            
                            self.option_chain_cache[underlying][expiry] = skeleton
                            
                            logger.info(f"✅ Built and cached option chain skeleton for {underlying} {expiry}")
                            logger.info(f"📊 Skeleton contains {len(skeleton.strikes)} strikes")
                            return True
                        else:
                            logger.error(f"❌ Failed to build skeleton from REST response for {underlying} {expiry}")
                            return False
                    else:
                        logger.error(f"❌ Dhan Option Chain API returned status {response.status}")
                        logger.error(f"Response: {await response.text()}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to build option chain skeleton for {underlying} {expiry}: {e}")
            return False
    
    async def _build_skeleton_from_rest_response(
        self, 
        underlying: str, 
        expiry: str, 
        data: Dict[str, Any], 
        atm_strike: float, 
        generated_strikes: List[float],
        lot_size: int,
        strike_interval: float
    ) -> Optional[OptionChainSkeleton]:
        """Build option chain skeleton from Dhan REST API response"""
        try:
            logger.info(f"🔍 Processing REST response for {underlying} {expiry}")
            
            # Extract option data from REST response
            rest_options = self._extract_options_from_rest_response(data)
            
            if not rest_options:
                logger.warning(f"⚠️ No option data in REST response for {underlying} {expiry}")
                return None
            
            # Build strikes dictionary
            strikes_dict = {}
            
            for strike_price in generated_strikes:
                # Find CE and PE data from REST response
                ce_data = self._find_option_data(rest_options, strike_price, "CE")
                pe_data = self._find_option_data(rest_options, strike_price, "PE")
                
                # Create OptionData objects
                ce_option = OptionData(
                    token=str(ce_data.get("security_id", "")),
                    ltp=ce_data.get("last_price"),
                    bid=ce_data.get("top_bid_price"),
                    ask=ce_data.get("top_ask_price"),
                    oi=ce_data.get("oi"),
                    volume=ce_data.get("volume"),
                    iv=ce_data.get("implied_volatility"),
                    greeks=ce_data.get("greeks", {})
                )
                
                pe_option = OptionData(
                    token=str(pe_data.get("security_id", "")),
                    ltp=pe_data.get("last_price"),
                    bid=pe_data.get("top_bid_price"),
                    ask=pe_data.get("top_ask_price"),
                    oi=pe_data.get("oi"),
                    volume=pe_data.get("volume"),
                    iv=pe_data.get("implied_volatility"),
                    greeks=pe_data.get("greeks", {})
                )
                
                # Create StrikeData object
                strike_data = StrikeData(
                    strike_price=strike_price,
                    CE=ce_option,
                    PE=pe_option
                )
                
                strikes_dict[strike_price] = strike_data
            
            # Create skeleton
            skeleton = OptionChainSkeleton(
                underlying=underlying,
                expiry=expiry,
                lot_size=lot_size,
                strike_interval=strike_interval,
                atm_strike=atm_strike,
                strikes=strikes_dict,
                last_updated=datetime.now()
            )
            
            logger.info(f"✅ Built skeleton with {len(strikes_dict)} strikes for {underlying} {expiry}")
            return skeleton
            
        except Exception as e:
            logger.error(f"❌ Error building skeleton from REST response: {e}")
            return None
    
    def _extract_options_from_rest_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract option data from Dhan REST response"""
        try:
            options = []
            
            # Handle Dhan API response format: {"data": {"oc": {"strike": {"ce": {...}, "pe": {...}}}}}
            if "data" in data and "oc" in data["data"]:
                oc_data = data["data"]["oc"]
                
                # Convert the nested structure to flat list of options
                for strike_price, strike_data in oc_data.items():
                    # Add CE option
                    if "ce" in strike_data:
                        ce_option = strike_data["ce"].copy()
                        ce_option["strike"] = float(strike_price)
                        ce_option["option_type"] = "CE"
                        options.append(ce_option)
                    
                    # Add PE option
                    if "pe" in strike_data:
                        pe_option = strike_data["pe"].copy()
                        pe_option["strike"] = float(strike_price)
                        pe_option["option_type"] = "PE"
                        options.append(pe_option)
            
            logger.info(f"📊 Extracted {len(options)} options from REST response")
            return options
            
        except Exception as e:
            logger.error(f"❌ Error extracting options from REST response: {e}")
            return []
    
    def _find_option_data(self, rest_options: List[Dict[str, Any]], strike_price: float, option_type: str) -> Dict[str, Any]:
        """Find specific option data from REST response"""
        try:
            # Search for matching option in the flat list
            for option in rest_options:
                # Check if strike and type match
                option_strike = option.get("strike")
                option_type_field = option.get("option_type")
                
                if (option_strike == strike_price and 
                    option_type_field == option_type):
                    return option
            
            # If not found, return empty data
            logger.warning(f"⚠️ {option_type} option at strike {strike_price} not found in REST response")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error finding option data: {e}")
            return {}
    
    async def build_complete_option_chain(self, underlying: str) -> bool:
        """
        Build complete option chain for all selected expiries
        """
        try:
            logger.info(f"🏗️ Building complete option chain for {underlying}")
            
            # STEP 2: Select expiries smartly
            selected_expiries = await self.select_expiries_smartly(underlying)
            
            if not selected_expiries:
                logger.error(f"❌ No expiries selected for {underlying}")
                return False
            
            logger.info(f"📅 Building chains for {len(selected_expiries)} expiries: {selected_expiries}")
            
            # STEP 5: Build skeleton for each expiry
            success_count = 0
            for expiry in selected_expiries:
                if await self.build_option_chain_skeleton_rest(underlying, expiry):
                    success_count += 1
                else:
                    logger.error(f"❌ Failed to build chain for {underlying} {expiry}")
            
            logger.info(f"✅ Built {success_count}/{len(selected_expiries)} option chains for {underlying}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to build complete option chain for {underlying}: {e}")
            return False
    
    # STEP 6: WEBSOCKET SUBSCRIPTIONS
    async def setup_websocket_subscriptions(self) -> bool:
        """
        Setup WebSocket subscriptions for all option tokens
        Max 5,000 per WebSocket, Max 5 connections
        """
        try:
            logger.info("🔌 Setting up WebSocket subscriptions...")
            
            # Extract ALL option tokens from cache
            all_tokens = []
            for underlying in self.option_chain_cache:
                for expiry in self.option_chain_cache[underlying]:
                    skeleton = self.option_chain_cache[underlying][expiry]
                    for strike_data in skeleton.strikes.values():
                        all_tokens.append(strike_data.CE.token)
                        all_tokens.append(stroke_data.PE.token)
            
            if not all_tokens:
                logger.warning("⚠️ No tokens to subscribe - option chain cache empty")
                return False
            
            logger.info(f"📊 Found {len(all_tokens)} tokens to subscribe")
            
            # Group tokens deterministically (max 5000 per WebSocket)
            max_tokens_per_ws = 5000
            max_connections = 5
            
            websocket_groups = []
            for i in range(0, len(all_tokens), max_tokens_per_ws):
                if len(websocket_groups) >= max_connections:
                    logger.warning(f"⚠️ Reached max WebSocket connections, skipping {len(all_tokens) - i} tokens")
                    break
                    
                group_tokens = all_tokens[i:i + max_tokens_per_ws]
                websocket_id = len(websocket_groups)
                websocket_groups.append((websocket_id, group_tokens))
            
            logger.info(f"🔌 Created {len(websocket_groups)} WebSocket groups")
            
            # TODO: Implement actual WebSocket connections
            # For now, just prepare the subscription mappings
            for websocket_id, tokens in websocket_groups:
                self.websocket_subscriptions[websocket_id] = set(tokens)
                
                # Map tokens to websocket_id
                for token in tokens:
                    self.token_to_websocket[token] = websocket_id
            
            logger.info(f"✅ Prepared WebSocket subscriptions for {len(all_tokens)} tokens")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup WebSocket subscriptions: {e}")
            return False
    
    # STEP 7: MERGE LIVE DATA (WEBSOCKET)
    def merge_live_data_from_websocket(self, token: str, price_data: Dict[str, Any]) -> bool:
        """
        Merge live WebSocket data into option chain cache
        Updates ONLY: LTP, Bid, Ask, Volume
        """
        try:
            # Find which WebSocket this token belongs to
            websocket_id = self.token_to_websocket.get(token)
            if websocket_id is None:
                logger.warning(f"⚠️ Token {token} not found in WebSocket subscriptions")
                return False
            
            # Find the option in cache and update it
            updated = False
            
            for underlying in self.option_chain_cache:
                for expiry in self.option_chain_cache[underlying]:
                    skeleton = self.option_chain_cache[underlying][expiry]
                    
                    for strike_price, strike_data in skeleton.strikes.items():
                        # Check CE
                        if strike_data.CE.token == token:
                            self._update_option_data_from_websocket(strike_data.CE, price_data)
                            updated = True
                            break
                        
                        # Check PE
                        if strike_data.PE.token == token:
                            self._update_option_data_from_websocket(strike_data.PE, price_data)
                            updated = True
                            break
                    
                    if updated:
                        break
                if updated:
                    break
            
            if updated:
                logger.debug(f"🔄 Updated live data for token {token}")
            else:
                logger.warning(f"⚠️ Token {token} not found in option chain cache")
            
            return updated
            
        except Exception as e:
            logger.error(f"❌ Failed to merge live data for token {token}: {e}")
            return False
    
    def _update_option_data_from_websocket(self, option_data: OptionData, websocket_data: Dict[str, Any]) -> None:
        """
        Update option data from WebSocket tick
        Updates ONLY: LTP, Bid, Ask, Volume
        """
        try:
            # Update only the fields that should come from WebSocket
            if "ltp" in websocket_data:
                option_data.ltp = websocket_data["ltp"]
            
            if "bid" in websocket_data or "best_bid" in websocket_data:
                option_data.bid = websocket_data.get("bid") or websocket_data.get("best_bid")
            
            if "ask" in websocket_data or "best_ask" in websocket_data:
                option_data.ask = websocket_data.get("ask") or websocket_data.get("best_ask")
            
            if "volume" in websocket_data:
                option_data.volume = websocket_data["volume"]
            
            # Note: OI, Greeks, IV remain from REST until refreshed periodically
            
        except Exception as e:
            logger.error(f"❌ Error updating option data from WebSocket: {e}")
    
    # STEP 8: CENTRAL CACHE (CRITICAL)
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
    
    # STEP 9: PERIODIC REFRESH RULES
    async def refresh_greeks_and_oi(self) -> bool:
        """
        Refresh Greeks and OI from REST API every 30-60 seconds
        """
        try:
            logger.info("🔄 Refreshing Greeks and OI from REST API...")
            
            refreshed_count = 0
            
            for underlying in self.option_chain_cache:
                for expiry in self.option_chain_cache[underlying]:
                    # Rebuild skeleton to get fresh Greeks and OI
                    if await self.build_option_chain_skeleton_rest(underlying, expiry):
                        refreshed_count += 1
            
            logger.info(f"✅ Refreshed Greeks and OI for {refreshed_count} option chains")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to refresh Greeks and OI: {e}")
            return False
    
    async def periodic_atm_recalculation(self) -> bool:
        """
        Periodic ATM recalculation - logical and continuous
        """
        try:
            logger.info("🔄 Recalculating ATM strikes...")
            
            updated_count = 0
            
            for underlying in list(self.atm_registry.atm_strikes.keys()):
                # Recompute ATM
                new_atm = await self.compute_atm_automatic(underlying)
                
                if new_atm and new_atm != self.atm_registry.atm_strikes[underlying]:
                    logger.info(f"🎯 ATM changed for {underlying}: {self.atm_registry.atm_strikes[underlying]} → {new_atm}")
                    
                    # TODO: Regenerate strikes if needed (market open, expiry rollover)
                    updated_count += 1
            
            logger.info(f"✅ Recalculated ATM for {len(self.atm_registry.atm_strikes)} underlyings, {updated_count} changed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed periodic ATM recalculation: {e}")
            return False
    
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

# Global instance
authoritative_option_chain_service = AuthoritativeOptionChainService()
