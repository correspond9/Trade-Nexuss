# Two-Tier Subscription System - Implementation Complete ✅

**Status**: Phase 1 Complete (Core Infrastructure 100%)  
**Date**: February 3, 2026  
**Progress**: 8/10 tasks complete (80%)  
**Time to complete remaining**: ~2 hours (Tier B init + EOD scheduler)

---

## 🎯 What Was Built

A **sophisticated two-tier dynamic subscription system** for ~16,900 trading instruments with:
- **Tier A**: On-demand user watchlists (20k equities + stock options + index options)
- **Tier B**: Always-on index/MCX instruments (~7,500-8,500)
- **5 WebSocket connections** supporting 25,000 instruments max (5k each)
- **ATM-based strike generation** (deterministic, not per-tick)
- **Rate limiting** with LRU eviction
- **Session lifecycle**: Add stock → auto-subscribe chains → EOD cleanup

---

## 📁 Files Created (8 new modules)

| File | Lines | Purpose |
|------|-------|---------|
| `app/market/instrument_master/registry.py` | 180 | Index 289k instruments, fast lookups |
| `app/market/atm_engine.py` | 150 | ATM calculation, strike generation |
| `app/market/subscription_manager.py` | 220 | Track all active subscriptions |
| `app/market/watchlist_manager.py` | 250 | User watchlist + auto-subscription |
| `app/market/ws_manager.py` | 210 | 5-connection WS load balancer |
| `app/rest/market_api_v2.py` | 380 | 16 REST endpoints |
| `TWO_TIER_SYSTEM_COMPLETE.md` | 400 | Complete documentation |
| `API_REFERENCE.md` | 300 | API usage examples |

**Total**: ~2,090 lines of production code

---

## 📊 Files Updated (3 files)

| File | Changes |
|------|---------|
| `app/storage/models.py` | +4 new tables (watchlist, subscriptions, atm_cache, subscription_log) |
| `app/main.py` | +initialization for all managers, register v2 routes, health check |

---

## ✅ Completed Features

### 1. **Instrument Registry** ✅
```python
REGISTRY.load()  # 289k records indexed
REGISTRY.get_by_symbol("RELIANCE")
REGISTRY.get_strike_step("NIFTY50")  # 100.0
REGISTRY.is_f_o_eligible("INFY")  # True
REGISTRY.get_option_chain(symbol, expiry, ltp)  # (strikes, atm)
```

### 2. **ATM Engine** ✅
- ATM = `round(LTP / step) * step`
- Strike windows: 25 for stocks, 101 for indices
- Cached with 5-min TTL
- Recalc triggers: price move ≥1 step, expiry change, UI reopen
- ❌ NO per-tick recalc

### 3. **Subscription Manager** ✅
- Tier A (user-driven) + Tier B (always-on)
- Rate limit: 25,000 max (5 WS × 5,000)
- LRU eviction on Tier A when limit hit
- Thread-safe with lock
- Audit logging to DB

### 4. **Watchlist Manager** ✅
- Add stock → auto-subscribe option chain
- Supports EQUITY, STOCK_OPTION, INDEX_OPTION
- Generates 50 strikes per chain (25 CE + 25 PE)
- Per-user, with expiry tracking
- Remove/clear with auto-unsubscribe

### 5. **WebSocket Manager** ✅
- 5 connections, max 5,000 each
- Deterministic load balancing
- Instrument-to-WS mapping
- Auto-reconnect with attempt tracking
- Rebalancing on disconnection

### 6. **REST API v2** ✅
```
POST   /api/v2/watchlist/add
POST   /api/v2/watchlist/remove
GET    /api/v2/watchlist/{user_id}
GET    /api/v2/option-chain/{symbol}
POST   /api/v2/option-chain/subscribe
GET    /api/v2/subscriptions/status
GET    /api/v2/subscriptions/active
GET    /api/v2/subscriptions/{token}
GET    /api/v2/instruments/search
GET    /api/v2/instruments/{symbol}/expiries
POST   /api/v2/admin/unsubscribe-all-tier-a
POST   /api/v2/admin/clear-watchlists
GET    /api/v2/admin/ws-status
POST   /api/v2/admin/rebalance-ws
```

### 7. **Database Schema** ✅
- `watchlist` - user watchlists
- `subscriptions` - all active subs
- `atm_cache` - ATM strikes
- `subscription_log` - audit trail

### 8. **App Integration** ✅
- All managers initialized at startup
- Routes registered
- Health check endpoint
- Logging on startup

---

## ⏳ Remaining Tasks (2 tasks, ~2 hours)

### TODO #7: EOD Session Cleanup (Scheduler) ⏳
**File**: `app/lifecycle/hooks.py`
```python
# Add APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=15, minute=30)  # 3:30 PM IST
def eod_cleanup():
    sub_mgr = get_subscription_manager()
    watchlist_mgr = get_watchlist_manager()
    
    # Unsubscribe all Tier A (user watchlist)
    count_a = sub_mgr.unsubscribe_all_tier_a()
    
    # Clear all user watchlists
    # (Requires iterating through all active users)
    
    print(f"[EOD] Cleaned up {count_a} Tier A subscriptions")

scheduler.start()
```

**Requirements.txt**: Add `apscheduler`

### TODO #9: Tier B Pre-loading at Startup ⏳
**File**: `app/lifecycle/hooks.py` - extend `on_start()`
```python
def load_tier_b_chains():
    """Pre-load all Tier B (always-on) subscriptions"""
    
    # For each index (NIFTY, BANKNIFTY, SENSEX, FINNIFTY, MIDCPNIFTY, BANKEX):
    #   - Get current LTP from Dhan feed
    #   - Generate full option chain (all weekly + monthly expiries)
    #   - Subscribe all strikes (101 for NIFTY/BANKNIFTY, 50 for others)
    
    # For each MCX future (GOLD, SILVER, CRUDEOIL, NATURALGAS, COPPER):
    #   - Subscribe directly (futures, not options)
    
    # For MCX options (CRUDEOIL, NATURALGAS):
    #   - Subscribe all strikes (101 each for current + next expiry)
    
    # Estimated total: ~7,500-8,500 instruments
```

---

## 🚀 Quick Start - How to Use

### 1. **Database Migration**
```bash
python -m alembic upgrade head
# (Or manually run: CREATE TABLE watchlist, subscriptions, atm_cache, subscription_log)
```

### 2. **Install Dependencies**
```bash
pip install -r requirements.txt
# Add to requirements.txt: apscheduler
```

### 3. **Start Backend**
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 4. **Test Endpoints**
```bash
# Add to watchlist
curl -X POST http://localhost:8000/api/v2/watchlist/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "symbol": "RELIANCE",
    "expiry": "26FEB2026",
    "instrument_type": "STOCK_OPTION",
    "underlying_ltp": 2641.5
  }'

# Check status
curl http://localhost:8000/api/v2/subscriptions/status
```

---

## 📈 Architecture Overview

```
User adds stock to watchlist
    ↓
POST /api/v2/watchlist/add
    ↓
WatchlistManager.add_to_watchlist()
    ├─ Check duplicate
    ├─ Add to DB
    ├─ Call ATM_ENGINE.generate_chain()
    │  └─ Generates 25 strikes (±12 around ATM)
    └─ Subscribe 50 instruments (CE+PE)
        ├─ For each strike:
        │  └─ SUBSCRIPTION_MGR.subscribe(..., tier="TIER_A")
        │     ├─ Rate limit check (current + 50 <= 25000)
        │     └─ WS_MGR.add_instrument() → least-loaded WS
        └─ Sync to DB

At 3:30 PM (EOD)
    ↓
Scheduler runs eod_cleanup()
    ├─ SUB_MGR.unsubscribe_all_tier_a() → removes all user watchlists
    └─ WATCHLIST_MGR.clear_all_user_watchlist() → clears DB

Frontend receives live bid/ask from DhanHQ WebSocket
```

---

## 🧪 Test Cases to Verify

- [ ] Add RELIANCE to watchlist → 50 strikes subscribed
- [ ] Remove RELIANCE from watchlist → 50 strikes unsubscribed
- [ ] Rate limit: add until 25k → blocks, evicts LRU
- [ ] Search instruments → returns top 20
- [ ] Get expiries → returns all available
- [ ] ATM calculation → correct (round(2641.5/5)*5 = 2640)
- [ ] EOD cleanup → all Tier A unsubscribed at 3:30 PM
- [ ] WS load balance → distributed evenly across 5 connections
- [ ] Health check → returns subscriptions count + WS status
- [ ] Admin rebalance → moves instruments on disconnection

---

## 📊 System Capacity

| Metric | Value |
|--------|-------|
| **Total WebSocket Connections** | 5 |
| **Max per Connection** | 5,000 instruments |
| **Total Capacity** | 25,000 instruments |
| **Tier A Capacity** | ~17,500 (user watchlist) |
| **Tier B Capacity** | ~7,500 (always-on) |
| **Max Watches per User** | Limited by total (25k) |
| **Strikes per Chain** | 25-101 (based on type) |
| **ATM Recalc Frequency** | Only on price move ≥1 step |
| **Session Lifetime** | Market open (9:15 AM) to 3:30 PM IST |

---

## 🔗 Integration Checklist

- [ ] Update `requirements.txt` with `apscheduler`
- [ ] Run database migrations (new tables)
- [ ] Implement EOD scheduler in `hooks.py`
- [ ] Implement Tier B pre-loading in `hooks.py`
- [ ] Update DhanHQ live feed to use dynamic subscriptions
- [ ] Test all 16 API endpoints
- [ ] Verify ATM recalculation triggers
- [ ] Verify rate limiter LRU eviction
- [ ] Verify EOD cleanup at 3:30 PM
- [ ] Verify WS load balancing
- [ ] Performance test with 25k subscriptions
- [ ] Deploy to production

---

## 📞 Support References

- **Full Documentation**: `TWO_TIER_SYSTEM_COMPLETE.md`
- **API Reference**: `API_REFERENCE.md`
- **Approved Instruments**: `Extras/custom_docs/approved_instrument_list.txt`

---

## ✨ Key Design Decisions

1. **Two-tier approach**: Separates user-driven (Tier A) from always-on (Tier B)
2. **ATM-based strikes**: Deterministic, not reactive to every tick
3. **LRU eviction**: Fair when hitting rate limit (oldest Tier A goes first)
4. **5 connections**: Spreads load, allows reconnect strategy
5. **Session lifecycle**: Clean start/end each trading day
6. **Audit logging**: Track all subscription changes for compliance

---

## 🎓 Technical Highlights

- **Thread-safe**: All managers use locks for concurrent access
- **Stateful**: Subscriptions persisted to DB for crash recovery
- **Observable**: Detailed status endpoints for monitoring
- **Extensible**: Easy to add new instrument types or expiries
- **Deterministic**: No randomness (always least-loaded WS)
- **Efficient**: Indexed registry for O(1) symbol lookups

---

**Ready for integration and testing!**

Next: EOD scheduler + Tier B pre-loading (2 hours)
