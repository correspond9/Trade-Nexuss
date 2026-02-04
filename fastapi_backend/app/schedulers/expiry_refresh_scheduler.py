"""
Daily Expiry Refresh Scheduler
Fetches expiry dates from DhanHQ REST API once daily during off-market hours
"""

import logging
from datetime import datetime, time
from typing import Dict, List
import asyncio
import aiohttp

logger = logging.getLogger(__name__)

# Run daily at 4:00 PM IST (post-market hours - market closes at 3:30 PM)
# Early refresh (4 PM instead of 9 PM) ensures expiry transitions happen same day
# Critical for expiry days when traders need next day's expiries for planning
REFRESH_TIME = time(16, 0, 0)

# Underlying instruments to fetch expiries for
# Includes all subscribed indices + MCX contracts for comprehensive coverage
# Source: instrument master CSV (SEGMENT=I rows → SECURITY_ID)
# NOTE: Dhan expirylist works with IDX_I segment for all indices (NSE + BSE)
UNDERLYINGS = {
    # NSE indices
    "NIFTY": {"security_id": 13, "segment": "IDX_I"},
    "BANKNIFTY": {"security_id": 25, "segment": "IDX_I"},
    "FINNIFTY": {"security_id": 27, "segment": "IDX_I"},
    "MIDCPNIFTY": {"security_id": 442, "segment": "IDX_I"},

    # BSE indices
    "SENSEX": {"security_id": 51, "segment": "IDX_I"},
    "BANKEX": {"security_id": 69, "segment": "IDX_I"},

    # MCX commodities (monthly expiries)
    # Note: These security IDs may need updating monthly - better to use instrument master auto-resolve
    # Commented out for now since MCX uses different expiry structure
    # "CRUDEOIL": {"security_id": 467013, "segment": "MCX_C"},
    # "NATURALGAS": {"security_id": 467016, "segment": "MCX_C"},
}


class ExpiryRefreshScheduler:
    """Manages daily expiry date refresh from DhanHQ API"""
    
    def __init__(self):
        self.is_running = False
        self.cached_expiries: Dict[str, List[str]] = {}
        self.last_refresh: Dict[str, datetime] = {}
    
    async def fetch_expiries_from_api(self, underlying: str, security_id: int, segment: str) -> List[str]:
        """
        Fetch expiry list from DhanHQ REST API
        
        Args:
            underlying: Instrument name (e.g., NIFTY, BANKNIFTY, FINNIFTY, etc.)
            security_id: Security ID from DhanHQ
            segment: Exchange segment (IDX_I for index options, MCX_C for commodities)
            
        Returns:
            List of expiry dates in YYYY-MM-DD format
        """
        try:
            # Get active credentials from database
            from app.storage.db import SessionLocal
            from app.storage.models import DhanCredential
            
            db = SessionLocal()
            creds_record = db.query(DhanCredential).filter(
                DhanCredential.is_default == True
            ).first() or db.query(DhanCredential).first()
            db.close()
            
            if not creds_record:
                logger.warning(f"No active credentials found for {underlying} expiry fetch")
                return []
            
            url = "https://api.dhan.co/v2/optionchain/expirylist"
            headers = {
                "access-token": creds_record.daily_token or creds_record.auth_token,
                "client-id": creds_record.client_id,
                "Content-Type": "application/json"
            }
            payload = {
                "UnderlyingScrip": security_id,
                "UnderlyingSeg": segment
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        expiries = data.get("data", [])
                        logger.info(f"✅ Fetched {len(expiries)} expiries for {underlying} from DhanHQ API")
                        return expiries
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ DhanHQ expiry API error for {underlying}: {response.status} - {error_text}")
                        return []
        
        except asyncio.TimeoutError:
            logger.error(f"⏱️ Timeout fetching expiries for {underlying}")
            return []
        except Exception as e:
            logger.error(f"❌ Error fetching expiries for {underlying}: {e}", exc_info=True)
            return []
    
    async def refresh_all_expiries(self) -> Dict[str, List[str]]:
        """
        Fetch expiries for all configured underlyings
        Respects DhanHQ rate limit: 1 request per 3 seconds
        
        Returns:
            Dict mapping underlying to expiry list
        """
        logger.info("🔄 Starting daily expiry refresh from DhanHQ API...")
        results = {}
        
        for underlying, config in UNDERLYINGS.items():
            expiries = await self.fetch_expiries_from_api(
                underlying=underlying,
                security_id=config["security_id"],
                segment=config["segment"]
            )
            
            if expiries:
                self.cached_expiries[underlying] = expiries
                self.last_refresh[underlying] = datetime.now()
                results[underlying] = expiries
                logger.info(f"📅 {underlying}: {expiries[:5]}{'...' if len(expiries) > 5 else ''}")
            else:
                logger.warning(f"⚠️ No expiries fetched for {underlying}, keeping cache")
                results[underlying] = self.cached_expiries.get(underlying, [])
            
            # Rate limit: Wait 3 seconds between requests
            await asyncio.sleep(3)
        
        logger.info(f"✅ Expiry refresh complete. Next refresh: tomorrow at {REFRESH_TIME.strftime('%I:%M %p')}")
        return results
    
    def get_expiries(self, underlying: str) -> List[str]:
        """
        Get cached expiries for an underlying
        
        Args:
            underlying: Instrument name (NIFTY, BANKNIFTY, SENSEX)
            
        Returns:
            List of expiry dates, or empty list if not cached
        """
        return self.cached_expiries.get(underlying, [])
    
    async def _scheduler_loop(self):
        """Background task that runs daily at configured time"""
        while self.is_running:
            try:
                now = datetime.now()
                target_time = datetime.combine(now.date(), REFRESH_TIME)
                
                # If target time already passed today, schedule for tomorrow
                if now.time() > REFRESH_TIME:
                    from datetime import timedelta
                    target_time += timedelta(days=1)
                
                # Calculate sleep duration
                sleep_seconds = (target_time - now).total_seconds()
                logger.info(f"⏰ Next expiry refresh scheduled at {target_time.strftime('%Y-%m-%d %H:%M:%S')} ({sleep_seconds/3600:.1f} hours)")
                
                await asyncio.sleep(sleep_seconds)
                
                # Execute refresh
                if self.is_running:
                    await self.refresh_all_expiries()
            
            except asyncio.CancelledError:
                logger.info("🛑 Expiry refresh scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in expiry scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Wait 1 hour on error before retrying
    
    async def start(self):
        """Start the scheduler background task"""
        if self.is_running:
            logger.warning("Expiry scheduler already running")
            return
        
        logger.info("🚀 Starting expiry refresh scheduler...")
        self.is_running = True
        
        # Run initial refresh immediately
        await self.refresh_all_expiries()
        
        # Start background loop
        asyncio.create_task(self._scheduler_loop())
    
    async def stop(self):
        """Stop the scheduler"""
        logger.info("🛑 Stopping expiry refresh scheduler...")
        self.is_running = False


# Global singleton instance
expiry_scheduler = ExpiryRefreshScheduler()


def get_expiry_scheduler() -> ExpiryRefreshScheduler:
    """Get the global expiry scheduler instance"""
    return expiry_scheduler
