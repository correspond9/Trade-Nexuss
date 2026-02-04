"""
QUICK API REFERENCE - Two-Tier Subscription System

Examples of how to use the new endpoints from frontend or tests.
"""

# ============================================================================
# WATCHLIST ENDPOINTS - USER ACTIONS
# ============================================================================

# 1. ADD STOCK OPTION TO WATCHLIST
POST /api/v2/watchlist/add
Content-Type: application/json

{
  "user_id": 1,
  "symbol": "RELIANCE",
  "expiry": "26FEB2026",
  "instrument_type": "STOCK_OPTION",
  "underlying_ltp": 2641.5
}

RESPONSE (200):
{
  "success": true,
  "message": "Added RELIANCE to watchlist (26FEB2026)",
  "option_chain": {
    "symbol": "RELIANCE",
    "expiry": "26FEB2026",
    "underlying_ltp": 2641.5,
    "atm_strike": 2640.0,
    "strike_step": 5.0,
    "strikes": [2600, 2625, 2640, 2675, 2700, ...],  # 25 total
    "strikes_ce_pe": {
      "2600": {"CE": "RELIANCE_26FEB_2600CE", "PE": "RELIANCE_26FEB_2600PE"},
      "2625": {"CE": "RELIANCE_26FEB_2625CE", "PE": "RELIANCE_26FEB_2625PE"},
      ...
    },
    "cached_at": "2026-02-03T10:15:30.123456",
    "cache_ttl_seconds": 300
  },
  "strikes_subscribed": 50  # 25 strikes × 2 (CE+PE)
}


# 2. REMOVE FROM WATCHLIST
POST /api/v2/watchlist/remove
Content-Type: application/json

{
  "user_id": 1,
  "symbol": "RELIANCE",
  "expiry": "26FEB2026"
}

RESPONSE (200):
{
  "success": true,
  "message": "Removed RELIANCE from watchlist"
}


# 3. GET USER WATCHLIST
GET /api/v2/watchlist/1

RESPONSE (200):
{
  "user_id": 1,
  "count": 3,
  "watchlist": [
    {
      "id": 1,
      "symbol": "RELIANCE",
      "expiry_date": "26FEB2026",
      "instrument_type": "STOCK_OPTION",
      "added_at": "2026-02-03T10:15:30.123456",
      "added_order": 1
    },
    {
      "id": 2,
      "symbol": "INFY",
      "expiry_date": "26FEB2026",
      "instrument_type": "STOCK_OPTION",
      "added_at": "2026-02-03T10:30:45.123456",
      "added_order": 2
    },
    ...
  ]
}


# ============================================================================
# OPTION CHAIN ENDPOINTS
# ============================================================================

# 4. GET OPTION CHAIN (WITHOUT SUBSCRIBING)
GET /api/v2/option-chain/RELIANCE?expiry=26FEB2026&underlying_ltp=2641.5

RESPONSE (200):
{
  "symbol": "RELIANCE",
  "expiry": "26FEB2026",
  "underlying_ltp": 2641.5,
  "atm_strike": 2640.0,
  "strike_step": 5.0,
  "strikes": [2600, 2625, 2640, 2675, 2700, ...],
  "strikes_ce_pe": {
    "2600": {"CE": "RELIANCE_26FEB_2600CE", "PE": "RELIANCE_26FEB_2600PE"},
    ...
  },
  "cached_at": "2026-02-03T10:15:30.123456",
  "cache_ttl_seconds": 300
}


# 5. EXPLICITLY SUBSCRIBE OPTION CHAIN
POST /api/v2/option-chain/subscribe
Content-Type: application/json

{
  "symbol": "INFY",
  "expiry": "26FEB2026",
  "underlying_ltp": 450.25
}

RESPONSE (200):
{
  "symbol": "INFY",
  "expiry": "26FEB2026",
  "option_chain": { ... },
  "subscribed": [
    "INFY_26FEB_440CE",
    "INFY_26FEB_440PE",
    "INFY_26FEB_445CE",
    "INFY_26FEB_445PE",
    ...  # 50 total
  ],
  "failed": [],
  "total_subscribed": 50
}


# ============================================================================
# SUBSCRIPTION STATUS ENDPOINTS
# ============================================================================

# 6. GET OVERALL SUBSCRIPTION STATUS
GET /api/v2/subscriptions/status

RESPONSE (200):
{
  "subscriptions": {
    "total_subscriptions": 12500,
    "max_capacity": 25000,
    "utilization_percent": 50.0,
    "tier_a_count": 2500,    # User watchlist
    "tier_b_count": 10000    # Always-on (index/MCX)
  },
  "websocket": {
    "total_subscriptions": 12500,
    "max_capacity": 25000,
    "utilization_percent": 50.0,
    "connected_connections": 5,
    "total_connections": 5,
    "per_connection": {
      "ws_1": {
        "active": true,
        "instruments": 5000,
        "utilization_percent": 100.0,
        "last_connected": 1707000000.123,
        "reconnect_attempts": 0,
        "last_error": null
      },
      "ws_2": {
        "active": true,
        "instruments": 5000,
        "utilization_percent": 100.0,
        ...
      },
      ...
    }
  }
}


# 7. LIST ACTIVE SUBSCRIPTIONS (ALL)
GET /api/v2/subscriptions/active

RESPONSE (200):
{
  "tier": null,
  "count": 12500,
  "subscriptions": [
    {
      "token": "RELIANCE_26FEB_2640CE",
      "symbol": "RELIANCE",
      "expiry": "26FEB2026",
      "strike": 2640.0,
      "option_type": "CE",
      "tier": "TIER_A",
      "subscribed_at": "2026-02-03T10:15:30.123456",
      "ws_id": 2,
      "active": true
    },
    ...
  ]
}


# 8. LIST ACTIVE SUBSCRIPTIONS (TIER A ONLY)
GET /api/v2/subscriptions/active?tier=TIER_A

RESPONSE (200):
{
  "tier": "TIER_A",
  "count": 2500,
  "subscriptions": [ ... ]  # Only user watchlist items
}


# 9. LIST ACTIVE SUBSCRIPTIONS (TIER B ONLY)
GET /api/v2/subscriptions/active?tier=TIER_B

RESPONSE (200):
{
  "tier": "TIER_B",
  "count": 10000,
  "subscriptions": [ ... ]  # Only always-on index/MCX
}


# 10. GET SPECIFIC SUBSCRIPTION DETAILS
GET /api/v2/subscriptions/RELIANCE_26FEB_2640CE

RESPONSE (200):
{
  "token": "RELIANCE_26FEB_2640CE",
  "details": {
    "symbol": "RELIANCE",
    "expiry": "26FEB2026",
    "strike": 2640.0,
    "option_type": "CE",
    "tier": "TIER_A",
    "subscribed_at": "2026-02-03T10:15:30.123456",
    "ws_id": 2,
    "active": true
  }
}


# ============================================================================
# INSTRUMENT SEARCH ENDPOINTS
# ============================================================================

# 11. SEARCH INSTRUMENTS (FOR WATCHLIST UI)
GET /api/v2/instruments/search?q=REL&limit=10

RESPONSE (200):
{
  "query": "REL",
  "count": 3,
  "results": [
    {
      "symbol": "RELIANCE",
      "count": 1234,  # Total records (all expiries/strikes)
      "f_o_eligible": true
    },
    {
      "symbol": "RELIANCEPOWER",
      "count": 856,
      "f_o_eligible": false
    },
    ...
  ]
}


# 12. GET AVAILABLE EXPIRIES FOR A SYMBOL
GET /api/v2/instruments/RELIANCE/expiries

RESPONSE (200):
{
  "symbol": "RELIANCE",
  "expiries": [
    "26FEB2026",
    "26MAR2026",
    "23APR2026",
    "28MAY2026"
  ],
  "count": 4
}


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

# 13. UNSUBSCRIBE ALL TIER A (EOD CLEANUP)
POST /api/v2/admin/unsubscribe-all-tier-a

RESPONSE (200):
{
  "action": "UNSUBSCRIBE_ALL_TIER_A",
  "count": 2500,
  "message": "Unsubscribed 2500 Tier A instruments"
}


# 14. CLEAR USER WATCHLIST
POST /api/v2/admin/clear-watchlists?user_id=1

RESPONSE (200):
{
  "action": "CLEAR_WATCHLIST",
  "user_id": 1,
  "success": true,
  "cleared_count": 3
}


# 15. GET DETAILED WEBSOCKET STATUS
GET /api/v2/admin/ws-status

RESPONSE (200):
{
  "total_subscriptions": 12500,
  "max_capacity": 25000,
  "utilization_percent": 50.0,
  "connected_connections": 5,
  "total_connections": 5,
  "per_connection": { ... }  # Same as #6
}


# 16. REBALANCE WEBSOCKETS
POST /api/v2/admin/rebalance-ws

RESPONSE (200):
{
  "action": "REBALANCE_WS",
  "moved_count": 150,
  "details": [
    "RELIANCE_26FEB_2640CE: 1 -> 3",
    "RELIANCE_26FEB_2645CE: 1 -> 3",
    ...
  ]
}


# ============================================================================
# SYSTEM HEALTH CHECK
# ============================================================================

# 17. HEALTH CHECK
GET /health

RESPONSE (200):
{
  "status": "healthy",
  "subscriptions": 12500,
  "websocket_status": { ... }
}


# ============================================================================
# EXAMPLE FLOW: USER ADDS RELIANCE OPTION CHAIN
# ============================================================================

STEP 1: User types "REL" in search box
→ GET /api/v2/instruments/search?q=REL&limit=10
← [{"symbol": "RELIANCE", "f_o_eligible": true}, ...]

STEP 2: User selects RELIANCE
→ GET /api/v2/instruments/RELIANCE/expiries
← ["26FEB2026", "26MAR2026", ...]

STEP 3: User selects expiry 26FEB2026 and LTP is 2641.5
→ GET /api/v2/option-chain/RELIANCE?expiry=26FEB2026&underlying_ltp=2641.5
← Option chain with 25 strikes (2600, 2625, 2640, 2675, ...)

STEP 4: User clicks "Add to Watchlist"
→ POST /api/v2/watchlist/add
  {
    "user_id": 1,
    "symbol": "RELIANCE",
    "expiry": "26FEB2026",
    "instrument_type": "STOCK_OPTION",
    "underlying_ltp": 2641.5
  }
← {
    "success": true,
    "option_chain": {...},
    "strikes_subscribed": 50
  }

STEP 5: System subscribes all 50 strikes (25 CE + 25 PE) to Dhan WebSocket
- Subscriptions stored in DB
- Distributed across WS (least-loaded gets new ones)

STEP 6: Frontend renders option chain with bid/ask from Dhan WebSocket

STEP 7: At 3:30 PM (EOD)
→ POST /api/v2/admin/unsubscribe-all-tier-a
← Automatically called by scheduler

STEP 8: All 50 RELIANCE strikes unsubscribed
- Next day: fresh start
