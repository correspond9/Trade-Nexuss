# Comprehensive Testing Guide - Data Flow Verification

**Created**: 2026-02-04  
**Purpose**: Validate all data flows are correct and no hardcoded values exist

---

## Test Environment Setup

### Prerequisites
- Backend running: `uvicorn app.main:app --reload` (port 8000)
- Frontend running: `npm run dev` (port 5173)
- Browser: Chrome/Firefox with DevTools open
- Network: Console tab ready for log monitoring

### Backend Data Availability

```bash
# Check if backend is serving data:

# 1. Verify underlying LTP endpoint
curl http://127.0.0.1:8000/api/v2/market/underlying-ltp/NIFTY

# 2. Verify instruments search
curl http://127.0.0.1:8000/api/v2/instruments/search?q=NIFTY

# 3. Verify option chain endpoint (fallback)
curl "http://127.0.0.1:8000/api/v2/option-chain/NIFTY?expiry=2026-02-11&underlying_ltp=23150"

# 4. Verify live cache endpoint
curl "http://127.0.0.1:8000/api/v2/options/live?underlying=NIFTY&expiry=2026-02-11"
```

---

## Test Suite 1: OPTIONS Tab

### Test 1.1: Load with Live Data

**Precondition**: Backend cache is populated with live data

**Steps**:
1. Navigate to terminal app
2. Click on "OPTIONS" tab
3. Select "NIFTY 50" from index selector
4. Select an expiry date (e.g., Feb 11, 2026)
5. Wait for data to load

**Expected Results**:
```
✅ Header displays:
   - Symbol: "NIFTY OPTIONS"
   - LTP: e.g., "23150.50"
   - ATM: e.g., "23000"
   - Step: e.g., "100" (NOT hardcoded)
   - Lot: e.g., "50" (NOT hardcoded)
   - Strike Count: e.g., "(19 strikes)"
   - Expiry: e.g., "11"

✅ Strike table displays:
   - Multiple strikes (e.g., 22900, 23000, 23100)
   - CE premium values: e.g., "250.50", "350.25", "200.75"
   - PE premium values: e.g., "250.50", "350.25", "200.75"
   - ATM row highlighted (different background)

✅ Console logs show:
   [useAuthoritativeOptionChain] Fetching from: ...options/live...
   [useAuthoritativeOptionChain] ✅ Loaded 19 strikes for NIFTY...

✅ No "N/A" values in premiums
```

**Verification Code** (paste in DevTools console):
```javascript
// Verify no hardcoded lot sizes
const pageHTML = document.body.innerHTML;
const hasHardcodedSwitch = pageHTML.includes("case 'NIFTY': return 50");
console.log("Has hardcoded lot size switch:", hasHardcodedSwitch); // Should be FALSE

// Check hook data
const strikeElements = document.querySelectorAll('[class*="grid"][class*="cols-3"]');
console.log("Strike rows found:", strikeElements.length);

// Sample check for N/A values
const nACount = pageHTML.match(/N\/A/g)?.length || 0;
console.log("N/A values found:", nACount, "(should be 0 or very few)");
```

### Test 1.2: Load with Fallback (Simulate Cache Miss)

**Precondition**: Backend cache is EMPTY or returns 404

**Steps**:
1. Stop backend cache service (don't stop backend itself)
2. Or clear cache via admin endpoint (if available)
3. Navigate to OPTIONS tab
4. Select NIFTY 50
5. Select expiry
6. Observe console logs

**Expected Results**:
```
✅ Header displays (all values present):
   - Symbol: "NIFTY OPTIONS"
   - LTP: e.g., "23150.50" (from fallback fetch)
   - ATM: e.g., "23000" (from ATM engine)
   - Step: e.g., "100" (from ATM engine)
   - Lot: e.g., "50" (from instruments API)
   - Count: e.g., "(19 strikes)"

✅ Strike table displays ESTIMATED premiums:
   - Shows values like "154.20", "231.50", "154.20"
   - NOT N/A, NOT 0
   - Premium curve realistic (ATM higher, edges lower)

✅ No errors shown to user

✅ Console shows fallback flow:
   [useAuthoritativeOptionChain] ❌ Failed to fetch option chain
   [useAuthoritativeOptionChain] 📊 Using fallback: 19 strikes, ATM=23000, LotSize=50

✅ Premium values should be ~10-20% of underlying LTP
   (e.g., for LTP=23150: base = 2315, so premiums ~150-300)
```

**Verification Code** (paste in DevTools console):
```javascript
// Check data structure from hook
// (Hook data would be in React component state, harder to access directly)

// Check if fallback was used
const consoleLogs = document.body.__reactInternalInstance;
console.log("Checking strike values...");

const strikeDataElements = document.querySelectorAll('[class*="font-semibold"]');
strikeDataElements.forEach(el => {
  const text = el.textContent;
  if (text.match(/^\d+\.\d+$/)) {
    console.log("Found premium value:", text);
  }
});
```

### Test 1.3: Switch Between Expirations

**Precondition**: Multiple expirations available for NIFTY

**Steps**:
1. Load OPTIONS page with Feb 11 expiry
2. Observe strikes and ATM
3. Switch to Feb 18 expiry
4. Observe strikes update
5. Switch back to Feb 11

**Expected Results**:
```
✅ Each expiry switch triggers new API call
✅ Strike list updates (different ATM, different range)
✅ ATM strike changes (e.g., 23000 → 23100)
✅ Step remains consistent (100 for all expirations)
✅ Lot size remains consistent (50 for NIFTY)
✅ No UI flicker or incorrect cached data

✅ Console shows new fetch:
   [useAuthoritativeOptionChain] Fetching from: ...options/live...?expiry=2026-02-18
   [useAuthoritativeOptionChain] ✅ Loaded X strikes for NIFTY 2026-02-18
```

### Test 1.4: Switch Between Underlyings

**Precondition**: Multiple underlyings available (NIFTY, BANKNIFTY)

**Steps**:
1. Load OPTIONS page with NIFTY
2. Note: Lot size (50), Step (100), LTP
3. Switch to BANKNIFTY
4. Observe data updates
5. Switch back to NIFTY

**Expected Results**:
```
✅ Each underlying switch triggers new API calls
✅ Lot size updates correctly:
   - NIFTY: 50
   - BANKNIFTY: 25
   - SENSEX: 10
   ✅ THESE ARE FETCHED FROM API, NOT HARDCODED

✅ Step may be same or different (depends on strike interval)
✅ ATM changes appropriately
✅ LTP updates

✅ No hardcoded values used in the switch logic
```

**Verification - Inspect Network Tab**:
1. Open DevTools → Network tab
2. Filter for "instruments/search"
3. Each underlying switch should show request like:
   ```
   /api/v2/instruments/search?q=BANKNIFTY&limit=1
   Response: { lot_size: 25, ... }
   ```
4. Lot size is served by API, not from client-side hardcoding

### Test 1.5: Buy/Sell Button Clicks

**Precondition**: OPTIONS page loaded with data

**Steps**:
1. Find a strike row (e.g., ATM strike 23000)
2. Click "B" (Buy) button on CE column
3. Observe modal opens
4. Check passed data (ltp, lotSize)
5. Click "S" (Sell) button on PE column

**Expected Results**:
```
✅ Modal opens with order details:
   - Symbol: "NIFTY 23000 CE" or similar
   - LTP: From hook (e.g., "250.50")
   - Lot Size: From hook (e.g., "50")
   - Action: BUY or SELL

✅ Lot size in modal is NOT hardcoded
   - If fallback: ~50 (from fallback fetch)
   - If live: 50 (from cache)
   - Both come from hook, not client code

✅ No hardcoded lot size logic in button handler
```

**Verification Code** (paste in DevTools console):
```javascript
// After clicking a button, check modal data
const modalText = document.body.innerHTML;
const lotSizeMatch = modalText.match(/Lot[^0-9]*(\d+)/);
console.log("Modal lot size:", lotSizeMatch?.[1] || "NOT FOUND");

// Should match header lot size
const headerLot = document.querySelector('[class*="text-blue"]')?.textContent;
console.log("Header lot size:", headerLot);

// Both should be same and from hook data
```

---

## Test Suite 2: STRADDLE Tab

### Test 2.1: Load with Live Data

**Precondition**: Backend cache populated

**Steps**:
1. Click "STRADDLE" tab
2. Select NIFTY 50
3. Select expiry
4. Wait for data

**Expected Results**:
```
✅ Header shows:
   - Symbol: "NIFTY Straddles"
   - ATM: e.g., "23000"
   - Step: e.g., "100" (NOT hardcoded)
   - LTP: e.g., "23150.50"
   - Count: e.g., "(19 strikes)"

✅ Straddle matrix displays:
   - Strike column: 22900, 23000, 23100, ...
   - Straddle premium: e.g., "500.25", "700.50", "500.25"
   - CE + PE breakdown shown
   - All values > 0 (not N/A)

✅ Console shows:
   [STRADDLE] 📊 NIFTY LTP: 23150.50
   [STRADDLE] 📏 Strike Interval: 100
   [STRADDLE] 📍 Center strike (ATM): 23000
```

### Test 2.2: Load with Fallback

**Precondition**: Cache empty/404

**Steps**:
1. Clear cache or stop cache service
2. Load STRADDLE page
3. Select NIFTY and expiry
4. Observe data

**Expected Results**:
```
✅ Header displays all values (none null/empty):
   - All metadata present
   - Step: 100 (from fallback)
   - Lot: Not shown but used internally

✅ Straddle matrix shows estimated premiums:
   - Example: "300.20" = 150.10 (CE) + 150.10 (PE)
   - ATM premium higher (e.g., 450)
   - Edge premiums lower (e.g., 300)

✅ Premium curve realistic

✅ No N/A values

✅ Console shows fallback:
   [useAuthoritativeOptionChain] 📊 Using fallback: 19 strikes, ATM=23000, LotSize=50
```

### Test 2.3: Buy/Sell Straddle

**Precondition**: STRADDLE page loaded with data

**Steps**:
1. Find ATM strike row (23000)
2. Click "BUY" button
3. Observe modal

**Expected Results**:
```
✅ Modal opens with both legs:
   - First leg: NIFTY 23000 CE, BUY, LTP=350, Lot=50
   - Second leg: NIFTY 23000 PE, BUY, LTP=350, Lot=50

✅ Lot sizes match header (NOT hardcoded):
   - Both legs show 50
   - 50 comes from hook

✅ LTPs are from hook:
   - Live: real prices
   - Fallback: estimated from underlying LTP
```

### Test 2.4: Verify No Hardcoded Lot Sizes

**Precondition**: STRADDLE page loaded

**Steps**:
1. Open DevTools → Sources tab
2. Open frontend/src/pages/STRADDLE.jsx
3. Search for "NIFTY" and "50"
4. Inspect surrounding code

**Expected Results**:
```
✅ No code like:
   const lotSize = symbol === 'NIFTY' ? 50 : ...
   
❌ Should NOT find hardcoded mappings

✅ Should find instead:
   const lotSize = chainData.lot_size;
   
✅ Comment says: "// From hook, not hardcoded"
```

---

## Test Suite 3: WATCHLIST Tab

### Test 3.1: Display Current Watchlist

**Precondition**: Some instruments in watchlist

**Steps**:
1. Click "WATCHLIST" tab
2. Observe displayed instruments
3. Look at expiry dates and instrument types

**Expected Results**:
```
✅ Instruments display correctly with:
   - Symbol (e.g., "NIFTY")
   - Type (INDEX, STOCK, FUTURE, OPTION)
   - Expiry dates (if applicable)
   - Strike prices (if option)

✅ Expiry dates are from API/database:
   - Format: "11 FEB" or similar
   - NOT hardcoded static dates

✅ NO hardcoded instruments in the display
```

**Note**: WATCHLIST doesn't use option chain hook directly (it shows list, not real-time prices). That's architecturally correct.

### Test 3.2: Add to Watchlist

**Precondition**: WATCHLIST page open

**Steps**:
1. Type in search box: "NIFTY"
2. See suggestions appear
3. Click on Tier B suggestion (NIFTY if available)
4. Observe it added to watchlist

**Expected Results**:
```
✅ Search works
✅ Suggestions appear with tier labels
✅ Clicking adds to watchlist
✅ Expiry dates are from backend, not hardcoded
```

---

## Test Suite 4: Error Scenarios

### Test 4.1: Network Error (Backend Down)

**Precondition**: Backend stopped

**Steps**:
1. Navigate to OPTIONS tab
2. Select NIFTY and expiry
3. Observe error state

**Expected Results**:
```
✅ Error message displayed (not blank page)
✅ Retry button available
✅ No N/A values or crashes
✅ Console shows error:
   [useAuthoritativeOptionChain] ❌ Failed to fetch option chain
```

### Test 4.2: Invalid Expiry

**Precondition**: OPTIONS page open

**Steps**:
1. Manually set expiry to invalid date (e.g., "1900-01-01")
2. Try to load

**Expected Results**:
```
✅ Shows empty state message:
   "No strikes available for this expiry."
   
✅ No crash
✅ No N/A values everywhere
```

### Test 4.3: Slow Network (Timeout)

**Precondition**: Network tab throttling enabled

**Steps**:
1. DevTools → Network → Slow 3G
2. Load OPTIONS page
3. Select expiry (will take time)

**Expected Results**:
```
✅ Loading spinner shown
✅ Eventually loads or shows error
✅ No permanent "stuck" state
✅ Retry works

✅ Lot size NOT shown as undefined
✅ Step NOT shown as undefined
```

---

## Test Suite 5: Cross-Component Data Consistency

### Test 5.1: Same Expiry Across Tabs

**Precondition**: Multiple tabs loaded

**Steps**:
1. Load OPTIONS tab with NIFTY, Feb 11
2. Load STRADDLE tab with same NIFTY, Feb 11
3. Compare ATM strikes, step sizes, lot sizes

**Expected Results**:
```
✅ ATM strike: SAME in both
✅ Step size: SAME in both
✅ Lot size: SAME in both (even if not displayed in STRADDLE)
✅ Both use same hook source (API)
```

### Test 5.2: Data Refresh on Manual Refresh Button

**Precondition**: OPTIONS page loaded

**Steps**:
1. Click refresh button (circular icon in header)
2. Observe console and data

**Expected Results**:
```
✅ New API call triggered:
   [useAuthoritativeOptionChain] Fetching from: ...
   
✅ Data may update if prices changed
✅ ATM, Step, Lot don't change (they're stable)
```

---

## Final Verification Checklist

Print this and check off as you verify:

### ✅ Code Quality
- [ ] STRADDLE.jsx: No hardcoded lot sizes found
- [ ] OPTIONS.jsx: No hardcoded lot sizes found
- [ ] useAuthoritativeOptionChain.js: Fallback normalizes data
- [ ] Hook returns proper structure (lot_size, strike_interval, atm_strike, strikes)

### ✅ Live Cache Path (200 OK)
- [ ] OPTIONS: Displays real premiums
- [ ] STRADDLE: Displays real straddle premiums
- [ ] Headers: Show actual lot size and step
- [ ] Console: Shows successful load message

### ✅ Fallback Path (404)
- [ ] OPTIONS: Shows estimated premiums (not N/A)
- [ ] STRADDLE: Shows estimated premiums (not N/A)
- [ ] Headers: All fields populated
- [ ] Console: Shows fallback message
- [ ] Premium curve realistic (ATM > edges)

### ✅ Data Sources
- [ ] Lot size: From API (not hardcoded)
- [ ] Strike interval: From API (not hardcoded)
- [ ] ATM strike: From API (not hardcoded)
- [ ] Underlying LTP: From /market/underlying-ltp
- [ ] Expiry dates: From API/database

### ✅ UI/UX
- [ ] No "N/A" values in data (unless truly unavailable)
- [ ] No crash on invalid inputs
- [ ] Retry buttons work
- [ ] Loading states show appropriately
- [ ] Error messages clear

### ✅ Performance
- [ ] Pages load within reasonable time
- [ ] No excessive API calls
- [ ] Fallback doesn't cause delays
- [ ] Refresh button works

---

## Browser Console Spy Script

Run this in DevTools to monitor all API calls:

```javascript
// Spy on fetch calls
const originalFetch = window.fetch;
window.fetch = function(...args) {
  const url = args[0];
  const method = args[1]?.method || 'GET';
  console.log(`🔗 [API] ${method} ${url}`);
  return originalFetch.apply(this, args).then(response => {
    console.log(`✅ Response: ${response.status}`);
    return response;
  }).catch(error => {
    console.log(`❌ Error: ${error.message}`);
    throw error;
  });
};

console.log("✅ API spy activated. All fetch calls will be logged.");
```

Then perform operations and watch console for all API activity.

---

## Issues to Report

If you find any of these, it's a bug:

1. **Hardcoded lot size found in OPTIONS or STRADDLE**
   - File and line number
   - Expected: Use hook data

2. **N/A values shown when data available**
   - Screenshot
   - Expected: Real or estimated premiums

3. **Strike interval not displayed**
   - Page affected (OPTIONS/STRADDLE)
   - Expected: Shows in header

4. **Same underlying shows different lot sizes**
   - Example: NIFTY shows as 50 in OPTIONS, 25 in STRADDLE
   - Expected: Consistent across pages

5. **Fallback not working (404 shows error instead of estimated data)**
   - Timing/steps to reproduce
   - Expected: Fallback loads estimated premiums

---

## Success Criteria

✅ **All of these must be true:**

1. No hardcoded lot sizes in page components
2. All lot sizes fetched from API via hook
3. Strike intervals displayed (from API, not hardcoded)
4. ATM strikes calculated dynamically (from API)
5. Fallback loads estimated premiums (not N/A)
6. Lot sizes match across OPTIONS and STRADDLE
7. No crashes or UI errors
8. Console shows clear debug logs
9. Network tab shows proper API calls
10. All data flows from hook (single source of truth)

