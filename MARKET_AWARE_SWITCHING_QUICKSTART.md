MARKET-AWARE PRICE SWITCHING - QUICK START GUIDE
================================================

## What Changed?

The system now **AUTOMATICALLY** switches between:
- **LIVE prices** when markets are OPEN (9:15 AM - 3:30 PM for NSE/BSE)
- **CLOSING prices** when markets are CLOSED

This happens automatically without any manual intervention!

## How It Works

### 1. On Startup
System checks current time → Loads appropriate data source
```
If 9:15 AM - 3:30 PM: Use LIVE prices from DhanHQ API
If 3:30 PM - 9:15 AM: Use CLOSING prices from file
If Weekend: Use CLOSING prices
```

### 2. Every 5 Minutes
Background scheduler checks if market status changed
```
If just opened: Auto-refresh → Switch to LIVE
If just closed: Auto-refresh → Switch to CLOSING
No change: Continue with current source
```

## Testing This

### Quick Test (Recommended)

**If it's currently market hours (9:15 AM - 3:30 PM):**

1. Start backend
```bash
cd fastapi_backend
python -m uvicorn app.main:app --reload
```

2. Check startup logs
```
[STARTUP] Checking market status and populating cache...
🌙 Markets are CLOSED - loading CLOSING prices...
OR
📈 Markets are OPEN - attempting to load LIVE prices...
```

3. Check which data source is being used
```
[STARTUP] Data sources in use:
   • NIFTY: LIVE (if market open)
   • BANKNIFTY: LIVE
   • SENSEX: LIVE
   OR
   • NIFTY: CLOSING (if market closed)
   • BANKNIFTY: CLOSING
   • SENSEX: CLOSING
```

4. **During market hours:** Prices should change/update frequently
5. **After market hours:** Prices should be static (closing prices)

### Full Test (Complete Verification)

**Test A: Start when market is OPEN, watch it close**
```
1. During market hours (e.g., 2 PM):
   - Start backend
   - Confirm log shows: "📈 Markets are OPEN - attempting to load LIVE prices"
   
2. Let it run and check frontend
   - NIFTY, BANKNIFTY prices should update frequently
   - Data source: LIVE
   
3. Wait until 3:35 PM (after market close)
   - Watch logs for: "🔄 MARKET CLOSED: NSE"
   - Then: "🔄 Market status changed - refreshing option chain cache..."
   - Finally: "Data sources in use: CLOSING"
   
4. Check frontend
   - Prices now static (from closing_prices.py)
   - Data source changed to CLOSING
```

**Test B: Start when market is CLOSED, watch it open**
```
1. After market hours (e.g., 4 PM):
   - Start backend
   - Confirm log shows: "🌙 Markets are CLOSED - loading CLOSING prices"
   
2. Let it run and check frontend
   - NIFTY, BANKNIFTY prices are static
   - Data source: CLOSING
   
3. Set system time to 9:20 AM next day (or wait)
   - Watch logs for: "🔄 MARKET OPENED: NSE"
   - Then: "🔄 Market status changed - refreshing option chain cache..."
   - Finally: "Data sources in use: LIVE"
   
4. Check frontend
   - Prices now updating frequently
   - Data source changed to LIVE
```

**Test C: Restart system at different times**
```
Restart 1 (Market open, 11 AM):
   → Should use LIVE prices
   
Restart 2 (Market close, 4 PM):
   → Should use CLOSING prices
   
Restart 3 (Startup at 8 AM, wait until open):
   → Starts with CLOSING
   → At 9:15 AM, auto-switches to LIVE
   → At 3:30 PM, auto-switches back to CLOSING
```

## Key Logs to Look For

### Startup
```
[STARTUP] Checking market status and populating cache...
📈 Markets are OPEN - attempting to load LIVE prices from DhanHQ API...
✅ Successfully populated cache with LIVE data:

OR

🌙 Markets are CLOSED - loading CLOSING prices...
✅ Successfully populated cache with CLOSING prices:
```

### Market Status Change (Every 5 Minutes)
```
🔄 MARKET OPENED: NSE
🔄 Market status changed - refreshing option chain cache...
🔄 Markets are OPEN - attempting to load LIVE prices...
✅ Successfully populated cache with LIVE data:
Current data sources:
   • NIFTY: LIVE
   • BANKNIFTY: LIVE
   • SENSEX: LIVE
   • FINNIFTY: LIVE
   • MIDCPNIFTY: LIVE
```

OR

```
🔄 MARKET CLOSED: NSE
🔄 Market status changed - refreshing option chain cache...
🌙 Markets are CLOSED - loading CLOSING prices...
✅ Successfully populated cache with CLOSING prices:
Current data sources:
   • NIFTY: CLOSING
   • BANKNIFTY: CLOSING
   • SENSEX: CLOSING
   • FINNIFTY: CLOSING
   • MIDCPNIFTY: CLOSING
```

## Important Notes

### 1. Market Hours
```
NSE/BSE:  9:15 AM - 3:30 PM IST (Monday-Friday)
MCX:      9:00 AM - 11:30 PM IST (Monday-Friday)
Weekends: Always closed
```

### 2. Closing Prices
The file `fastapi_backend/app/market/closing_prices.py` must be updated with latest EOD data.
Current version might have old prices, but system will still work correctly.

### 3. Exchange Tracking
System automatically determines if each underlying is NSE/BSE or MCX:
- NSE/BSE shares same market hours
- MCX has different hours (tracked separately)
- MCX underlyings: CRUDEOIL, NATURALGAS

### 4. No Manual Intervention Needed
System handles everything automatically:
- ✅ Checks market status on startup
- ✅ Monitors market status every 5 minutes
- ✅ Auto-switches data source when market opens/closes
- ✅ Logs all changes for debugging

## Troubleshooting

### "Still showing old closing prices even though market is open"
1. Check current time: Is it really within market hours?
2. Check logs: Does it show "LIVE" or "CLOSING"?
3. Wait 5-10 minutes: Scheduler checks every 5 minutes
4. Check DhanHQ API: May be failing, falling back to closing prices

### "Prices not updating even though it's market hours"
1. Check logs for errors
2. Verify DhanHQ credentials are correct
3. Check API rate limits (1 req/sec for live data)
4. Check internet connectivity

### "Yesterday's closing prices are still showing"
1. Update closing_prices.py with today's EOD data
2. Restart backend
3. Prices will be correct after next market close

## Success Indicators

✅ System shows correct data source on startup
✅ Prices update frequently during market hours (LIVE)
✅ Prices are static after market hours (CLOSING)
✅ CE and PE prices are different (not identical)
✅ No old prices from previous days
✅ Log shows auto-switch when market opens/closes

## Questions?

Check the detailed documentation: `MARKET_AWARE_PRICE_SWITCHING.md`
