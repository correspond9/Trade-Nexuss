"""
Market-Aware Cache Refresh Scheduler

Monitors market hours and automatically refreshes the option chain cache
with appropriate data source (LIVE during market hours, CLOSING otherwise).

This prevents the issue where:
- System starts during market hours with live prices
- Markets close → cache switches to closing prices  
- Markets open next day → BUT cache doesn't switch back to live prices

Solution: Check market status periodically and refresh cache when status changes.
"""

import logging
from datetime import datetime, time, timedelta
from typing import Dict, Optional
import asyncio
import os

logger = logging.getLogger(__name__)

# Check market status every 5 minutes
MARKET_CHECK_INTERVAL_SECONDS = 300  # 5 minutes

# Time windows for market checks
NSE_BSE_MARKET_HOURS = {
    "open_time": time(9, 15),      # 9:15 AM IST
    "close_time": time(15, 31)     # 3:31 PM IST
}

MCX_MARKET_HOURS = {
    "open_time": time(9, 0),       # 9:00 AM IST
    "close_time": time(23, 30)     # 11:30 PM IST
}

ENABLE_DHAN_REST_CLOSING_SNAPSHOT = (os.getenv("ENABLE_DHAN_REST_CLOSING_SNAPSHOT") or "").strip().lower() in {"1", "true", "yes", "on"}


class MarketAwareCacheScheduler:
    """
    Automatically refreshes option chain cache based on market hours.
    
    Ensures that:
    1. During market hours: Uses LIVE prices from DhanHQ API
    2. During off-hours: Uses CLOSING prices from fallback
    3. On market open/close: Automatically switches data source
    4. Works correctly regardless of when system is restarted
    """
    
    def __init__(self):
        self.is_running = False
        self.last_market_status: Dict[str, bool] = {}  # {exchange: is_open}
        self.last_refresh_time: Optional[datetime] = None
        self.last_successful_refresh: Optional[datetime] = None
        self.last_closing_run_date: Optional[str] = None
        
    def _is_market_open_for_exchange(self, exchange: str) -> bool:
        """Determine if market is open for given exchange"""
        try:
            now = datetime.now()
            current_time = now.time()
            
            # Skip checks on weekends
            if now.weekday() >= 5:  # Saturday=5, Sunday=6
                return False
            
            if exchange in ["NSE", "BSE"]:
                hours = NSE_BSE_MARKET_HOURS
            elif exchange == "MCX":
                hours = MCX_MARKET_HOURS
            else:
                # Unknown exchange - assume closed
                return False
            
            is_open = hours["open_time"] <= current_time <= hours["close_time"]
            return is_open
            
        except Exception as e:
            logger.error(f"❌ Error checking market status for {exchange}: {e}")
            return False
    
    async def _refresh_cache_if_needed(self) -> bool:
        """
        Check if market status changed since last refresh.
        If status changed, refresh cache with appropriate data source.
        
        Returns:
            True if refresh was performed, False if no refresh needed
        """
        try:
            from app.services.authoritative_option_chain_service import authoritative_option_chain_service
            
            # Check both NSE/BSE and MCX market status
            exchanges_to_check = ["NSE", "MCX"]
            status_changed = False
            first_run = any(exchange not in self.last_market_status for exchange in exchanges_to_check)
            
            for exchange in exchanges_to_check:
                current_status = self._is_market_open_for_exchange(exchange)
                last_status = self.last_market_status.get(exchange)
                
                if last_status is not None and last_status != current_status:
                    status_changed = True
                    event = "OPENED" if current_status else "CLOSED"
                    logger.info(f"🔄 MARKET {event}: {exchange}")
                
                self.last_market_status[exchange] = current_status
            
            if status_changed or first_run:
                if first_run:
                    logger.info("🔄 Initial market-aware cache refresh")
                else:
                    logger.info("🔄 Market status changed - refreshing option chain cache...")
                
                # Refresh with market-aware logic
                success = await authoritative_option_chain_service.populate_cache_with_market_aware_data()
                
                if success:
                    self.last_successful_refresh = datetime.now()
                    logger.info("✅ Cache refreshed successfully after market status change")
                    
                    # Log which data sources are now in use
                    cache_sources = authoritative_option_chain_service.cache_source
                    if cache_sources:
                        logger.info("Current data sources:")
                        for underlying, source in sorted(cache_sources.items()):
                            logger.info(f"   • {underlying}: {source}")
                else:
                    logger.warning("⚠️ Cache refresh failed - keeping current cache")
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error refreshing cache: {e}")
            return False
    
    async def _periodic_checker(self):
        """Background task that periodically checks market status"""
        while self.is_running:
            try:
                await asyncio.sleep(MARKET_CHECK_INTERVAL_SECONDS)
                
                if not self.is_running:
                    break
                
                self.last_refresh_time = datetime.now()
                await self._refresh_cache_if_needed()
                
                # Optional REST closing snapshot jobs (disabled by default).
                if ENABLE_DHAN_REST_CLOSING_SNAPSHOT:
                    try:
                        now = datetime.now()
                        today_key = now.date().isoformat()
                        close_time = NSE_BSE_MARKET_HOURS["close_time"]
                        if (
                            now.weekday() < 5  # Mon-Fri
                            and now.time() >= close_time
                            and self.last_closing_run_date != today_key
                        ):
                            logger.info("🕞 Running one-time closing snapshot job (15:31)...")
                            from app.services.authoritative_option_chain_service import authoritative_option_chain_service
                            ok = await authoritative_option_chain_service.populate_closing_snapshot_from_rest()
                            if ok:
                                self.last_closing_run_date = today_key
                                logger.info("✅ Closing snapshot job completed")
                            else:
                                logger.warning("⚠️ Closing snapshot job failed")
                        
                        # MCX one-time closing snapshot after 23:30
                        mcx_close_time = MCX_MARKET_HOURS["close_time"]
                        if (
                            now.weekday() < 5
                            and now.time() >= mcx_close_time
                            and self.last_closing_run_date != (today_key + "_MCX")
                        ):
                            logger.info("🕚 Running MCX closing snapshot job (23:30)...")
                            from app.commodity_engine import commodity_engine
                            ok2 = await commodity_engine.populate_closing_snapshot_from_rest()
                            if ok2:
                                self.last_closing_run_date = today_key + "_MCX"
                                logger.info("✅ MCX closing snapshot job completed")
                            else:
                                logger.warning("⚠️ MCX closing snapshot job failed")
                    except Exception as e:
                        logger.error(f"❌ Error running closing snapshot job: {e}")
                
            except asyncio.CancelledError:
                logger.info("🛑 Market-aware cache scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in market checker loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def start(self):
        """Start the market-aware cache scheduler"""
        if self.is_running:
            logger.warning("Market-aware cache scheduler already running")
            return
        
        logger.info("🚀 Starting market-aware cache scheduler...")
        logger.info(f"   • Will check market status every {MARKET_CHECK_INTERVAL_SECONDS//60} minutes")
        logger.info(f"   • NSE/BSE hours: {NSE_BSE_MARKET_HOURS['open_time'].strftime('%I:%M %p')} - {NSE_BSE_MARKET_HOURS['close_time'].strftime('%I:%M %p')}")
        logger.info(f"   • MCX hours: {MCX_MARKET_HOURS['open_time'].strftime('%I:%M %p')} - {MCX_MARKET_HOURS['close_time'].strftime('%I:%M %p')}")
        
        self.is_running = True
        
        # Perform initial market status check
        logger.info("Checking initial market status...")
        initial_check_task = asyncio.create_task(self._refresh_cache_if_needed())
        await initial_check_task
        
        # Start background monitoring
        asyncio.create_task(self._periodic_checker())
        logger.info("✅ Market-aware cache scheduler started")
    
    async def stop(self):
        """Stop the scheduler"""
        logger.info("🛑 Stopping market-aware cache scheduler...")
        self.is_running = False
    
    def get_status(self) -> Dict:
        """Get scheduler status information"""
        return {
            "is_running": self.is_running,
            "last_refresh_time": self.last_refresh_time.isoformat() if self.last_refresh_time else None,
            "last_successful_refresh": self.last_successful_refresh.isoformat() if self.last_successful_refresh else None,
            "market_status": self.last_market_status,
            "check_interval_seconds": MARKET_CHECK_INTERVAL_SECONDS
        }


# Global singleton instance
market_aware_cache_scheduler = MarketAwareCacheScheduler()


def get_market_aware_cache_scheduler() -> MarketAwareCacheScheduler:
    """Get the global market-aware cache scheduler instance"""
    return market_aware_cache_scheduler
