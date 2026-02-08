from datetime import datetime, time
import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Daily time to refresh lot sizes before market opens
REFRESH_TIME = time(8, 45, 0)


class LotSizeRefreshScheduler:
    def __init__(self) -> None:
        self.is_running = False
        self.last_refresh: Dict[str, datetime] = {}

    async def refresh_all_lot_sizes(self) -> bool:
        try:
            from app.services.dhan_security_id_mapper import dhan_security_mapper
            from app.services.authoritative_option_chain_service import authoritative_option_chain_service
            from app.commodity_engine.commodity_option_chain_service import commodity_option_chain_service
            from app.commodity_engine.commodity_futures_service import commodity_futures_service

            # Load latest CSV (includes lot sizes)
            ok = await dhan_security_mapper.load_security_ids()
            if not ok:
                logger.warning("⚠️ Lot size CSV loading failed; keeping existing mappings")

            # Update option chains (Tier A/B currently cached)
            chains = authoritative_option_chain_service.option_chain_cache
            updated_count = 0
            for underlying, exp_map in chains.items():
                lot = dhan_security_mapper.get_lot_size(underlying)
                if isinstance(lot, int) and lot > 0:
                    for expiry, skeleton in exp_map.items():
                        try:
                            skeleton.lot_size = lot
                            updated_count += 1
                        except Exception:
                            continue

            # Update MCX option chains
            mcx_chains = commodity_option_chain_service.option_chain_cache
            for symbol, exp_map in mcx_chains.items():
                lot = dhan_security_mapper.get_lot_size(symbol)
                if isinstance(lot, int) and lot > 0:
                    for expiry, skeleton in exp_map.items():
                        try:
                            skeleton["lot_size"] = lot
                            updated_count += 1
                        except Exception:
                            continue

            # Update MCX futures cache
            mcx_fut = commodity_futures_service.futures_cache
            for symbol, exp_map in mcx_fut.items():
                lot = dhan_security_mapper.get_lot_size(symbol)
                if isinstance(lot, int) and lot > 0:
                    for expiry, entry in exp_map.items():
                        try:
                            entry["lot_size"] = lot
                            updated_count += 1
                        except Exception:
                            continue

            self.last_refresh["LOT_SIZE"] = datetime.now()
            logger.info(f"✅ Lot sizes refreshed for {updated_count} cached instruments")
            return True

        except Exception as e:
            logger.error(f"❌ Error refreshing lot sizes: {e}", exc_info=True)
            return False

    async def _scheduler_loop(self):
        while self.is_running:
            try:
                now = datetime.now()
                target_time = datetime.combine(now.date(), REFRESH_TIME)
                if now.time() > REFRESH_TIME:
                    from datetime import timedelta
                    target_time += timedelta(days=1)
                sleep_seconds = (target_time - now).total_seconds()
                logger.info(f"⏰ Next lot size refresh scheduled at {target_time.strftime('%Y-%m-%d %H:%M:%S')} "
                            f"({sleep_seconds/3600:.1f} hours)")
                await asyncio.sleep(sleep_seconds)
                if self.is_running:
                    await self.refresh_all_lot_sizes()
            except asyncio.CancelledError:
                logger.info("🛑 Lot size refresh scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in lot size scheduler loop: {e}", exc_info=True)
                await asyncio.sleep(3600)

    async def start(self):
        if self.is_running:
            logger.warning("Lot size refresh scheduler already running")
            return
        logger.info("🚀 Starting lot size refresh scheduler...")
        self.is_running = True
        await self.refresh_all_lot_sizes()
        asyncio.create_task(self._scheduler_loop())

    async def stop(self):
        logger.info("🛑 Stopping lot size refresh scheduler...")
        self.is_running = False


lot_size_scheduler = LotSizeRefreshScheduler()


def get_lot_size_scheduler() -> LotSizeRefreshScheduler:
    return lot_size_scheduler
