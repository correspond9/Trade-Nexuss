import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from app.market.instrument_master.loader import MASTER
from app.dhan.live_feed import start_live_feed

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler = None

def get_scheduler():
    """Get or create the background scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler

def eod_cleanup():
    """
    End-of-Day (3:30 PM IST) cleanup task
    - Unsubscribe all Tier A (user watchlist) subscriptions
    - Preserve Tier B (always-on) subscriptions
    - Reset system for next trading session
    """
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.storage.db import SessionLocal
        
        print("\n" + "="*70)
        print("[EOD] Starting End-of-Day cleanup (3:30 PM IST)")
        print("="*70)
        
        # Get subscription stats before cleanup
        stats_before = SUBSCRIPTION_MGR.get_ws_stats()
        print(f"[EOD] Before cleanup:")
        print(f"  • Total subscriptions: {stats_before['total_subscriptions']}")
        print(f"  • Tier A (user watchlists): {stats_before['tier_a_count']}")
        print(f"  • Tier B (always-on): {stats_before['tier_b_count']}")
        
        # Unsubscribe all Tier A subscriptions
        tier_a_unsubscribed = SUBSCRIPTION_MGR.unsubscribe_all_tier_a()
        print(f"\n[EOD] Unsubscribed {tier_a_unsubscribed} Tier A instruments")
        
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
                reason=f"End-of-day cleanup: unsubscribed {tier_a_unsubscribed} instruments"
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


def load_tier_b_chains():
    """
    PHASE 3: Pre-load ~2,272 Tier B subscriptions at startup
    
    Tier B includes:
    - Index options (NIFTY50, BANKNIFTY, SENSEX, FINNIFTY, MIDCPNIFTY, BANKEX)
    - MCX futures and options (CRUDEOIL, NATURALGAS)
    
    Total: ~2,272 subscriptions (9.1% of 25,000 limit)
    """
    try:
        from app.market.subscription_manager import SUBSCRIPTION_MGR
        from app.market.atm_engine import ATM_ENGINE
        from app.market.live_prices import get_prices
        from app.market.instrument_master.registry import REGISTRY

        print("\n" + "="*70)
        print("[STARTUP-PHASE3] Loading Full Tier B Subscriptions (2,272 instruments)")
        print("="*70)

        def _select_expiries(symbol: str, count: int) -> list:
            expiries = REGISTRY.get_expiries_for_underlying(symbol) or REGISTRY.get_expiries_for_symbol(symbol)
            return expiries[:count]

        # Define Tier B instruments with dynamic expiries from instrument master
        tier_b_instruments = [
            ("NIFTY", _select_expiries("NIFTY", 16)),
            ("BANKNIFTY", _select_expiries("BANKNIFTY", 7)),
            ("SENSEX", _select_expiries("SENSEX", 7)),
            ("FINNIFTY", _select_expiries("FINNIFTY", 7)),
            ("MIDCPNIFTY", _select_expiries("MIDCPNIFTY", 7)),
            ("BANKEX", _select_expiries("BANKEX", 7)),
        ]
        
        mcx_instruments = [
            ("CRUDEOIL", _select_expiries("CRUDEOIL", 4)),
            ("NATURALGAS", _select_expiries("NATURALGAS", 4)),
        ]

        all_prices = get_prices()
        total_subscribed = 0
        total_failed = 0

        # Subscribe to index options
        print("\n[INDEX OPTIONS] Subscribing to full option chains...")
        for symbol, expiries in tier_b_instruments:
            underlying_ltp = all_prices.get(symbol) or 25000  # Fallback if price not available yet
            print(f"  {symbol}: {len(expiries)} expiries, LTP={underlying_ltp}")
            
            for expiry in expiries:
                option_chain = ATM_ENGINE.generate_chain(symbol, expiry, underlying_ltp)
                strikes = option_chain["strikes"]
                
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

        print(f"  ✓ Index options subscribed: {total_subscribed}")

        # Subscribe to MCX contracts
        print("\n[MCX CONTRACTS] Subscribing to futures and options...")
        mcx_subscribed = 0
        for symbol, expiries in mcx_instruments:
            underlying_ltp = all_prices.get(symbol) or 5500  # Fallback if price not available yet
            print(f"  {symbol}: {len(expiries)} expiries, LTP={underlying_ltp}")
            
            for expiry in expiries:
                # Subscribe to futures
                token_fut = f"{symbol}_{expiry}_FUT"
                success, msg, ws_id = SUBSCRIPTION_MGR.subscribe(
                    token=token_fut,
                    symbol=symbol,
                    expiry=expiry,
                    strike=None,
                    option_type=None,
                    tier="TIER_B"
                )
                if success:
                    total_subscribed += 1
                    mcx_subscribed += 1
                else:
                    total_failed += 1
                
                # Subscribe to ATM ±2 options
                option_chain = ATM_ENGINE.generate_chain(symbol, expiry, underlying_ltp)
                strikes = option_chain["strikes"]
                atm_idx = len(strikes) // 2
                selected_strikes = strikes[max(0, atm_idx-2):min(len(strikes), atm_idx+3)]
                
                for strike in selected_strikes:
                    for option_type in ["CE", "PE"]:
                        token_opt = f"{symbol}_{expiry}_{strike}{option_type}"
                        success, msg, ws_id = SUBSCRIPTION_MGR.subscribe(
                            token=token_opt,
                            symbol=symbol,
                            expiry=expiry,
                            strike=float(strike),
                            option_type=option_type,
                            tier="TIER_B"
                        )
                        if success:
                            total_subscribed += 1
                            mcx_subscribed += 1
                        else:
                            total_failed += 1

        print(f"  ✓ MCX contracts subscribed: {mcx_subscribed}")

        # Print summary
        stats = SUBSCRIPTION_MGR.get_ws_stats()
        print("\n" + "="*70)
        print("[STARTUP-PHASE3] Tier B Pre-loading Complete")
        print("="*70)
        print(f"✓ Tier B subscriptions: {stats['tier_b_count']:,}")
        print(f"✓ Total subscriptions: {stats['total_subscriptions']:,}")
        print(f"✓ System utilization: {stats['utilization_percent']:.1f}%")
        print(f"✓ Subscribed: {total_subscribed:,} | Failed: {total_failed:,}")
        
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

def on_start():
    """Application startup - initialize managers and scheduler"""
    print("\n" + "="*70)
    print("[STARTUP] Initializing Broking Terminal V2 Backend")
    print("="*70)
    
    # Load instrument master
    print("[STARTUP] Loading instrument master...")
    MASTER.load()
    print("[STARTUP] ✓ Instrument master loaded")
    
    # Initialize managers (they auto-initialize on import)
    print("[STARTUP] Initializing subscription managers...")
    from app.market.subscription_manager import SUBSCRIPTION_MGR
    from app.market.watchlist_manager import WATCHLIST_MGR
    from app.market.ws_manager import WS_MANAGER
    from app.market.atm_engine import ATM_ENGINE
    print("[STARTUP] ✓ Subscription managers initialized")
    
    # Start EOD scheduler
    print("[STARTUP] Starting EOD scheduler...")
    scheduler = get_scheduler()
    
    # Schedule EOD cleanup for 3:30 PM IST every trading day
    scheduler.add_job(
        eod_cleanup,
        'cron',
        hour=15,           # 3:30 PM IST (15:30 in 24-hour format)
        minute=30,
        id='eod_cleanup',
        name='End-of-Day Cleanup',
        replace_existing=True,
        max_instances=1    # Ensure only one instance runs at a time
    )
    
    scheduler.start()
    print("[STARTUP] ✓ EOD scheduler started (fires at 3:30 PM IST)")
    print("[STARTUP] ✓ Manual trigger: POST /api/v2/admin/unsubscribe-all-tier-a")
    
    # Load Tier B chains (Phase 3) before starting the feed so default
    # subscriptions already exist when we compute initial targets.
    print("[STARTUP] Loading Tier B pre-loaded chains...")
    load_tier_b_chains()
    
    # Start official Dhan WebSocket feed after Tier B is registered
    print("[STARTUP] Starting Dhan WebSocket feed...")
    start_live_feed()
    print("[STARTUP] ✓ Dhan WebSocket feed started")

    print("[STARTUP] ✓ Backend ready!")
    print("="*70 + "\n")

def on_stop():
    """Application shutdown - cleanup"""
    print("\n[SHUTDOWN] Stopping scheduler...")
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        print("[SHUTDOWN] ✓ Scheduler stopped")
    print("[SHUTDOWN] ✓ Backend shutdown complete\n")
