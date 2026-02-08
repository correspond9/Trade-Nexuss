# 🎯 QUICK REFERENCE CARD

**Two-Tier Subscription System - Fast Lookup**

---

## 🚀 START BACKEND
```bash
python -m uvicorn app.main:app --port 8000
```

## 📊 KEY METRICS
- **Total Capacity**: 25,000 instruments
- **Tier A (User)**: Up to 17,500
- **Tier B (Always)**: ~8,500
- **Connections**: 5 WebSocket
- **Per Connection**: 5,000 max
- **Session**: 9:15 AM - 3:30 PM IST

---

## 🔌 16 API ENDPOINTS

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/v2/watchlist/add` | Add to watchlist |
| POST | `/api/v2/watchlist/remove` | Remove from watchlist |
| GET | `/api/v2/watchlist/{user_id}` | List watchlist |
| GET | `/api/v2/option-chain/{symbol}` | Get chain |
| POST | `/api/v2/option-chain/subscribe` | Subscribe chain |
| GET | `/api/v2/subscriptions/status` | Overall status |
| GET | `/api/v2/subscriptions/active` | List active |
| GET | `/api/v2/subscriptions/{token}` | Get details |
| GET | `/api/v2/instruments/search` | Search symbols |
| GET | `/api/v2/instruments/{symbol}/expiries` | Get expiries |
| POST | `/api/v2/admin/unsubscribe-all-tier-a` | EOD cleanup |
| POST | `/api/v2/admin/clear-watchlists` | Clear watchlists |
| GET | `/api/v2/admin/ws-status` | WS stats |
| POST | `/api/v2/admin/rebalance-ws` | Rebalance |
| GET | `/health` | Health check |

---

## 📝 EXAMPLE: ADD RELIANCE TO WATCHLIST

```bash
curl -X POST http://localhost:8000/api/v2/watchlist/add \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "symbol": "RELIANCE",
    "expiry": "26FEB2026",
    "instrument_type": "STOCK_OPTION",
    "underlying_ltp": 2641.5
  }'
```

**Response**: 50 strikes subscribed (25 CE + 25 PE)

---

## 🔧 CORE MODULES

| Module | Purpose | Key Methods |
|--------|---------|-------------|
| `registry.py` | Index instruments | `get_by_symbol()`, `get_strike_step()` |
| `atm_engine.py` | ATM calculation | `generate_chain()`, `should_recalculate()` |
| `subscription_manager.py` | Track subscriptions | `subscribe()`, `unsubscribe()`, `get_ws_stats()` |
| `watchlist_manager.py` | User watchlists | `add_to_watchlist()`, `remove_from_watchlist()` |
| `ws_manager.py` | Load balance WS | `add_instrument()`, `rebalance()` |

---

## 💾 DATABASE TABLES

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `watchlist` | User watchlists | user_id, symbol, expiry, added_order |
| `subscriptions` | Active subs | instrument_token, tier, ws_id |
| `atm_cache` | Strike metadata | symbol, atm_strike, generated_strikes |
| `subscription_log` | Audit trail | action, instrument_token, reason |

---

## 🔄 ATM CALCULATION

```python
ATM = round(LTP / Strike_Step) * Strike_Step

Example:
LTP = 2641.5
Step = 5.0
ATM = round(2641.5 / 5) * 5 = 2640.0
```

**Recalculates ONLY on**:
- Price move ≥ 1 strike step
- Expiry change  
- Option chain UI reopen
- ❌ NOT per tick

---

## 📈 STRIKE WINDOWS

| Type | Count | Example |
|------|-------|---------|
| Index Options (NIFTY) | 101 | 50 above + ATM + 50 below |
| Index Options (FINNIFTY) | 50 | 25 above + ATM + 24 below |
| Stock Options | 25 | 12 above + ATM + 12 below |
| MCX Options | 101 | 50 above + ATM + 50 below |

---

## ⚡ RATE LIMITING

**Hard Limit**: 25,000 instruments

**If over limit**:
1. Check: current + new > 25,000?
2. Evict oldest Tier A (LRU)
3. Add new chain
4. Notify user

---

## 🎯 USER FLOW

```
1. Search: GET /api/v2/instruments/search?q=REL
2. Select: Get expiries
3. Preview: GET /api/v2/option-chain/RELIANCE?expiry=...&ltp=2641.5
4. Add: POST /api/v2/watchlist/add
5. Trade: Bid/ask flows in real-time
6. 3:30 PM: Auto-cleanup (EOD)
```

---

## 📊 STATUS QUERY

```bash
curl http://localhost:8000/api/v2/subscriptions/status

Returns:
{
  "subscriptions": {
    "total_subscriptions": 12500,
    "tier_a_count": 2500,
    "tier_b_count": 10000,
    "utilization_percent": 50.0
  },
  "websocket": {
    "total_subscriptions": 12500,
    "connected_connections": 5,
    "per_connection": {
      "ws_1": {"instruments": 2500, "utilization_percent": 50.0},
      ...
    }
  }
}
```

---

## 📁 FILE STRUCTURE

```
NEW: app/market/
├── instrument_master/registry.py    ← Index 289k instruments
├── atm_engine.py                    ← ATM calculation
├── subscription_manager.py          ← Track subscriptions
├── watchlist_manager.py             ← User watchlists
└── ws_manager.py                    ← Load balance WS

NEW: app/rest/
└── market_api_v2.py                 ← 16 REST endpoints

UPDATED: app/storage/models.py       ← +4 tables
UPDATED: app/main.py                 ← Manager init + routes
```

---

## 📚 DOCUMENTATION

| Document | Quick Link | Length |
|----------|-----------|--------|
| Full Docs | `TWO_TIER_SYSTEM_COMPLETE.md` | 400 lines |
| API Ref | `API_REFERENCE.md` | 300 lines |
| Implementation | `IMPLEMENTATION_SUMMARY.md` | 250 lines |
| Architecture | `ARCHITECTURE_DIAGRAM.md` | 200 lines |
| Integration | `INTEGRATION_CHECKLIST.md` | 400 lines |
| Summary | `FINAL_SUMMARY.md` | 250 lines |

---

## ⏳ REMAINING WORK

- [ ] Phase 2: EOD Scheduler (1 hour)
- [ ] Phase 3: Tier B Pre-loading (1 hour)
- [ ] Phase 4: DhanHQ Integration (30 min)
- [ ] Phase 5: Testing (1 hour)

**Total**: 3.5 hours to full deployment

---

## 🚀 DEPLOY CHECKLIST

- [ ] Install apscheduler: `pip install apscheduler`
- [ ] Update requirements.txt
- [ ] Run migrations: Create 4 new tables
- [ ] Test 3 endpoints (search, chain, status)
- [ ] Implement EOD scheduler
- [ ] Implement Tier B pre-loading
- [ ] Run end-to-end tests
- [ ] Deploy to VPS
- [ ] Monitor 24 hours

---

## 💡 TIPS

**To add stock to watchlist**:
```bash
POST /api/v2/watchlist/add
{
  "user_id": 1,
  "symbol": "RELIANCE",
  "expiry": "26FEB2026",
  "instrument_type": "STOCK_OPTION",
  "underlying_ltp": 2641.5
}
```

**To check status**:
```bash
GET /api/v2/subscriptions/status
```

**To search instruments**:
```bash
GET /api/v2/instruments/search?q=REL&limit=10
```

**To cleanup EOD** (manual):
```bash
POST /api/v2/admin/unsubscribe-all-tier-a
```

---

## 🎯 KEY NUMBERS

- **289,298** instruments in master
- **25,000** subscription capacity
- **5** WebSocket connections
- **5,000** instruments per WS
- **101** strikes max (index options)
- **25** strikes typical (stock options)
- **50** CE + PE per chain
- **3.5** hours to full deployment
- **2,090** lines of production code
- **1,500** lines of documentation

---

**Status**: 80% complete, ready for integration  
**Next**: Implement EOD scheduler (1 hour)  
**Deployment**: 3.5 hours total
