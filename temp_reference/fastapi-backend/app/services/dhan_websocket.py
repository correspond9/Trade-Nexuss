"""
Dhan WebSocket Service
Real-time market data from DhanHQ API v2
Implements proper WebSocket connection with compliance limits
"""

import asyncio
import json
import logging
import websockets
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import aiohttp
import jwt
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

@dataclass
class DhanCredentials:
    """Dhan API credentials"""
    client_id: str
    api_key: str
    access_token: str
    auth_type: str = "2"  # JWT token authentication

@dataclass
class DhanInstrument:
    """Dhan instrument format for v2 API"""
    exchange_segment: str
    security_id: str

class DhanWebSocketService:
    """
    Real Dhan WebSocket implementation
    Connects to DhanHQ API v2 WebSocket for real-time market data
    """
    
    def __init__(self):
        self.credentials: Optional[DhanCredentials] = None
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.subscribed_instruments: Set[str] = set()
        self.price_data: Dict[str, Dict] = {}
        self.connection_attempts = 0
        self.max_retries = 10
        self.backoff_base = 2  # seconds
        self.backoff_max = 60  # seconds
        self.last_error: Optional[str] = None
        
        # Dhan v2 WebSocket endpoint
        self.ws_url_base = "wss://api-feed.dhan.co"
        
        # Compliance limits
        self.max_connections = 5
        self.max_instruments_per_connection = 5000
        self.max_total_instruments = 25000
        
    async def load_credentials(self) -> bool:
        """Load Dhan credentials from file"""
        try:
            import json
            import os
            
            # Load from dhan_credentials.json file
            creds_file = os.path.join(os.path.dirname(__file__), '..', '..', 'dhan_credentials.json')
            
            if not os.path.exists(creds_file):
                logger.error("Credentials file not found")
                return False
                
            with open(creds_file, 'r') as f:
                creds_data = json.load(f)
            
            active_mode = creds_data.get('active_mode', 'DAILY_TOKEN')
            creds = creds_data.get(active_mode, {})
            
            if not creds.get('access_token'):
                logger.error("No access token found in credentials")
                return False
            
            self.credentials = DhanCredentials(
                client_id=creds['client_id'],
                api_key=creds.get('api_key', ''),
                access_token=creds['access_token'],
                auth_type="2"  # JWT token authentication
            )
            
            # Validate token
            try:
                decoded = jwt.decode(self.credentials.access_token, options={"verify_signature": False})
                expiry = datetime.fromtimestamp(decoded['exp'])
                if expiry < datetime.now():
                    logger.error("Dhan access token has expired")
                    return False
                    
                logger.info(f"Dhan credentials loaded successfully, expires: {expiry}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to validate Dhan token: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load Dhan credentials: {e}")
            return False
    
    def _build_websocket_url(self) -> str:
        """Build Dhan v2 WebSocket URL with authentication"""
        if not self.credentials:
            raise ValueError("No credentials loaded")
        
        params = {
            "version": "2",
            "token": self.credentials.access_token,
            "clientId": self.credentials.client_id,
            "authType": self.credentials.auth_type
        }
        
        return f"{self.ws_url_base}?{urlencode(params)}"
    
    def _convert_instrument_to_v2_format(self, instrument: str) -> DhanInstrument:
        """
        Convert instrument string to Dhan v2 format
        Examples:
        - "NIFTY" -> {"ExchangeSegment": "NSE_FNO", "SecurityId": "260105"}
        - "BANKNIFTY" -> {"ExchangeSegment": "NSE_FNO", "SecurityId": "260106"}
        - "SENSEX" -> {"ExchangeSegment": "BSE_FNO", "SecurityId": "22"}
        """
        # Handle index instruments
        if instrument == "NIFTY":
            return DhanInstrument("NSE_FNO", "260105")  # NIFTY index token
        elif instrument == "BANKNIFTY":
            return DhanInstrument("NSE_FNO", "260106")  # BANKNIFTY index token
        elif instrument == "SENSEX":
            return DhanInstrument("BSE_FNO", "22")  # SENSEX index token
        
        # Handle option instruments (format: NIFTY_20000_CE)
        if "_" in instrument:
            parts = instrument.split("_")
            if len(parts) == 3:
                symbol, strike, option_type = parts
                # For NIFTY options, use proper security ID format
                if symbol == "NIFTY":
                    # NIFTY options use specific security IDs
                    security_id = f"{strike}"  # Simplified for now
                else:
                    security_id = f"{symbol}{strike}"
                
                return DhanInstrument("NSE_FNO", security_id)  # Options are in FNO segment
        
        # Handle equity instruments (format: RELIANCE-EQ)
        if "-" in instrument:
            symbol = instrument.split("-")[0]
            return DhanInstrument("NSE_EQ", symbol)  # Equity cash segment
        
        # Default fallback
        return DhanInstrument("NSE_EQ", instrument)
    
    def _build_subscription_message(self, instruments: List[str]) -> Dict:
        """Build Dhan v2 subscription message"""
        instrument_list = []
        
        for instrument in instruments:
            dhan_instrument = self._convert_instrument_to_v2_format(instrument)
            instrument_list.append({
                "ExchangeSegment": dhan_instrument.exchange_segment,
                "SecurityId": dhan_instrument.security_id
            })
        
        return {
            "RequestCode": 15,  # Subscription request code
            "InstrumentCount": len(instrument_list),
            "InstrumentList": instrument_list
        }
    
    async def connect(self) -> bool:
        """Connect to Dhan WebSocket"""
        if not await self.load_credentials():
            return False
        
        if self.is_connected:
            logger.warning("Already connected to Dhan WebSocket")
            return True
        
        try:
            ws_url = self._build_websocket_url()
            logger.info(f"Connecting to Dhan WebSocket: {ws_url}")
            
            # Implement exponential backoff
            backoff_time = self.backoff_base * (2 ** min(self.connection_attempts, 5))
            backoff_time = min(backoff_time, self.backoff_max)
            
            if self.connection_attempts > 0:
                logger.info(f"Waiting {backoff_time}s before connection attempt {self.connection_attempts + 1}")
                await asyncio.sleep(backoff_time)
            
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.is_connected = True
            self.connection_attempts = 0
            self.last_error = None
            
            logger.info("Successfully connected to Dhan WebSocket")
            
            # Start message listener
            asyncio.create_task(self._message_listener())
            
            return True
            
        except Exception as e:
            self.connection_attempts += 1
            self.last_error = str(e)
            logger.error(f"Failed to connect to Dhan WebSocket (attempt {self.connection_attempts}): {e}")
            
            if self.connection_attempts >= self.max_retries:
                logger.error("Max connection attempts reached, giving up")
                return False
            
            return False
    
    async def disconnect(self):
        """Disconnect from Dhan WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
            self.is_connected = False
            logger.info("Disconnected from Dhan WebSocket")
    
    async def subscribe_index_tokens(self) -> bool:
        """Subscribe to index tokens for underlying price updates"""
        try:
            # Index tokens for underlying prices
            index_tokens = [
                {"ExchangeSegment": "NSE_INDEX", "SecurityId": "260105"},  # NIFTY
                {"ExchangeSegment": "NSE_INDEX", "SecurityId": "260106"},  # BANKNIFTY
                {"ExchangeSegment": "BSE_INDEX", "SecurityId": "260107"}   # SENSEX
            ]
            
            # Convert to Dhan v2 format
            dhan_instruments = [
                {"ExchangeSegment": token["ExchangeSegment"], "SecurityId": token["SecurityId"]}
                for token in index_tokens
            ]
            
            # Subscribe to index tokens
            success = await self.subscribe_instruments(dhan_instruments)
            
            if success:
                logger.info(f"✅ Subscribed to {len(index_tokens)} index tokens for underlying prices")
                
                # Mark tokens as unavailable initially until data arrives
                from app.services.underlying_price_store import underlying_price_store
                for token in index_tokens:
                    symbol_map = {"260105": "NIFTY", "260106": "BANKNIFTY", "260107": "SENSEX"}
                    symbol = symbol_map.get(token["SecurityId"])
                    if symbol:
                        underlying_price_store.mark_unavailable(symbol, "Awaiting WebSocket data")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to subscribe to index tokens: {e}")
            return False
    
    async def subscribe_instruments(self, instruments: List[Dict]) -> bool:
        """Subscribe to instruments for real-time data"""
        if not self.is_connected:
            logger.error("Not connected to Dhan WebSocket")
            return False
        
        try:
            subscription_message = self._build_subscription_message(instruments)
            
            await self.websocket.send(json.dumps(subscription_message))
            
            # Track subscribed instruments
            for instrument in instruments:
                instrument_key = f"{instrument.get('ExchangeSegment')}_{instrument.get('SecurityId')}"
                self.subscribed_instruments.add(instrument_key)
            
            logger.info(f"Subscribed to {len(instruments)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"Failed to subscribe to instruments: {e}")
            return False
    
    async def _message_listener(self):
        """Listen for WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse WebSocket message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Dhan WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket message listener: {e}")
            self.is_connected = False
    
    async def _process_message(self, data: Dict):
        """Process incoming WebSocket message"""
        try:
            # Handle different message types from Dhan
            if "RequestCode" in data:
                # Response to subscription/unsubscription
                logger.debug(f"Subscription response: {data}")
            elif "ExchangeSegment" in data and "SecurityId" in data:
                # Market data message
                await self._process_market_data(data)
            else:
                logger.debug(f"Unknown message format: {data}")
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    async def _process_market_data(self, data: Dict):
        """Process market data message and update UnderlyingPriceStore for indices"""
        try:
            exchange_segment = data.get("ExchangeSegment")
            security_id = data.get("SecurityId")
            ltp = data.get("LastTradedPrice", 0)
            
            # Convert back to our instrument format
            instrument_key = f"{exchange_segment}_{security_id}"
            
            # Extract price data
            price_data = {
                "ltp": ltp,
                "best_bid": data.get("BestBidPrice", 0),
                "best_ask": data.get("BestAskPrice", 0),
                "bid_qty": data.get("BestBidQuantity", 0),
                "ask_qty": data.get("BestAskQuantity", 0),
                "volume": data.get("VolumeTraded", 0),
                "oi": data.get("OpenInterest", 0),
                "timestamp": datetime.now(),
                "exchange_segment": exchange_segment,
                "security_id": security_id
            }
            
            # Store price data
            self.price_data[instrument_key] = price_data
            
            # Update price store for option chain service
            from app.services.websocket_price_store import price_store
            price_store.update_price(instrument_key, price_data)
            
            # 🎯 CRITICAL: Update UnderlyingPriceStore for INDEX instruments
            await self._update_underlying_store(exchange_segment, security_id, ltp, data)
            
        except Exception as e:
            logger.error(f"Error processing market data: {e}")
    
    async def _update_underlying_store(self, exchange_segment: str, security_id: str, ltp: float, data: Dict):
        """Update UnderlyingPriceStore for index instruments"""
        try:
            # Import here to avoid circular imports
            from app.services.underlying_price_store import underlying_price_store
            
            # Map Dhan tokens to index symbols
            index_token_map = {
                "260105": "NIFTY",      # NIFTY index token
                "260106": "BANKNIFTY", # BANKNIFTY index token  
                "260107": "SENSEX"      # SENSEX index token
            }
            
            # Check if this is an index instrument
            if security_id in index_token_map:
                symbol = index_token_map[security_id]
                
                # Get exchange timestamp from data if available, otherwise use now
                timestamp = datetime.now()
                if "ExchangeTimeStamp" in data:
                    try:
                        # Parse exchange timestamp if provided
                        timestamp_str = data["ExchangeTimeStamp"]
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    except:
                        timestamp = datetime.now()
                
                # Update UnderlyingPriceStore immediately (no throttling)
                underlying_price_store.update_price(symbol, ltp, timestamp, "WEBSOCKET")
                
                logger.info(f"📈 {symbol} index updated: {ltp} (token: {security_id})")
                
        except Exception as e:
            logger.error(f"Error updating underlying store: {e}")
    
    def get_price(self, instrument: str) -> Optional[Dict]:
        """Get latest price for an instrument"""
        # Convert instrument to Dhan format
        dhan_instrument = self._convert_instrument_to_v2_format(instrument)
        instrument_key = f"{dhan_instrument.exchange_segment}_{dhan_instrument.security_id}"
        
        return self.price_data.get(instrument_key)
    
    def get_connection_status(self) -> Dict:
        """Get connection status"""
        return {
            "connected": self.is_connected,
            "subscribed_instruments": len(self.subscribed_instruments),
            "connection_attempts": self.connection_attempts,
            "last_error": self.last_error,
            "credentials_loaded": self.credentials is not None
        }

# Global instance
dhan_websocket_service = DhanWebSocketService()