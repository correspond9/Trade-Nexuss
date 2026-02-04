#!/usr/bin/env python3
"""
DhanHQ WebSocket V2 Compliant Implementation
STRICT COMPLIANCE - Follows all DhanHQ rules to prevent IP bans
"""

import asyncio
import websockets
import json
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Import compliance rules
from dhan_compliance_rules import get_compliance_manager, get_compliance_rules

logger = logging.getLogger(__name__)

@dataclass
class DhanWebSocketV2Config:
    """Dhan WebSocket V2 configuration with compliance enforcement"""
    # Compliance enforced limits
    max_connections: int = 5
    max_subscriptions_per_connection: int = 5000
    subscription_batch_size: int = 100
    subscription_rate_limit: float = 2.0  # 2 per second
    
    # Connection settings
    connection_timeout: int = 10
    ping_interval: int = 20
    ping_timeout: int = 10
    close_timeout: int = 10
    
    # Retry settings
    max_retry_attempts: int = 3
    retry_delay: float = 30.0  # 30 seconds minimum
    error_backoff_multiplier: float = 2.0
    max_error_backoff: float = 300.0  # 5 minutes max

class DhanWebSocketV2Client:
    """
    DhanHQ WebSocket V2 Client - 100% Compliant Implementation
    Follows all DhanHQ rules to prevent IP bans
    """
    
    def __init__(self, config: DhanWebSocketV2Config = None):
        self.config = config or DhanWebSocketV2Config()
        self.compliance_manager = get_compliance_manager()
        self.rules = get_compliance_rules()
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.connection_count = 0
        
        # Authentication
        self.client_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.auth_type: int = 2  # Default to token-based
        
        # Subscription management
        self.subscribed_instruments: List[Dict[str, str]] = []
        self.subscription_count = 0
        
        # Error tracking
        self.error_count = 0
        self.last_error_time = 0
        
        logger.info("🔒 Dhan WebSocket V2 Client initialized with compliance enforcement")
    
    def set_credentials(self, client_id: str, access_token: str, auth_type: int = 2):
        """Set authentication credentials with validation"""
        if not client_id or not access_token:
            raise ValueError("❌ Client ID and Access Token are required")
        
        self.client_id = client_id
        self.access_token = access_token
        self.auth_type = auth_type
        
        logger.info("✅ Credentials set (token masked for security)")
    
    async def connect(self) -> bool:
        """Connect to Dhan WebSocket V2 with compliance enforcement"""
        # Compliance check
        if not self.compliance_manager.validate_connection_attempt():
            logger.error("❌ Connection attempt blocked by compliance rules")
            return False
        
        if not self.client_id or not self.access_token:
            logger.error("❌ Credentials not set")
            return False
        
        try:
            # Build compliant WebSocket URL
            ws_url = self.compliance_manager.build_compliant_websocket_url(
                self.client_id, self.access_token, self.auth_type
            )
            
            logger.info("🔌 Attempting compliant WebSocket connection...")
            logger.info(f"📡 URL: {ws_url.split('?')[0]}?version=2&token=***&clientId={self.client_id}&authType={self.auth_type}")
            
            # Connect with compliance settings
            self.websocket = await websockets.connect(
                ws_url,
                ping_interval=self.config.ping_interval,
                ping_timeout=self.config.ping_timeout,
                close_timeout=self.config.close_timeout,
                max_queue=1024
            )
            
            self.is_connected = True
            self.connection_count += 1
            self.compliance_manager.record_connection_attempt()
            
            logger.info("✅ WebSocket connected successfully")
            logger.info(f"📊 Connection count: {self.connection_count}")
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            return True
            
        except Exception as e:
            self.is_connected = False
            self.error_count += 1
            self.compliance_manager.record_error()
            
            logger.error(f"❌ WebSocket connection failed: {type(e).__name__}: {e}")
            
            # Handle official DhanHQ error codes
            error_str = str(e)
            if "804" in error_str:
                logger.error("🚨 DHANHQ ERROR 804: 'Requested number of instruments exceeds limit'")
                logger.error("💡 REDUCE SUBSCRIPTION COUNT PER CONNECTION")
            elif "805" in error_str:
                logger.error("🚨 DHANHQ ERROR 805: 'Too many requests or connections'")
                logger.error("💡 REDUCE REQUEST RATE OR CONNECTION COUNT")
                logger.error("⚠️  FURTHER REQUESTS MAY RESULT IN USER BEING BLOCKED")
            elif "429" in error_str:
                logger.error("🚨 RATE LIMIT DETECTED - Backing off...")
                backoff_delay = self.compliance_manager.calculate_backoff_delay()
                logger.info(f"⏰ Waiting {backoff_delay:.1f} seconds before retry...")
                await asyncio.sleep(backoff_delay)
            
            return False
    
    async def connect_with_retry(self) -> bool:
        """Connect with compliant retry logic"""
        for attempt in range(self.config.max_retry_attempts):
            try:
                success = await self.connect()
                if success:
                    return True
                    
                if attempt < self.config.max_retry_attempts - 1:
                    # Calculate compliant backoff delay
                    delay = self.config.retry_delay * (self.config.error_backoff_multiplier ** attempt)
                    delay = min(delay, self.config.max_error_backoff)
                    
                    logger.info(f"🔄 Connection attempt {attempt + 1} failed. Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"❌ Retry attempt {attempt + 1} failed: {e}")
        
        logger.error("❌ Max connection attempts reached")
        return False
    
    async def subscribe_instruments(self, instruments: List[Dict[str, str]]) -> bool:
        """Subscribe to instruments with compliance enforcement"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to WebSocket")
            return False
        
        # Compliance check - subscription rate limiting
        if not self.compliance_manager.validate_subscription_rate():
            logger.error("❌ Subscription rate limit exceeded")
            return False
        
        # Validate subscription count
        total_subscriptions = len(self.subscribed_instruments) + len(instruments)
        if total_subscriptions > self.rules.MAX_SUBSCRIPTIONS_PER_CONNECTION:
            logger.error(f"❌ Subscription limit exceeded: {total_subscriptions}/{self.rules.MAX_SUBSCRIPTIONS_PER_CONNECTION}")
            return False
        
        try:
            # Process in compliant batches
            batch_size = self.config.subscription_batch_size
            for i in range(0, len(instruments), batch_size):
                batch = instruments[i:i + batch_size]
                
                # Build compliant subscription message
                subscription_message = self.compliance_manager.build_compliant_subscription_message(batch)
                
                # Send subscription
                await self.websocket.send(json.dumps(subscription_message))
                
                # Update subscription tracking
                self.subscribed_instruments.extend(batch)
                self.subscription_count += len(batch)
                self.compliance_manager.record_subscription()
                
                logger.info(f"📤 Subscribed to batch {i//batch_size + 1}: {len(batch)} instruments")
                logger.info(f"📊 Total subscriptions: {self.subscription_count}")
                
                # Compliance delay between batches
                if i + batch_size < len(instruments):
                    await asyncio.sleep(self.rules.BULK_SUBSCRIPTION_DELAY)
            
            logger.info(f"✅ Successfully subscribed to {len(instruments)} instruments")
            return True
            
        except Exception as e:
            self.error_count += 1
            self.compliance_manager.record_error()
            logger.error(f"❌ Subscription failed: {type(e).__name__}: {e}")
            return False
    
    async def subscribe_to_symbol(self, symbol: str, exchange: str = "NSE") -> bool:
        """Subscribe to a single symbol with compliance"""
        try:
            # Convert symbol to compliant format
            instrument = self.compliance_manager.convert_symbol_to_compliant_format(symbol, exchange)
            return await self.subscribe_instruments([instrument])
            
        except Exception as e:
            logger.error(f"❌ Failed to subscribe to {symbol}: {e}")
            return False
    
    async def unsubscribe_instruments(self, instruments: List[Dict[str, str]]) -> bool:
        """Unsubscribe from instruments"""
        if not self.is_connected or not self.websocket:
            logger.error("❌ Not connected to WebSocket")
            return False
        
        try:
            # Build unsubscribe message (RequestCode 16 for unsubscribe)
            unsubscribe_message = {
                "RequestCode": 16,  # Unsubscribe request code
                "InstrumentCount": len(instruments),
                "InstrumentList": instruments
            }
            
            await self.websocket.send(json.dumps(unsubscribe_message))
            
            # Update subscription tracking
            for instrument in instruments:
                if instrument in self.subscribed_instruments:
                    self.subscribed_instruments.remove(instrument)
                    self.subscription_count -= 1
            
            logger.info(f"📤 Unsubscribed from {len(instruments)} instruments")
            return True
            
        except Exception as e:
            logger.error(f"❌ Unsubscribe failed: {e}")
            return False
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages"""
        try:
            async for message in self.websocket:
                try:
                    # Handle binary messages (Dhan sends binary data)
                    if isinstance(message, (bytes, bytearray)):
                        await self._parse_binary_message(message)
                    else:
                        # Handle text messages
                        await self._parse_text_message(message)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing message: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"❌ Message handler error: {e}")
            self.is_connected = False
    
    async def _parse_binary_message(self, data: bytes):
        """Parse binary message from Dhan"""
        try:
            # Dhan binary message parsing logic here
            # This is a placeholder - implement actual binary parsing based on Dhan specs
            logger.debug(f"📨 Received binary message: {len(data)} bytes")
            
            # TODO: Implement actual binary message parsing
            # based on Dhan WebSocket V2 specification
            
        except Exception as e:
            logger.error(f"❌ Binary message parsing error: {e}")
    
    async def _parse_text_message(self, message: str):
        """Parse text message from Dhan"""
        try:
            data = json.loads(message)
            logger.debug(f"📨 Received text message: {data}")
            
            # TODO: Implement actual text message parsing
            # based on Dhan WebSocket V2 specification
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON parsing error: {e}")
        except Exception as e:
            logger.error(f"❌ Text message parsing error: {e}")
    
    async def disconnect(self):
        """Disconnect from WebSocket"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("🔌 WebSocket disconnected gracefully")
            except Exception as e:
                logger.error(f"❌ Error during disconnect: {e}")
            finally:
                self.websocket = None
                self.is_connected = False
                self.connection_count = 0
    
    def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status"""
        return {
            "is_connected": self.is_connected,
            "connection_count": self.connection_count,
            "subscription_count": self.subscription_count,
            "error_count": self.error_count,
            "client_id": self.client_id,
            "auth_type": self.auth_type,
            "compliance_status": "OK" if self.compliance_manager.is_session_valid() else "EXPIRED"
        }

# === COMPLIANT TEST FUNCTIONS ===

async def test_compliant_connection():
    """Test compliant WebSocket connection"""
    client = DhanWebSocketV2Client()
    
    # Set credentials (use real ones from API_cred.txt)
    client.set_credentials(
        client_id="1100353799",
        access_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzY5ODQzNjA5LCJpYXQiOjE3Njk3NTcyMDksInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTAwMzUzNzk5In0.bKl_DpJ8ePk5EqUTD4tWcSLvwBTgCzz2bZYwYqMcKkk5T___OJxXSIHfPTEKwz-7hkduQGCMebVDyjWPAuopLg",
        auth_type=2
    )
    
    try:
        # Test connection
        logger.info("🧪 Testing compliant WebSocket connection...")
        success = await client.connect_with_retry()
        
        if success:
            logger.info("✅ Connection successful!")
            
            # Test subscription with compliant symbols
            test_symbols = ["NIFTY", "BANKNIFTY"]
            for symbol in test_symbols:
                await client.subscribe_to_symbol(symbol)
                await asyncio.sleep(1)  # Compliance delay
            
            # Keep connection alive for testing
            await asyncio.sleep(5)
            
            # Get status
            status = client.get_connection_status()
            logger.info(f"📊 Final status: {status}")
            
        else:
            logger.error("❌ Connection failed")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🔒 DHAN WEBSOCKET V2 COMPLIANT TEST")
    print("=" * 50)
    print("This test follows all DhanHQ compliance rules")
    print("=" * 50)
    
    asyncio.run(test_compliant_connection())
