import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from app.market.instrument_master.loader import MASTER
from app.market_orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None
_bootstrap_task: Optional[asyncio.Task] = None
_ONE_TIME_CLEANUP_ACTION = "ONE_TIME_LEGACY_PURGE_V1"


def _env_bool(name: str, default: bool = False) -> bool:
    value = (os.getenv(name) or "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")

def get_scheduler():
    """Get or create the background scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def purge_previous_day_orders() -> dict:
    """Delete all order-book data older than current IST trading day."""
    db = None
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import MockOrder, MockTrade, ExecutionEvent

        db = SessionLocal()
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        ist_day_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

        old_order_ids = [
            row[0]
            for row in db.query(MockOrder.id)
            .filter(MockOrder.created_at < ist_day_start)
            .all()
        ]

        if not old_order_ids:
            return {
                "orders_removed": 0,
                "trades_removed": 0,
                "execution_events_removed": 0,
                "cutoff": ist_day_start.isoformat(),
            }

        execution_events_removed = (
            db.query(ExecutionEvent)
            .filter(ExecutionEvent.order_id.in_(old_order_ids))
            .delete(synchronize_session=False)
        )
        trades_removed = (
            db.query(MockTrade)
            .filter(MockTrade.order_id.in_(old_order_ids))
            .delete(synchronize_session=False)
        )
        orders_removed = (
            db.query(MockOrder)
            .filter(MockOrder.id.in_(old_order_ids))
            .delete(synchronize_session=False)
        )

        db.commit()
        return {
            "orders_removed": int(orders_removed or 0),
            "trades_removed": int(trades_removed or 0),
            "execution_events_removed": int(execution_events_removed or 0),
            "cutoff": ist_day_start.isoformat(),
        }
    except Exception:
        if db is not None:
            db.rollback()
        raise
    finally:
        if db is not None:
            db.close()


def purge_superadmin_previous_day_positions() -> dict:
    """Delete SUPER_ADMIN positions older than current IST trading day only."""
    db = None
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import MockPosition

        db = SessionLocal()
        now_ist = datetime.utcnow() + timedelta(hours=5, minutes=30)
        ist_day_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)

        deleted = (
            db.query(MockPosition)
            .filter(
                MockPosition.user_id == 1,
                MockPosition.created_at < ist_day_start,
            )
            .delete(synchronize_session=False)
        )

        db.commit()
        return {
            "positions_removed": int(deleted or 0),
            "cutoff": ist_day_start.isoformat(),
        }
    except Exception:
        if db is not None:
            db.rollback()
        raise
    finally:
        if db is not None:
            db.close()


def run_one_time_legacy_cleanup() -> dict:
    """
    Run destructive legacy cleanup exactly once:
    - purge previous-day order/trade/execution-event rows
    - purge previous-day SUPER_ADMIN positions only
    This must never run in daily EOD flow.
    """
    db = None
    try:
        from app.storage.db import SessionLocal
        from app.storage.models import SubscriptionLog

        db = SessionLocal()
        already_done = (
            db.query(SubscriptionLog.id)
            .filter(SubscriptionLog.action == _ONE_TIME_CLEANUP_ACTION)
            .first()
        )
        if already_done:
            return {
                "already_done": True,
                "orders_removed": 0,
                "trades_removed": 0,
                "execution_events_removed": 0,
                "superadmin_positions_removed": 0,
            }

        order_cleanup = purge_previous_day_orders()
        superadmin_pos_cleanup = purge_superadmin_previous_day_positions()

        log_entry = SubscriptionLog(
            action=_ONE_TIME_CLEANUP_ACTION,
            instrument_token="SYSTEM",
            reason=(
                "One-time legacy cleanup completed: "
                f"orders_removed={order_cleanup.get('orders_removed', 0)}, "
                f"trades_removed={order_cleanup.get('trades_removed', 0)}, "
                f"events_removed={order_cleanup.get('execution_events_removed', 0)}, "
                f"superadmin_positions_removed={superadmin_pos_cleanup.get('positions_removed', 0)}"
            ),
        )
        db.add(log_entry)
        db.commit()

        return {
            "already_done": False,
            "orders_removed": int(order_cleanup.get("orders_removed", 0) or 0),
            "trades_removed": int(order_cleanup.get("trades_removed", 0) or 0),
            "execution_events_removed": int(order_cleanup.get("execution_events_removed", 0) or 0),
            "superadmin_positions_removed": int(superadmin_pos_cleanup.get("positions_removed", 0) or 0),
        }
    except Exception:
        if db is not None:
            db.rollback()
        raise
    finally:
        if db is not None:
            db.close()

def eod_cleanup():
    """
    End-of-Day (4:00 PM IST) cleanup task
    - Unsubscribe Tier A (user watchlist) subscriptions except globally protected open-position symbols
    - Clear watchlist entries except globally protected open-position symbols
    - Preserve Tier B (always-on) subscriptions
    - Reset system for next trading session
    """
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.watchlist_manager import WATCHLIST_MGR
        from app.storage.db import SessionLocal
        
        print("\n" + "="*70)
        print("[EOD] Starting End-of-Day cleanup (4:00 PM IST)")
        print("="*70)
        
        # Get subscription stats before cleanup
        stats_before = SUBSCRIPTION_MGR.get_ws_stats()
        print(f"[EOD] Before cleanup:")
        print(f"  • Total subscriptions: {stats_before['total_subscriptions']}")
        print(f"  • Tier A (user watchlists): {stats_before['tier_a_count']}")
        print(f"  • Tier B (always-on): {stats_before['tier_b_count']}")

        protected_keys = SUBSCRIPTION_MGR.get_global_open_position_protected_keys()
        print(f"\n[EOD] Protected symbol-expiry keys (open positions): {len(protected_keys)}")
        
        # Phase 1: Unsubscribe Tier A subscriptions (except protected)
        tier_a_unsubscribed = SUBSCRIPTION_MGR.unsubscribe_all_tier_a(protected_keys=protected_keys)
        print(f"\n[EOD] Phase 1 - Unsubscribed {tier_a_unsubscribed} Tier A instruments")

        # Phase 2: Clear watchlists (except protected)
        watchlist_result = WATCHLIST_MGR.clear_all_watchlists(protected_keys=protected_keys)
        watchlist_cleared = int(watchlist_result.get("cleared_count") or 0)
        watchlist_skipped = int(watchlist_result.get("skipped_count") or 0)
        if not watchlist_result.get("success"):
            print(f"[EOD-WARN] Watchlist clear failed: {watchlist_result.get('message')}")
        print(f"[EOD] Phase 2 - Cleared watchlist entries: {watchlist_cleared}, Skipped (protected): {watchlist_skipped}")
        
        # Get stats after cleanup
        stats_after = SUBSCRIPTION_MGR.get_ws_stats()
        print(f"\n[EOD] After cleanup:")
        print(f"  • Total subscriptions: {stats_after['total_subscriptions']}")
        print(f"  • Tier A (user watchlists): {stats_after['tier_a_count']}")
        print(f"  • Tier B (always-on): {stats_after['tier_b_count']}")
        
        # Log EOD cleanup event to database
        try:
            from app.storage.models import SubscriptionLog
            db = SessionLocal()
            log_entry = SubscriptionLog(
                action="EOD_CLEANUP",
                instrument_token="ALL_TIER_A",
                reason=(
                    f"End-of-day cleanup: unsubscribed={tier_a_unsubscribed}, "
                    f"watchlist_cleared={watchlist_cleared}, "
                    f"watchlist_skipped={watchlist_skipped}, "
                    f"protected_keys={len(protected_keys)}"
                )
            )
            db.add(log_entry)
            db.commit()
            db.close()
            print(f"\n[EOD] Logged cleanup event to database")
        except Exception as e:
            print(f"\n[EOD-WARN] Failed to log event: {e}")
        
        print(f"[EOD] ✓ Cleanup complete - system ready for next session")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"[EOD-ERROR] Cleanup failed: {e}", exc_info=True)
        print(f"\n[EOD-ERROR] Cleanup failed: {e}\n")

_EXPIRY_FORMATS = ("%d%b%Y", "%d%B%Y", "%d%b%y", "%Y-%m-%d")


def _parse_expiry_value(value: str):
    text = (value or "").strip().upper()
    for fmt in _EXPIRY_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _get_exchange_id(record: dict) -> Optional[int]:
    """Extract exchange ID from instrument record."""
    exch = record.get("EXCH_ID") or ""
    if isinstance(exch, int):
        return exch
    try:
        return int(exch)
    except (ValueError, TypeError):
        return None


def _find_next_expiry(symbol: str, exchange_id: Optional[int] = None) -> Optional[str]:
    """Find next expiry for a symbol, optionally filtered by exchange.
    
    Args:
        symbol: Instrument symbol (e.g., 'CRUDEOIL', 'NIFTY')
        exchange_id: Optional exchange ID to filter by (5=MCX, 0=NSE, etc.)
    """
    try:
        from app.market.instrument_master.registry import REGISTRY
        
        # Get all records for symbol
        all_records = REGISTRY.get_by_symbol(symbol.upper())
        if not all_records:
            return None
        
        # Filter by exchange if specified
        if exchange_id is not None:
            filtered_records = [
                r for r in all_records 
                if _get_exchange_id(r) == exchange_id
            ]
        else:
            filtered_records = all_records
        
        if not filtered_records:
            return None
        
        # Extract unique expiries from filtered records
        expiries = sorted(set(
            r.get("SM_EXPIRY_DATE") or r.get("EXPIRY") or r.get("EXPIRY_DATE")
            for r in filtered_records
            if r.get("SM_EXPIRY_DATE") or r.get("EXPIRY") or r.get("EXPIRY_DATE")
        ))
        
        import sys
        sys.stderr.write(f"[LOAD-TB] _find_next_expiry({symbol}, exchange={exchange_id}): Found {len(expiries)} expiries\n")
        if expiries:
            sys.stderr.write(f"[LOAD-TB]   Expiries: {expiries[:5]}...\n")
        sys.stderr.flush()
    except Exception as e:
        import sys
        sys.stderr.write(f"[LOAD-TB] _find_next_expiry({symbol}): EXCEPTION {e}\n")
        sys.stderr.flush()
        return None

    if not expiries:
        return None

    today = datetime.utcnow().date()
    parsed = []
    for raw in expiries:
        dt = _parse_expiry_value(raw)
        if dt:
            parsed.append((dt, raw))

    if not parsed:
        import sys
        sys.stderr.write(f"[LOAD-TB]   FALLBACK: Returning first raw expiry: {expiries[0]}\n")
        sys.stderr.flush()
        return expiries[0]

    future = [item for item in parsed if item[0] >= today]
    target = min(future or parsed, key=lambda item: item[0])
    import sys
    sys.stderr.write(f"[LOAD-TB]   RESOLVED: {target[1]}\n")
    sys.stderr.flush()
    return target[1]


def ensure_tier_b_etf_subscriptions() -> tuple[int, int]:
    """Ensure Tier-B ETF symbols are subscribed (separate from Tier-B equities)."""
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.instrument_master.tier_b_etf_symbols import get_tier_b_etf_symbols

        symbols = sorted(get_tier_b_etf_symbols() or set())
        if not symbols:
            return 0, 0

        active_tier_b = SUBSCRIPTION_MGR.list_active_subscriptions(tier="TIER_B")
        existing_tokens = {str(row.get("token") or "") for row in active_tier_b}

        subscribed = 0
        failed = 0
        for symbol in symbols:
            token = f"ETF_{symbol.upper()}"
            if token in existing_tokens:
                continue

            ok, _msg, _ws_id = SUBSCRIPTION_MGR.subscribe(
                token=token,
                symbol=symbol,
                expiry=None,
                strike=None,
                option_type=None,
                tier="TIER_B",
            )
            if ok:
                subscribed += 1
            else:
                failed += 1

        if subscribed:
            SUBSCRIPTION_MGR.sync_to_db()
        return subscribed, failed
    except Exception:
        return 0, 0


def ensure_tier_b_equity_subscriptions() -> tuple[int, int]:
    """Ensure Tier-B EQUITY symbols are subscribed (always-on equities)."""
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.instrument_master.tier_a_equity_symbols import get_tier_a_equity_symbols

        symbols = sorted(get_tier_a_equity_symbols() or set())
        if not symbols:
            return 0, 0

        active_tier_b = SUBSCRIPTION_MGR.list_active_subscriptions(tier="TIER_B")
        existing_tokens = {str(row.get("token") or "") for row in active_tier_b}

        subscribed = 0
        failed = 0
        for symbol in symbols:
            token = f"EQUITY_{symbol.upper()}"
            if token in existing_tokens:
                continue

            ok, _msg, _ws_id = SUBSCRIPTION_MGR.subscribe(
                token=token,
                symbol=symbol,
                expiry=None,
                strike=None,
                option_type=None,
                tier="TIER_B",
            )
            if ok:
                subscribed += 1
            else:
                failed += 1

        if subscribed:
            SUBSCRIPTION_MGR.sync_to_db()
        return subscribed, failed
    except Exception:
        return 0, 0


def purge_tier_b_equity_subscriptions() -> tuple[int, int]:
    """Remove legacy always-on Tier-B equity subscriptions (EQUITY_* tokens)."""
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR

        active_tier_b = SUBSCRIPTION_MGR.list_active_subscriptions(tier="TIER_B")
        targets = [
            row for row in active_tier_b
            if str(row.get("token") or "").upper().startswith("EQUITY_")
            and not row.get("option_type")
        ]

        removed = 0
        failed = 0
        for row in targets:
            token = str(row.get("token") or "")
            ok, _msg = SUBSCRIPTION_MGR.unsubscribe(token, reason="EQUITY_LIST_TIERA_MIGRATION")
            if ok:
                removed += 1
            else:
                failed += 1

        if targets:
            SUBSCRIPTION_MGR.sync_to_db()
        return removed, failed
    except Exception:
        return 0, 0


async def load_tier_b_chains():
    """
    PHASE 3: Pre-load Tier B subscriptions at startup
    
    Tier B includes:
    - Index options (NIFTY50, BANKNIFTY, SENSEX) from option chain service
    - ETF equities from MW-ETF source list (always-on)
    - MCX futures and options (CRUDEOIL, NATURALGAS) from fallback
    
    Total: ~612 subscriptions from option chains + MCX contracts
    """
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.atm_engine import ATM_ENGINE
        from app.market.live_prices import get_prices
        from app.services.authoritative_option_chain_service import authoritative_option_chain_service
        from app.market.instrument_master.tier_b_etf_symbols import get_tier_b_etf_symbols

        print("\n" + "="*70)
        print("[STARTUP-PHASE3] Loading Tier B Subscriptions from Option Chain Service")
        print("="*70)

        all_prices = get_prices()
        total_subscribed = 0
        total_failed = 0

        # ✨ NEW: Load option chains from authoritative service
        print("\n[INDEX OPTIONS] Loading from option chain service...")
        try:
            # Initialize and populate the option chain service
            await authoritative_option_chain_service.populate_cache_with_market_aware_data()
            
            # Get available underlyings
            underlyings = authoritative_option_chain_service.get_available_underlyings()
            print(f"  Found underlyings: {underlyings}")
            
            for underlying in underlyings:
                expiries = authoritative_option_chain_service.get_available_expiries(underlying)
                print(f"  {underlying}: {len(expiries)} expiries")
                
                underlying_ltp = all_prices.get(underlying) or 25000  # Fallback
                
                for expiry in expiries:
                    # Get option chain from cache
                    option_chain = authoritative_option_chain_service.get_option_chain_from_cache(underlying, expiry)
                    if not option_chain:
                        print(f"    ❌ No option chain for {underlying} {expiry}")
                        continue
                    
                    # Subscribe all strikes
                    strikes = option_chain.get('strikes', {})
                    print(f"    📊 {expiry}: {len(strikes)} strikes")
                    
                    for strike_price, strike_data in strikes.items():
                        # Subscribe CE option
                        ce_token = strike_data.get('CE', {}).get('token')
                        if ce_token:
                            success, msg, ws_id = SUBSCRIPTION_MGR.subscribe(
                                token=str(ce_token),
                                symbol=underlying,
                                expiry=expiry,
                                strike=float(strike_price),
                                option_type="CE",
                                tier="TIER_B"
                            )
                            if success:
                                total_subscribed += 1
                            else:
                                total_failed += 1
                        else:
                            total_failed += 1
                        
                        # Subscribe PE
                        pe_token = strike_data.get('PE', {}).get('token')
                        if pe_token:
                            success, msg, ws_id = SUBSCRIPTION_MGR.subscribe(
                                token=str(pe_token),
                                symbol=underlying,
                                expiry=expiry,
                                strike=float(strike_price),
                                option_type="PE",
                                tier="TIER_B"
                            )
                            if success:
                                total_subscribed += 1
                            else:
                                total_failed += 1
            
            print(f"  ✓ Index options subscribed: {total_subscribed}")
            
        except Exception as e:
            print(f"  ❌ Failed to load option chains: {e}")
            print(f"  ⚠️ Falling back to hardcoded indices...")
            
            # Fallback to hardcoded indices
            tier_b_instruments = [
                ("NIFTY", ["2026-02-10", "2026-02-17"]),  # Example expiries
                ("BANKNIFTY", ["2026-02-10", "2026-02-17"]),
                ("SENSEX", ["2026-02-10", "2026-02-17"]),
            ]
            
            for symbol, expiries in tier_b_instruments:
                underlying_ltp = all_prices.get(symbol) or 25000
                print(f"  {symbol}: {len(expiries)} expiries, LTP={underlying_ltp}")
                
                for expiry in expiries:
                    # Generate ATM-based strikes (simplified)
                    atm_strike = round(underlying_ltp / 50) * 50  # NIFTY step = 50
                    strikes = [atm_strike + (i * 50) for i in range(-10, 11)]  # ATM ± 10 strikes
                    
                    for strike in strikes:
                        for option_type in ["CE", "PE"]:
                            token = f"{symbol}_{expiry}_{strike}{option_type}"
                            success, msg, ws_id = SUBSCRIPTION_MGR.subscribe(
                                token=token,
                                symbol=symbol,
                                expiry=expiry,
                                strike=float(strike),
                                option_type=option_type,
                                tier="TIER_B"
                            )
                            if success:
                                total_subscribed += 1
                            else:
                                total_failed += 1

        # Load always-on Tier-B equities (separate from ETF list).
        print("\n[EQUITIES] Loading Tier-B always-on equities...")
        eq_subscribed, eq_failed = await asyncio.to_thread(ensure_tier_b_equity_subscriptions)
        total_subscribed += int(eq_subscribed)
        total_failed += int(eq_failed)
        print(f"  ✓ Tier-B equities subscribed: {eq_subscribed} | failed: {eq_failed}")

        # Load optional Tier-B ETFs (if enabled by env).
        print("\n[ETFs] Loading Tier-B ETFs (if enabled)...")
        etf_expected = len(get_tier_b_etf_symbols() or set())
        etf_subscribed, etf_failed = await asyncio.to_thread(ensure_tier_b_etf_subscriptions)
        total_subscribed += int(etf_subscribed)
        total_failed += int(etf_failed)
        print(f"  ✓ Tier-B ETFs expected: {etf_expected}, subscribed: {etf_subscribed} | failed: {etf_failed}")

        # Print summary
        stats = SUBSCRIPTION_MGR.get_ws_stats()
        print("\n" + "="*70)
        print("[STARTUP-PHASE3] Tier B Pre-loading Complete")
        print("="*70)
        print(f"✓ Tier B subscriptions: {stats['tier_b_count']:,}")
        print(f"✓ Total subscriptions: {stats['total_subscriptions']:,}")
        print(f"✓ System utilization: {stats['utilization_percent']:.1f}%")
        print(f"✓ Subscribed: {total_subscribed:,} | Failed: {total_failed:,}")
        
        # ✨ NEW: Sync subscriptions to database for persistence
        print(f"\n[DB] Syncing subscriptions to database...")
        SUBSCRIPTION_MGR.sync_to_db()
        print(f"✓ Database sync completed")
        
        print(f"\nWebSocket Distribution:")
        for ws_id, count in sorted(stats['ws_usage'].items()):
            percent = (count / 5000) * 100
            print(f"  WS-{ws_id}: {count:,} / 5,000 ({percent:.1f}%)")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[STARTUP-PHASE3-ERROR] Failed to load Tier B: {e}")
        import traceback
        traceback.print_exc()
        print(f"Continuing without Tier B pre-loading...")
        print("="*70 + "\n")

async def on_start():
    """Application startup - initialize managers and scheduler"""
    global _bootstrap_task
    logger.info("[STARTUP] Initializing Broking Terminal V2 Backend")

    # Run heavy initialization in the background so startup can complete quickly
    # (prevents healthcheck restart loops).
    def _log_task_result(task: asyncio.Task, name: str) -> None:
        exc = task.exception()
        if exc:
            logger.exception("[STARTUP] Background task '%s' failed", name, exc_info=exc)

    async def _bootstrap_after_startup() -> None:
        logger.info("[STARTUP] Background bootstrap started")
        is_production = (os.getenv("ENVIRONMENT") or "").strip().lower() == "production"

        # Start EOD scheduler
        try:
            scheduler = get_scheduler()
            scheduler.add_job(
                eod_cleanup,
                'cron',
                hour=16,
                minute=0,
                id='eod_cleanup',
                name='End-of-Day Cleanup',
                replace_existing=True,
                max_instances=1
            )
            if not scheduler.running:
                scheduler.start()
            logger.info("[STARTUP] EOD scheduler started")
        except Exception:
            logger.exception("[STARTUP] Failed to start EOD scheduler")

        # Ensure database schema exists before any managers query tables
        from app.storage.migrations import init_db
        await asyncio.to_thread(init_db)

        # One-time legacy destructive cleanup (must not run in daily EOD)
        try:
            cleanup_result = await asyncio.to_thread(run_one_time_legacy_cleanup)
            if cleanup_result.get("already_done"):
                logger.info("[STARTUP] One-time legacy cleanup already completed")
            else:
                logger.warning(
                    "[STARTUP] One-time legacy cleanup executed "
                    "(orders_removed=%s trades_removed=%s events_removed=%s superadmin_positions_removed=%s)",
                    cleanup_result.get("orders_removed", 0),
                    cleanup_result.get("trades_removed", 0),
                    cleanup_result.get("execution_events_removed", 0),
                    cleanup_result.get("superadmin_positions_removed", 0),
                )
        except Exception:
            logger.exception("[STARTUP] One-time legacy cleanup failed")

        # Load instrument master
        load_master = _env_bool("STARTUP_LOAD_MASTER", default=not is_production)
        if load_master:
            logger.info("[STARTUP] Loading instrument master...")
            await asyncio.to_thread(MASTER.load)
            logger.info("[STARTUP] Instrument master loaded")
        else:
            logger.warning("[STARTUP] Skipping instrument master load (STARTUP_LOAD_MASTER=false)")

        # Initialize managers (they auto-initialize on import)
        logger.info("[STARTUP] Initializing subscription managers...")
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.watchlist_manager import WATCHLIST_MGR
        from app.market.ws_manager import WS_MANAGER
        from app.market.atm_engine import ATM_ENGINE
        logger.info("[STARTUP] Subscription managers initialized")

        # Load subscriptions from database (deferred from __init__ to avoid import-time DB queries)
        logger.info("[STARTUP] Loading subscriptions from database...")
        await asyncio.to_thread(SUBSCRIPTION_MGR._load_from_database)
        logger.info("[STARTUP] Subscriptions loaded from database")

        # Optional migration toggle: purge legacy Tier-B EQUITY subscriptions only if explicitly requested.
        purge_tier_b_equity = _env_bool("PURGE_TIER_B_EQUITY_ON_STARTUP", default=False)
        if purge_tier_b_equity:
            eq_removed, eq_failed = await asyncio.to_thread(purge_tier_b_equity_subscriptions)
            logger.warning("[STARTUP] Tier-B EQUITY purge enabled (removed=%s, failed=%s)", eq_removed, eq_failed)
        else:
            logger.info("[STARTUP] Tier-B EQUITY purge skipped (PURGE_TIER_B_EQUITY_ON_STARTUP=false)")

        load_tier_b = _env_bool("STARTUP_LOAD_TIER_B", default=not is_production)
        if load_tier_b:
            logger.info("[STARTUP] Scheduling Tier B pre-load in background...")
            tier_b_task = asyncio.create_task(load_tier_b_chains())
            tier_b_task.add_done_callback(lambda t: _log_task_result(t, "load_tier_b_chains"))
        else:
            logger.warning("[STARTUP] Skipping Tier B preload (STARTUP_LOAD_TIER_B=false)")

        start_streams = _env_bool("STARTUP_START_STREAMS", default=True)
        if start_streams:
            logger.info("[STARTUP] Scheduling market data streams in background...")
            from app.market_orchestrator import get_orchestrator
            streams_task = asyncio.create_task(get_orchestrator().start_streams())
            streams_task.add_done_callback(lambda t: _log_task_result(t, "start_streams"))
        else:
            logger.warning("[STARTUP] Skipping automatic stream start (STARTUP_START_STREAMS=false)")

    loop = asyncio.get_running_loop()

    def _schedule_bootstrap() -> None:
        global _bootstrap_task
        _bootstrap_task = asyncio.create_task(_bootstrap_after_startup())
        _bootstrap_task.add_done_callback(lambda t: _log_task_result(t, "bootstrap_after_startup"))

    loop.call_soon(_schedule_bootstrap)
    logger.info("[STARTUP] Backend ready (bootstrap running in background)")

def on_stop():
    """Application shutdown - cleanup"""
    print("\n[SHUTDOWN] Stopping scheduler...")
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        print("[SHUTDOWN] ✓ Scheduler stopped")
    print("[SHUTDOWN] ✓ Backend shutdown complete\n")
