# INTEGRATION CHECKLIST - Two-Tier Subscription System

**System**: Broking Terminal V2 - Market Data Subscriptions  
**Status**: Phase 1 Complete, Ready for Integration  
**Date**: February 3, 2026

---

## ✅ PHASE 1: CORE INFRASTRUCTURE (COMPLETE)

### Modules Created
- [x] `app/market/instrument_master/registry.py` - 289k instrument index
- [x] `app/market/atm_engine.py` - ATM calculation & strike generation
- [x] `app/market/subscription_manager.py` - Subscription state tracking
- [x] `app/market/watchlist_manager.py` - User watchlist management
- [x] `app/market/ws_manager.py` - WebSocket load balancing
- [x] `app/rest/market_api_v2.py` - 16 REST API endpoints

### Database Schema
- [x] `watchlist` table - user watchlists
- [x] `subscriptions` table - active subscriptions
- [x] `atm_cache` table - strike metadata
- [x] `subscription_log` table - audit trail

### Application Updates
- [x] `app/storage/models.py` - +4 tables
- [x] `app/main.py` - Manager initialization + route registration

### Documentation
- [x] `TWO_TIER_SYSTEM_COMPLETE.md` - Full technical docs
- [x] `API_REFERENCE.md` - All 16 endpoints with examples
- [x] `IMPLEMENTATION_SUMMARY.md` - Implementation guide
- [x] `ARCHITECTURE_DIAGRAM.md` - System architecture
- [x] `README_TWO_TIER_SYSTEM.md` - Executive summary

---

## ⏳ PHASE 2: INTEGRATION (IN PROGRESS)

### Dependencies
- [ ] Install APScheduler: `pip install apscheduler`
- [ ] Update `requirements.txt` with `apscheduler`
- [ ] Verify all imports in new modules
- [ ] Test imports: `python -c "from app.market.registry import REGISTRY"`

### Database Migration
- [ ] Run Alembic or manual SQL to create 4 new tables
- [ ] Verify tables created: `sqlite3 app.db ".tables"`
- [ ] Verify columns: `sqlite3 app.db ".schema watchlist"`

### Application Startup
- [ ] Test app startup: `uvicorn app.main:app --reload`
- [ ] Verify no import errors
- [ ] Check startup logs for "Backend ready!"
- [ ] Verify health check: `curl http://localhost:8000/health`

### REST API Verification
- [ ] Test instrument search: `GET /api/v2/instruments/search?q=REL`
- [ ] Test expiries: `GET /api/v2/instruments/RELIANCE/expiries`
- [ ] Test option chain: `GET /api/v2/option-chain/RELIANCE?expiry=26FEB2026&underlying_ltp=2641.5`
- [ ] Test subscription status: `GET /api/v2/subscriptions/status`
- [ ] Test watchlist add: `POST /api/v2/watchlist/add`
- [ ] Test health: `GET /health`

---

## ⏳ PHASE 3: EOD SCHEDULER (TODO)

### File: `app/lifecycle/hooks.py`

**Task**: Add APScheduler for 3:30 PM cleanup

```python
from apscheduler.schedulers.background import BackgroundScheduler
from app.market.subscription_manager import get_subscription_manager
from app.market.watchlist_manager import get_watchlist_manager

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=15, minute=30)  # 3:30 PM IST
def eod_cleanup():
    """Cleanup at end of trading day"""
    print("[EOD] Starting cleanup...")
    
    sub_mgr = get_subscription_manager()
    watchlist_mgr = get_watchlist_manager()
    
    # Unsubscribe all Tier A
    tier_a_count = sub_mgr.unsubscribe_all_tier_a()
    print(f"[EOD] Unsubscribed {tier_a_count} Tier A instruments")
    
    # TODO: Clear all user watchlists (need to get all users)
    # For now, admins can call: POST /api/v2/admin/clear-watchlists
    
    print("[EOD] Cleanup complete, ready for next session")

def on_start():
    # ... existing code ...
    
    # Start EOD scheduler
    scheduler.start()
    print("[OK] EOD scheduler started (3:30 PM IST)")

def on_stop():
    # ... existing code ...
    scheduler.shutdown()
```

**Checklist**:
- [ ] Import APScheduler
- [ ] Add `eod_cleanup()` function
- [ ] Register scheduler in `on_start()`
- [ ] Test: manually call function at 3:30 PM
- [ ] Verify: all Tier A unsubscribed
- [ ] Log: capture cleanup events

---

## ⏳ PHASE 4: TIER B PRE-LOADING (TODO)

### File: `app/lifecycle/hooks.py`

**Task**: Pre-load all always-on index/MCX instruments

```python
def load_tier_b_chains():
    """Pre-load Tier B (always-on) subscriptions at startup"""
    from app.market.subscription_manager import get_subscription_manager
    from app.market.atm_engine import get_atm_engine
    from app.market.live_prices import get_prices
    
    sub_mgr = get_subscription_manager()
    atm_engine = get_atm_engine()
    
    print("[STARTUP] Loading Tier B (always-on) chains...")
    
    # Index options
    indices = [
        ("NIFTY50", ["26FEB2026", "26MAR2026", ...]),  # 8 weekly + 4 quarterly
        ("BANKNIFTY", [...]),
        ("SENSEX", [...]),
        ("FINNIFTY", [...]),
        ("MIDCPNIFTY", [...]),
        ("BANKEX", [...])
    ]
    
    for symbol, expiries in indices:
        # Get current LTP (from Dhan feed after it connects)
        prices = get_prices()
        ltp = prices.get(symbol, 0)
        
        if ltp <= 0:
            print(f"[WARN] No LTP for {symbol}, skipping")
            continue
        
        # For each expiry: generate chain, subscribe all strikes
        for expiry in expiries:
            chain = atm_engine.generate_chain(symbol, expiry, ltp)
            strikes = chain.get("strikes", [])
            
            for strike in strikes:
                # CE
                token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                success, msg, ws_id = sub_mgr.subscribe(
                    token=token_ce,
                    symbol=symbol,
                    expiry=expiry,
                    strike=strike,
                    option_type="CE",
                    tier="TIER_B"
                )
                
                # PE
                token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                success, msg, ws_id = sub_mgr.subscribe(
                    token=token_pe,
                    symbol=symbol,
                    expiry=expiry,
                    strike=strike,
                    option_type="PE",
                    tier="TIER_B"
                )
        
        print(f"[OK] Loaded {symbol} chains")
    
    # MCX Futures
    mcx_futures = ["GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER"]
    for symbol in mcx_futures:
        # Direct subscribe (futures, not options)
        token = f"{symbol}_FUT"
        success, msg, ws_id = sub_mgr.subscribe(
            token=token,
            symbol=symbol,
            expiry=None,
            strike=None,
            option_type=None,
            tier="TIER_B"
        )
        print(f"[OK] Loaded {symbol} futures")
    
    # MCX Options (CRUDEOIL, NATURALGAS)
    for symbol in ["CRUDEOIL", "NATURALGAS"]:
        ltp = prices.get(symbol, 0)
        if ltp <= 0:
            continue
        
        for expiry in ["26FEB2026", "26MAR2026"]:  # Nearest 2
            chain = atm_engine.generate_chain(symbol, expiry, ltp)
            strikes = chain.get("strikes", [])
            
            for strike in strikes:
                token_ce = f"{symbol}_{expiry}_{strike:.0f}CE"
                token_pe = f"{symbol}_{expiry}_{strike:.0f}PE"
                
                sub_mgr.subscribe(token_ce, symbol, expiry, strike, "CE", "TIER_B")
                sub_mgr.subscribe(token_pe, symbol, expiry, strike, "PE", "TIER_B")
    
    stats = sub_mgr.get_ws_stats()
    print(f"[OK] Tier B loaded: {stats['tier_b_count']} instruments")

def on_start():
    # ... existing code ...
    
    # Load instrument registry
    load_instruments()
    
    # Load Tier B after market feed starts
    # (need LTP for ATM calculation)
    time.sleep(2)  # Wait for Dhan feed to start
    load_tier_b_chains()
```

**Checklist**:
- [ ] Get current LTP from Dhan feed
- [ ] Generate index option chains
- [ ] Subscribe all strikes (CE+PE)
- [ ] Subscribe MCX futures
- [ ] Subscribe MCX options
- [ ] Verify: ~8,500 total Tier B
- [ ] Test: check subscriptions status

---

## ⏳ PHASE 5: DHAN FEED INTEGRATION (TODO)

### File: `app/dhan/live_feed.py`

**Task**: Make instrument subscriptions dynamic

**Current**: Hardcoded 3 instruments (NIFTY, SENSEX, CRUDEOIL)

**Next**: Fetch instruments from SubscriptionManager

```python
def run_feed():
    while True:
        try:
            sub_mgr = get_subscription_manager()
            
            # Get current subscriptions
            active_subs = sub_mgr.list_active_subscriptions()
            
            # Extract unique (segment, token) pairs
            instruments = set()
            for sub in active_subs:
                # Parse from subscription to (segment, security_id, type)
                # segment = 0 (IDX) or 5 (MCX)
                # security_id = from registry lookup
                pass
            
            # Subscribe to all instruments
            # Handle dynamic add/remove on subscription changes
            
except Exception as e:
    print(f"[ERROR] Feed error: {e}")
    time.sleep(5)
```

**Checklist**:
- [ ] Read subscriptions dynamically
- [ ] Map subscriptions to (segment, token)
- [ ] Subscribe via DhanHQ API
- [ ] Handle add/remove on changes
- [ ] Test with 100, 1000, 10000 subscriptions
- [ ] Verify prices flowing to frontend

---

## 🧪 TESTING CHECKLIST

### Unit Tests
- [ ] InstrumentRegistry: load, lookup, strike step
- [ ] ATMEngine: calculate ATM, should_recalculate, generate_chain
- [ ] SubscriptionManager: subscribe, unsubscribe, rate limit
- [ ] WatchlistManager: add, remove, list
- [ ] WebSocketManager: add_instrument, rebalance

### Integration Tests
- [ ] Add stock to watchlist → 50 strikes subscribed
- [ ] Remove stock → 50 strikes unsubscribed
- [ ] Rate limit: add until 25k → blocks, evicts LRU
- [ ] EOD cleanup: all Tier A unsubscribed at 3:30 PM
- [ ] WS load balance: distributed evenly

### API Tests
- [ ] POST /api/v2/watchlist/add (success + error cases)
- [ ] GET /api/v2/option-chain/{symbol} (all symbols)
- [ ] GET /api/v2/subscriptions/status (format, data)
- [ ] GET /api/v2/instruments/search (accuracy)
- [ ] All 16 endpoints respond correctly

### Performance Tests
- [ ] Load 25k subscriptions → memory usage
- [ ] Query subscriptions → response time
- [ ] Add watchlist → end-to-end latency
- [ ] WS rebalance → no packet loss

### End-to-End Tests
- [ ] User flow: search → select → add → see chain → EOD cleanup
- [ ] DhanHQ connection: prices flow, ticks update
- [ ] Session lifecycle: start → trade → end
- [ ] Multiple users: separate watchlists

---

## 📋 DEPLOYMENT CHECKLIST

### Pre-deployment
- [ ] All code reviewed
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Performance baselines set
- [ ] Security audit done

### Deployment
- [ ] Backup database
- [ ] Run migrations
- [ ] Install APScheduler
- [ ] Update requirements.txt
- [ ] Deploy code
- [ ] Verify startup
- [ ] Test critical paths

### Post-deployment
- [ ] Monitor logs for errors
- [ ] Check subscription counts
- [ ] Verify EOD cleanup runs
- [ ] Verify Tier B loads
- [ ] User acceptance testing
- [ ] Performance monitoring

---

## 🎯 SUCCESS CRITERIA

- [ ] System starts without errors
- [ ] All 16 API endpoints work
- [ ] Watchlist add/remove functional
- [ ] Rate limiter working (LRU eviction)
- [ ] EOD cleanup runs at 3:30 PM
- [ ] Tier B (8.5k) loaded at startup
- [ ] WS distributed evenly (all 5 used)
- [ ] Prices flowing from Dhan to frontend
- [ ] No memory leaks (monitor for 24 hours)
- [ ] Documentation complete & accurate

---

## 📞 SUPPORT CONTACTS

**For questions on**:
- **Architecture**: See `ARCHITECTURE_DIAGRAM.md`
- **API usage**: See `API_REFERENCE.md`
- **Implementation**: See `TWO_TIER_SYSTEM_COMPLETE.md`
- **Quick start**: See `README_TWO_TIER_SYSTEM.md`

---

**Status**: Ready for Phase 2 integration  
**Next step**: Run database migrations and test API endpoints  
**Estimated time to full deployment**: 4 hours (with testing)
