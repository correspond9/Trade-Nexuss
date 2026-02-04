"""
ARCHITECTURE DIAGRAM - Two-Tier Subscription System

Visual overview of the complete system architecture and data flow.
"""

# ============================================================================
# OVERALL SYSTEM ARCHITECTURE
# ============================================================================

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      TWO-TIER SUBSCRIPTION SYSTEM                       │
│                    ~16,900 Instruments, 25k Capacity                    │
└─────────────────────────────────────────────────────────────────────────┘

                        ┌──────────────────────────┐
                        │   DHAN HQ WEBSOCKET      │
                        │   wss://api-feed...      │
                        │   5 concurrent streams   │
                        │   (5,000 each max)       │
                        └──────────┬───────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
                 WS-1           WS-2           WS-3-5
                (5k)           (5k)           (15k)
                 │              │              │
        ┌────────v────────┐  ┌──v──────────┐  └──────┐
        │ WebSocket Mgr   │  │ Subscription│         │
        │ (5 connections, │  │ Manager     │         │
        │  load balancer) │  │ (tracking)  │         │
        └────────┬────────┘  └──┬──────────┘         │
                 │              │                    │
        ┌────────┴──────────────┴────────────────────┘
        │
        ↓
┌───────────────────────────────────────────────────┐
│         SUBSCRIPTION STATE (In-Memory)            │
├───────────────────────────────────────────────────┤
│ Tier B (Always-on, ~7.5k)                        │
│ ├─ NIFTY 50: 8 weekly + 4 quarterly              │
│ ├─ BANKNIFTY: 1 monthly + 4 quarterly            │
│ ├─ SENSEX: 4 weekly + 1 monthly                  │
│ ├─ FINNIFTY: 1 monthly + 3 quarterly             │
│ ├─ MIDCPNIFTY: 1 monthly + 3 quarterly           │
│ ├─ BANKEX: 1 monthly + 3 quarterly               │
│ ├─ MCX Futures: GOLD, SILVER, CRUDEOIL, ...      │
│ └─ MCX Options: CRUDEOIL, NATURALGAS             │
│                                                   │
│ Tier A (On-demand, user watchlist, ~17.5k max)   │
│ ├─ Equity stocks (when user adds to watchlist)   │
│ ├─ Stock options (25 ATM strikes per symbol)     │
│ ├─ Index options (101 ATM strikes per symbol)    │
│ └─ Lifecycle: add → subscribe → EOD → unsubscribe│
└───────────────────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                    MANAGER LAYERS                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ FRONTEND / REST API LAYER                            │       │
│  │ (market_api_v2.py - 16 endpoints)                   │       │
│  │                                                      │       │
│  │ ├─ Watchlist: add, remove, list                     │       │
│  │ ├─ Option chain: generate, subscribe                │       │
│  │ ├─ Status: subscriptions, WS, health               │       │
│  │ ├─ Search: instruments, expiries                    │       │
│  │ └─ Admin: cleanup, rebalance, stats                │       │
│  └──────────────┬───────────────────────────────────────┘       │
│                 │                                                │
│  ┌──────────────v───────────────────────────────────────┐       │
│  │ BUSINESS LOGIC LAYER                                 │       │
│  │                                                      │       │
│  │ WatchlistManager (watchlist_manager.py)             │       │
│  │ ├─ add_to_watchlist() → auto-subscribe chains       │       │
│  │ ├─ remove_from_watchlist() → auto-unsubscribe       │       │
│  │ ├─ get_user_watchlist()                             │       │
│  │ └─ clear_all_user_watchlist() [EOD]                │       │
│  │                                                      │       │
│  │ ATMEngine (atm_engine.py)                           │       │
│  │ ├─ generate_chain() → strikes + CE+PE tokens        │       │
│  │ ├─ should_recalculate() → check triggers             │       │
│  │ └─ cache management with TTL                        │       │
│  │                                                      │       │
│  │ SubscriptionManager (subscription_manager.py)       │       │
│  │ ├─ subscribe() → rate limit check + assign WS       │       │
│  │ ├─ unsubscribe()                                    │       │
│  │ ├─ get_ws_stats()                                   │       │
│  │ └─ unsubscribe_all_tier_a() [EOD]                  │       │
│  │                                                      │       │
│  │ InstrumentRegistry (instrument_master/registry.py)  │       │
│  │ ├─ load() → index 289k records                      │       │
│  │ ├─ get_by_symbol(), get_strike_step()              │       │
│  │ └─ get_option_chain() → strikes from registry       │       │
│  │                                                      │       │
│  │ WebSocketManager (ws_manager.py)                    │       │
│  │ ├─ add_instrument() → least-loaded WS               │       │
│  │ ├─ remove_instrument()                              │       │
│  │ ├─ rebalance() → on disconnection                  │       │
│  │ └─ get_status()                                     │       │
│  └──────────────┬───────────────────────────────────────┘       │
│                 │                                                │
│  ┌──────────────v───────────────────────────────────────┐       │
│  │ DATA LAYER                                            │       │
│  │                                                      │       │
│  │ Database (SQLite)                                    │       │
│  │ ├─ watchlist table                                  │       │
│  │ ├─ subscriptions table                              │       │
│  │ ├─ atm_cache table                                  │       │
│  │ ├─ subscription_log (audit)                         │       │
│  │ └─ + existing tables (users, orders, etc.)          │       │
│  │                                                      │       │
│  │ In-Memory Caches                                     │       │
│  │ ├─ Instrument registry (289k indexed)               │       │
│  │ ├─ ATM cache (with TTL)                             │       │
│  │ ├─ Subscriptions dict (all active)                  │       │
│  │ └─ WS mapping (token → ws_id)                       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘


# ============================================================================
# DATA FLOW: USER ADDS STOCK TO WATCHLIST
# ============================================================================

User (Frontend)
    │
    ├─ Searches "RELIANCE"
    │  └─ GET /api/v2/instruments/search?q=RELIANCE
    │     └─ InstrumentRegistry.by_symbol lookup (O(1))
    │        └─ Returns [RELIANCE + count]
    │
    ├─ Selects RELIANCE
    │  └─ GET /api/v2/instruments/RELIANCE/expiries
    │     └─ Returns ["26FEB2026", "26MAR2026", ...]
    │
    ├─ Selects expiry 26FEB2026, LTP = 2641.5
    │  └─ GET /api/v2/option-chain/RELIANCE?expiry=26FEB2026&ltp=2641.5
    │     └─ ATMEngine.generate_chain()
    │        ├─ ATM = round(2641.5 / 5) * 5 = 2640.0
    │        ├─ Strikes: [2600, 2625, 2640, 2675, 2700, ...]  # 25 total
    │        └─ Returns chain with CE+PE tokens
    │
    ├─ Clicks "Add to Watchlist"
    │  └─ POST /api/v2/watchlist/add
    │     │
    │     └─ WatchlistManager.add_to_watchlist()
    │        │
    │        ├─ Check: not duplicate ✓
    │        ├─ Add to watchlist table ✓
    │        │
    │        ├─ Loop: for each of 25 strikes:
    │        │  │
    │        │  ├─ Create token: "RELIANCE_26FEB_2640CE"
    │        │  │
    │        │  ├─ SubscriptionManager.subscribe()
    │        │  │  │
    │        │  │  ├─ Check rate limit: 8500 + 50 <= 25000? ✓
    │        │  │  ├─ Find least-loaded WS: ws_2
    │        │  │  ├─ WebSocketManager.add_instrument()
    │        │  │  │  └─ Update ws_usage[2] += 1
    │        │  │  │  └─ Add to subscriptions dict
    │        │  │  └─ Add to tier_a_lru for LRU eviction
    │        │  │
    │        │  └─ (same for PE)
    │        │
    │        └─ Return: 50 strikes subscribed ✓
    │
    └─ Frontend: renders option chain UI
       ├─ Shows 25 strikes with CE + PE
       ├─ Displays bid/ask from Dhan WebSocket
       └─ User can now place orders


# ============================================================================
# ATM RECALCULATION LOGIC
# ============================================================================

Scenario: RELIANCE price moves from 2641.5 to 2650.0

┌─ DhanHQ WebSocket broadcasts: RELIANCE LTP = 2650.0
├─ Frontend polls GET /api/v2/option-chain/RELIANCE?expiry=26FEB2026&ltp=2650.0
├─ ATMEngine.should_recalculate()?
│  ├─ Price moved: |2650 - 2641.5| = 8.5 >= 5.0 (strike step)? ✓ YES
│  └─ Return: True (recalculate)
├─ ATMEngine.generate_chain()
│  ├─ New ATM = round(2650 / 5) * 5 = 2650.0
│  ├─ New strikes: [2610, 2625, 2650, 2675, 2690, ...]
│  └─ Cache invalidated, fresh chain returned
└─ Frontend: updates option chain UI with new strikes


# ============================================================================
# RATE LIMIT SCENARIO
# ============================================================================

Current: 8500 Tier B + 16000 Tier A = 24500 subscriptions
User tries to add new stock option chain (50 more)

┌─ POST /api/v2/watchlist/add
├─ SubscriptionManager.subscribe() for 1st strike
│  ├─ Check: 24500 + 50 > 25000? ✓ YES → OVER LIMIT
│  ├─ Tier A? ✓ YES → Try LRU eviction
│  ├─ Evict oldest Tier A chain (e.g., INFY, 50 strikes)
│  │  └─ unsubscribe_all for INFY_* tokens
│  │  └─ Now: 24500 - 50 = 24450
│  ├─ Check again: 24450 + 50 <= 25000? ✓ YES
│  ├─ Add new RELIANCE strikes
│  └─ Now: 24500
├─ Result: INFY removed, RELIANCE added
└─ User notification: "Added RELIANCE, removed INFY (capacity limit)"


# ============================================================================
# EOD SESSION CLEANUP (3:30 PM)
# ============================================================================

APScheduler fires at 3:30 PM IST

┌─ eod_cleanup()
│  │
│  ├─ SubscriptionManager.unsubscribe_all_tier_a()
│  │  ├─ For each Tier A subscription:
│  │  │  └─ Call unsubscribe()
│  │  │     ├─ Remove from subscriptions dict
│  │  │     ├─ Update ws_usage (decrement)
│  │  │     └─ Log to DB (action=EOD_CLEANUP)
│  │  └─ Result: All user watchlists gone
│  │
│  ├─ WatchlistManager.clear_all_user_watchlist()
│  │  ├─ Delete all watchlist table entries
│  │  └─ Clear cache
│  │
│  ├─ Result:
│  │  ├─ Tier A: 0 subscriptions
│  │  ├─ Tier B: ~8500 (always-on, persistent)
│  │  └─ Capacity: ready for next day
│  │
│  └─ Log: "[EOD] Cleaned up 16500 Tier A, ready for next session"
│
└─ Next day (9:15 AM): Market opens
   ├─ Tier B already subscribed (persistent)
   ├─ Users add stocks via watchlist
   ├─ Tier A grows from 0 to 17500 max
   └─ Cycle repeats


# ============================================================================
# WEBSOCKET LOAD DISTRIBUTION
# ============================================================================

Initial state (empty):

  WS-1      WS-2      WS-3      WS-4      WS-5
  [0]       [0]       [0]       [0]       [0]
  Total: 0


Tier B loaded (~8500):

  WS-1      WS-2      WS-3      WS-4      WS-5
  [2000]    [2000]    [2000]    [1500]    [1000]
  Total: 8500


Tier A grows (users add watchlist):

  1. RELIANCE_50   → WS-4 (least loaded): [1500] → [1550]
  2. INFY_50       → WS-5 (least loaded): [1000] → [1050]
  3. TCS_50        → WS-4 (least loaded): [1550] → [1600]
  4. WIPRO_50      → WS-5 (least loaded): [1050] → [1100]
  ...
  
Eventually:

  WS-1      WS-2      WS-3      WS-4      WS-5
  [5000]    [5000]    [5000]    [5000]    [5000]
  Total: 25000 (at capacity)


# ============================================================================
# KEY PERFORMANCE CHARACTERISTICS
# ============================================================================

Operation             Time Complexity    Space
─────────────────────────────────────────────────
Symbol lookup         O(1) hashtable     289k refs
Add to watchlist      O(1) + network     DB insert
Remove from watchlist O(1) + network     DB delete
Generate chain        O(n) n=25/101      Cache
Subscribe (single)    O(1)               In-memory
Unsubscribe (single)  O(1)               In-memory
Rate limit check      O(1)               WS stats dict
LRU eviction          O(1) pop           tier_a_lru list
Find least-loaded WS  O(5) = O(1)        5 connections
Rebalance WS          O(moved_count)     Reconnect


# ============================================================================
# FAILURE SCENARIOS & RECOVERY
# ============================================================================

Scenario 1: WS-2 disconnects
├─ detect_disconnection()
├─ mark WS-2 inactive
├─ ws_manager.rebalance()
│  └─ Move all WS-2 instruments to least-loaded active WS
├─ auto_reconnect() after 5 seconds
└─ Resume streaming

Scenario 2: Rate limit hit, LRU eviction needed
├─ Check: current + new > 25000? YES
├─ Find oldest Tier A subscription
├─ Unsubscribe entire chain (50 strikes)
├─ Add new chain
└─ Log: "INFY evicted due to rate limit, RELIANCE added"

Scenario 3: Backend restart
├─ Load from DB: subscriptions table
├─ Reload: in-memory state
├─ Reconnect to DhanHQ
├─ Resume with previous state
└─ No data loss (state persisted)

Scenario 4: User removes watchlist entry
├─ find_related_chains()
├─ Unsubscribe all 50 strikes
├─ Delete from watchlist table
├─ Update UI
└─ Tier A count decreases


```

---

This architecture ensures:
✅ Scalability (25k instruments across 5 WS)
✅ Fairness (LRU eviction, least-loaded balancing)
✅ Reliability (DB persistence, auto-reconnect)
✅ Responsiveness (O(1) ops, cached registry)
✅ Auditability (subscription_log for compliance)
"""
