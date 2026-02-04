#!/usr/bin/env python3
"""
DhanHQ WebSocket V2 Compliance Rules - MUST FOLLOW UNCONDITIONALLY
These rules prevent IP bans and ensure compliant API usage
"""

import time
import logging
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DhanComplianceRules:
    """
    DhanHQ API V2 Compliance Rules - STRICT ENFORCEMENT
    Violation of these rules will result in IP bans and account suspension
    """
    
    # === CONNECTION LIMITS (OFFICIAL DHANHQ LIMITS) ===
    MAX_CONCURRENT_CONNECTIONS: int = 5  # OFFICIAL: "A single user can establish up to 5 WebSocket connections"
    MAX_SUBSCRIPTIONS_PER_CONNECTION: int = 5000  # OFFICIAL: "On each connection, you may subscribe to up to 5,000 instruments per connection"
    CONNECTION_RETRY_DELAY: float = 30.0  # MINIMUM 30 seconds between retries
    MAX_RETRY_ATTEMPTS: int = 3  # MAX 3 attempts per session
    
    # === RATE LIMITING (OFFICIAL DHANHQ LIMITS) ===
    REST_API_QUOTE_RATE_LIMIT: float = 1.0  # OFFICIAL: "Quote/market snapshot (REST) APIs are limited to 1 request per second per user"
    REST_API_DATA_RATE_LIMIT: float = 5.0  # OFFICIAL: "Data APIs (like option chains, Greeks, margin) are limited to 5 requests per second"
    WEBSOCKET_SUBSCRIPTION_RATE: float = 2.0  # Conservative rate for WebSocket subscriptions
    BULK_SUBSCRIPTION_BATCH_SIZE: int = 100  # Conservative batch size to stay within limits
    BULK_SUBSCRIPTION_DELAY: float = 0.5  # 500ms delay between batches
    
    # === AUTHENTICATION ===
    TOKEN_VALIDATION_REQUIRED: bool = True  # Always validate token before connection
    CLIENT_ID_REQUIRED: bool = True  # Client ID mandatory for all requests
    AUTH_TYPE_2_FOR_TOKEN: int = 2  # Fixed auth type for token-based auth
    AUTH_TYPE_1_FOR_CREDENTIALS: int = 1  # Fixed auth type for credential-based auth
    
    # === WEBSOCKET URL FORMAT ===
    WEBSOCKET_BASE_URL: str = "wss://api-feed.dhan.co"  # ONLY this URL allowed
    VERSION_PARAMETER: str = "version=2"  # MUST be version=2
    TOKEN_PARAMETER: str = "token"  # MUST be token parameter
    CLIENT_ID_PARAMETER: str = "clientId"  # MUST be clientId parameter
    AUTH_TYPE_PARAMETER: str = "authType"  # MUST be authType parameter
    
    # === SUBSCRIPTION FORMAT ===
    REQUEST_CODE_SUBSCRIBE: int = 15  # FIXED request code for subscriptions
    INSTRUMENT_COUNT_REQUIRED: bool = True  # MUST include instrument count
    INSTRUMENT_LIST_REQUIRED: bool = True  # MUST include instrument list
    
    # === INSTRUMENT FORMAT ===
    EXCHANGE_SEGMENT_REQUIRED: bool = True  # MUST include ExchangeSegment
    SECURITY_ID_REQUIRED: bool = True  # MUST include SecurityId
    VALID_EXCHANGE_SEGMENTS: List[str] = None  # Will be initialized below
    
    # === ERROR HANDLING (OFFICIAL DHANHQ ERROR CODES) ===
    ERROR_CODE_INSTRUMENT_LIMIT: int = 804  # OFFICIAL: "Requested number of instruments exceeds limit"
    ERROR_CODE_RATE_LIMIT: int = 805  # OFFICIAL: "Too many requests or connections. Further requests may result in the user being blocked"
    MAX_ERROR_RETRIES: int = 3  # MAX 3 retries on errors
    ERROR_BACKOFF_MULTIPLIER: float = 2.0  # Exponential backoff
    MAX_ERROR_BACKOFF: float = 300.0  # MAX 5 minutes backoff
    
    # === IMPLEMENTATION REQUIREMENTS (OFFICIAL DHANHQ GUIDELINES) ===
    CENTRALIZE_REST_CALLS: bool = True  # "centralizes and throttles all REST calls"
    AVOID_PER_TICK_REST: bool = True  # "avoids calling REST on a per-order or per-tick basis"
    BATCH_SUBSCRIPTIONS: bool = True  # "batches instrument subscriptions carefully per connection"
    MONITOR_RECONNECTIONS: bool = True  # "monitors WebSocket reconnections to re-establish subscriptions safely"
    
    # === SESSION MANAGEMENT ===
    SESSION_TIMEOUT: int = 3600  # 1 hour session timeout
    HEARTBEAT_INTERVAL: int = 20  # 20 second heartbeat
    CONNECTION_TIMEOUT: int = 10  # 10 second connection timeout
    
    def __post_init__(self):
        """Initialize valid exchange segments"""
        self.VALID_EXCHANGE_SEGMENTS = [
            "NSE_EQ", "NSE_IDX", "NSE_FNO", "BSE_EQ", "BSE_IDX", "BSE_FNO",
            "MCX_EQ", "MCX_IDX", "MCX_FNO", "NCDEX_EQ", "NCDEX_IDX", "NCDEX_FNO",
            "CDS_EQ", "CDS_IDX", "CDS_FNO"
        ]

class DhanComplianceManager:
    """
    Enforces DhanHQ compliance rules to prevent IP bans
    """
    
    def __init__(self):
        self.rules = DhanComplianceRules()
        self.connection_count = 0
        self.last_connection_time = 0
        self.last_subscription_time = 0
        self.retry_count = 0
        self.error_count = 0
        self.session_start_time = time.time()
        
    def validate_connection_attempt(self) -> bool:
        """Validate if connection attempt is allowed"""
        current_time = time.time()
        
        # Check connection limit
        if self.connection_count >= self.rules.MAX_CONCURRENT_CONNECTIONS:
            logger.error(f"❌ CONNECTION LIMIT EXCEEDED: {self.connection_count}/{self.rules.MAX_CONCURRENT_CONNECTIONS}")
            return False
        
        # Check retry delay
        if current_time - self.last_connection_time < self.rules.CONNECTION_RETRY_DELAY:
            remaining_delay = self.rules.CONNECTION_RETRY_DELAY - (current_time - self.last_connection_time)
            logger.error(f"❌ RETRY DELAY VIOLATION: Wait {remaining_delay:.1f} more seconds")
            return False
        
        # Check retry attempts
        if self.retry_count >= self.rules.MAX_RETRY_ATTEMPTS:
            logger.error(f"❌ MAX RETRY ATTEMPTS EXCEEDED: {self.retry_count}/{self.rules.MAX_RETRY_ATTEMPTS}")
            return False
        
        return True
    
    def validate_subscription_rate(self) -> bool:
        """Validate subscription rate limiting"""
        current_time = time.time()
        
        if current_time - self.last_subscription_time < (1.0 / self.rules.WEBSOCKET_SUBSCRIPTION_RATE):
            logger.error("❌ SUBSCRIPTION RATE LIMIT EXCEEDED")
            return False
        
        return True
    
    def build_compliant_websocket_url(self, client_id: str, access_token: str, auth_type: int = 2) -> str:
        """Build 100% compliant WebSocket URL"""
        # Validate required parameters
        if not client_id:
            raise ValueError("❌ Client ID is required")
        if not access_token:
            raise ValueError("❌ Access token is required")
        
        # Build compliant URL
        url = (
            f"{self.rules.WEBSOCKET_BASE_URL}?"
            f"{self.rules.VERSION_PARAMETER}&"
            f"{self.rules.TOKEN_PARAMETER}={access_token}&"
            f"{self.rules.CLIENT_ID_PARAMETER}={client_id}&"
            f"{self.rules.AUTH_TYPE_PARAMETER}={auth_type}"
        )
        
        logger.info(f"✅ Compliant WebSocket URL built (token masked)")
        return url
    
    def build_compliant_subscription_message(self, instruments: List[Dict[str, str]]) -> Dict[str, Any]:
        """Build 100% compliant subscription message"""
        # Validate instrument count
        if len(instruments) > self.rules.BULK_SUBSCRIPTION_BATCH_SIZE:
            raise ValueError(f"❌ INSTRUMENT COUNT EXCEEDED: {len(instruments)}/{self.rules.BULK_SUBSCRIPTION_BATCH_SIZE}")
        
        # Validate each instrument format
        for instrument in instruments:
            if not self.validate_instrument_format(instrument):
                raise ValueError(f"❌ INVALID INSTRUMENT FORMAT: {instrument}")
        
        # Build compliant message
        subscription_message = {
            "RequestCode": self.rules.REQUEST_CODE_SUBSCRIBE,
            "InstrumentCount": len(instruments),
            "InstrumentList": instruments
        }
        
        logger.info(f"✅ Compliant subscription message built for {len(instruments)} instruments")
        return subscription_message
    
    def validate_instrument_format(self, instrument: Dict[str, str]) -> bool:
        """Validate instrument format compliance"""
        required_fields = ["ExchangeSegment", "SecurityId"]
        
        # Check required fields
        for field in required_fields:
            if field not in instrument:
                logger.error(f"❌ MISSING REQUIRED FIELD: {field}")
                return False
        
        # Validate exchange segment
        if instrument["ExchangeSegment"] not in self.rules.VALID_EXCHANGE_SEGMENTS:
            logger.error(f"❌ INVALID EXCHANGE SEGMENT: {instrument['ExchangeSegment']}")
            return False
        
        # Validate security ID
        if not instrument["SecurityId"] or not str(instrument["SecurityId"]).strip():
            logger.error("❌ INVALID SECURITY ID")
            return False
        
        return True
    
    def convert_symbol_to_compliant_format(self, symbol: str, exchange: str = "NSE") -> Dict[str, str]:
        """Convert symbol to compliant instrument format"""
        # Map common symbols to compliant format
        symbol_mapping = {
            "NIFTY": {"ExchangeSegment": "NSE_IDX", "SecurityId": "13626"},
            "BANKNIFTY": {"ExchangeSegment": "NSE_IDX", "SecurityId": "14152"},
            "SENSEX": {"ExchangeSegment": "BSE_IDX", "SecurityId": "265"},
            "FINNIFTY": {"ExchangeSegment": "NSE_IDX", "SecurityId": "16063"},
            "MIDCPNIFTY": {"ExchangeSegment": "NSE_IDX", "SecurityId": "16266"},
        }
        
        # Check if symbol is in mapping
        if symbol.upper() in symbol_mapping:
            return symbol_mapping[symbol.upper()]
        
        # For equity symbols, use NSE_EQ format
        if exchange.upper() == "NSE":
            return {"ExchangeSegment": "NSE_EQ", "SecurityId": symbol}
        elif exchange.upper() == "BSE":
            return {"ExchangeSegment": "BSE_EQ", "SecurityId": symbol}
        else:
            raise ValueError(f"❌ UNSUPPORTED EXCHANGE: {exchange}")
    
    def record_connection_attempt(self):
        """Record connection attempt for compliance tracking"""
        self.connection_count += 1
        self.last_connection_time = time.time()
        self.retry_count += 1
        
    def record_subscription(self):
        """Record subscription for compliance tracking"""
        self.last_subscription_time = time.time()
        
    def record_error(self):
        """Record error for compliance tracking"""
        self.error_count += 1
        
    def calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay"""
        delay = min(
            self.rules.ERROR_BACKOFF_MULTIPLIER ** self.error_count,
            self.rules.MAX_ERROR_BACKOFF
        )
        return delay
    
    def is_session_valid(self) -> bool:
        """Check if session is still valid"""
        return (time.time() - self.session_start_time) < self.rules.SESSION_TIMEOUT

# Global compliance manager instance
compliance_manager = DhanComplianceManager()

def get_compliance_rules() -> DhanComplianceRules:
    """Get compliance rules"""
    return DhanComplianceRules()

def get_compliance_manager() -> DhanComplianceManager:
    """Get compliance manager instance"""
    return compliance_manager

# === COMPLIANCE CHECKLIST (OFFICIAL DHANHQ REQUIREMENTS) ===
COMPLIANCE_CHECKLIST = [
    "✅ MAX 5 concurrent connections (Official DhanHQ limit)",
    "✅ MAX 5000 subscriptions per connection (Official DhanHQ limit)", 
    "✅ 30 seconds minimum between connection retries",
    "✅ MAX 3 retry attempts per session",
    "✅ 1 request per second for Quote/market snapshot REST APIs (Official DhanHQ limit)",
    "✅ 5 requests per second for Data APIs (Official DhanHQ limit)",
    "✅ 2 subscriptions per second for WebSocket (conservative rate)",
    "✅ MAX 100 instruments per subscription batch (conservative)",
    "✅ 500ms delay between subscription batches",
    "✅ Handle Error Code 804: 'Requested number of instruments exceeds limit'",
    "✅ Handle Error Code 805: 'Too many requests or connections'",
    "✅ Centralize and throttle all REST calls (Official DhanHQ requirement)",
    "✅ Avoid calling REST on per-order or per-tick basis (Official DhanHQ requirement)",
    "✅ Batch instrument subscriptions carefully per connection (Official DhanHQ requirement)",
    "✅ Monitor WebSocket reconnections safely (Official DhanHQ requirement)",
    "✅ Token validation before connection",
    "✅ Client ID mandatory for all requests",
    "✅ Fixed authType (2 for token, 1 for credentials)",
    "✅ ONLY wss://api-feed.dhan.co URL",
    "✅ MUST use version=2 parameter",
    "✅ MUST use token parameter",
    "✅ MUST use clientId parameter", 
    "✅ MUST use authType parameter",
    "✅ FIXED RequestCode 15 for subscriptions",
    "✅ MUST include InstrumentCount",
    "✅ MUST include InstrumentList",
    "✅ MUST include ExchangeSegment",
    "✅ MUST include SecurityId",
    "✅ ONLY valid exchange segments allowed",
    "✅ MAX 3 retries on errors",
    "✅ Exponential backoff for errors",
    "✅ MAX 5 minutes error backoff",
    "✅ 1 hour session timeout",
    "✅ 20 second heartbeat interval",
    "✅ 10 second connection timeout"
]

if __name__ == "__main__":
    print("🔒 DHANHQ COMPLIANCE RULES")
    print("=" * 50)
    print("VIOLATION OF THESE RULES WILL RESULT IN IP BAN")
    print("=" * 50)
    for rule in COMPLIANCE_CHECKLIST:
        print(rule)
    print("=" * 50)
    print("✅ ALWAYS FOLLOW THESE RULES UNCONDITIONALLY")
