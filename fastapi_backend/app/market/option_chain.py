"""
Option Chain Management Module
Provides interface for building and updating option chains from REST and WebSocket
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

def update(symbol: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update option chain from live ticks
    
    This is now delegated to AuthoritativeOptionChainService
    See: app/services/authoritative_option_chain_service.py
    """
    # Import here to avoid circular dependencies
    from app.services.authoritative_option_chain_service import authoritative_option_chain_service
    
    # The actual implementation is in the authoritative service
    # This is maintained for backwards compatibility
    logger.debug(f"Option chain update requested for {symbol}")
    
    return {
        "status": "redirected_to_authoritative_service",
        "message": "Use authoritative_option_chain_service for option chain operations"
    }
