# Quick Start Guide - Python Dhan Feed

## 🎯 What Changed
- ❌ Removed: Node.js market data service (port 9100)
- ✅ Added: Native Python WebSocket to Dhan (direct connection)
- ✅ Added: CRUDEOIL price feed (was missing before)
- ✅ Added: HTTP REST endpoint for price polling

## 🚀 How to Use

### 1. Verify Credentials Exist
```python
# Open Python shell in project directory
from app.storage.db import SessionLocal
from app.storage.models import DhanCredential

db = SessionLocal()
cred = db.query(DhanCredential).first()
if cred:
    print(f"✅ Client ID: {cred.client_id}")
else:
    print("❌ No credentials found - add via admin panel")
db.close()
```

### 2. Start Backend
```bash
uvicorn app.main:app --reload
```

### 3. Check Prices

#### Via HTTP
```bash
curl http://localhost:8000/prices
```

Output:
```json
{
  "NIFTY": 23445.50,
  "SENSEX": 77800.25,
  "CRUDEOIL": 75.80
}
```

#### Via WebSocket
```bash
# Install wscat if needed: npm install -g wscat
wscat -c ws://localhost:8000/ws/prices
```

Output:
```json
{"NIFTY": 23445.50, "SENSEX": 77800.25, "CRUDEOIL": 75.80}
{"NIFTY": 23446.20, "SENSEX": 77801.50, "CRUDEOIL": 75.82}
...
```

## 📊 Files Modified

| File | Change |
|------|--------|
| `requirements.txt` | Added websocket-client, dhanhq, requests |
| `app/lifecycle/hooks.py` | Start Dhan feed directly (no Node.js) |
| `app/dhan/dhan_socket_a.py` | Added CRUDEOIL, better logging |
| `app/market/live_prices.py` | Added get_prices() helper function |
| `app/rest/ws.py` | Added GET /prices endpoint |

## 🔍 Troubleshooting

### "Missing Dhan credentials"
→ Add credentials via admin panel or directly to database

### "Connection refused" to wss://api-feed.dhan.co
→ Check internet connection, verify API endpoint is accessible

### Prices showing 0.0
→ Subscription payload might be wrong, check console logs for errors

### "Module not found: websocket"
→ Run: `pip install websocket-client`

## 📝 Binary Protocol Details

**Subscription Packet:**
```
Byte 0: 15 (RequestCode)
Byte 1: 3  (InstrumentCount)
Bytes 2-6: NIFTY (segment=1, token=13)
Bytes 7-11: SENSEX (segment=1, token=51)
Bytes 12-16: CRUDEOIL (segment=5, token=114)
```

**Tick Frame:**
```
[Segment:1B] [Token:4B BE] [LTP:8B double BE]
```

## ✅ Success Indicators

- ✅ No import errors on startup
- ✅ Logs show "✅ DhanSocket Method A connected"
- ✅ `/prices` endpoint returns non-zero values
- ✅ WebSocket receives updates every second
- ✅ Prices change throughout trading hours

---

**Frontend Integration:**
Your frontend is ready to connect immediately!
Just point it to `ws://localhost:8000/ws/prices` or `http://localhost:8000/prices`
