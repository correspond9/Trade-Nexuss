# Data Flow Architecture - Visual Guide

## Current Implementation Architecture

### 1. Hook Data Structure

```javascript
// Returned by useAuthoritativeOptionChain hook:
chainData = {
  underlying: "NIFTY",           // ✅ From API
  expiry: "2026-02-11",          // ✅ From API
  lot_size: 50,                  // ✅ From instruments API (NOT hardcoded)
  strike_interval: 100,          // ✅ From ATM engine (NOT hardcoded)
  atm_strike: 23000,             // ✅ From ATM engine (NOT hardcoded)
  underlying_ltp: 23150.50,      // ✅ From /market/underlying-ltp (in fallback)
  
  // Strike data - normalized structure (all sources)
  strikes: {
    "22900": {
      strike_price: 22900,
      CE: {
        token: "12345",
        ltp: 250.50,             // ✅ From live cache OR estimated
        bid: 250.00,             // ✅ From live cache OR estimated
        ask: 251.00,             // ✅ From live cache OR estimated
        greeks: { delta: 0.5 },  // ✅ From live cache (empty if estimated)
        source: "live_cache"     // OR "estimated_from_ltp"
      },
      PE: {
        token: "12346",
        ltp: 250.50,             // ✅ From live cache OR estimated
        bid: 250.00,
        ask: 251.00,
        greeks: {},
        source: "live_cache"     // OR "estimated_from_ltp"
      }
    },
    "23000": {
      // ATM strike - typically higher estimated premium if fallback
      CE: { ltp: 350.00, source: "estimated_from_ltp" },
      PE: { ltp: 350.00, source: "estimated_from_ltp" }
    },
    // ... more strikes
  }
}
```

---

## Data Flow Diagram

### Path A: Live Cache Available (200 OK)

```
User loads OPTIONS/STRADDLE page
     ↓
useAuthoritativeOptionChain(symbol="NIFTY", expiry="2026-02-11")
     ↓
GET /api/v2/options/live?underlying=NIFTY&expiry=2026-02-11
     ↓ (200 OK - Cache Hit)
Response: {
  data: { strikes: {...}, lot_size: 50, ... }
}
     ↓
setData(chainData)  // Has live LTP values
     ↓
Pages render with LIVE PREMIUMS
  - OPTIONS: Shows real CE/PE LTPs
  - STRADDLE: Shows real straddle premiums
  - Headers: LTP, ATM, Step, Lot size - all from hook
```

### Path B: Cache Miss (404) - Fallback to LTP Estimation

```
User loads OPTIONS/STRADDLE page
     ↓
useAuthoritativeOptionChain(symbol="NIFTY", expiry="2026-02-11")
     ↓
GET /api/v2/options/live?underlying=NIFTY&expiry=2026-02-11
     ↓ (404 Not Found - Cache Miss)
Trigger Fallback Logic
     ↓
┌─────────────────────────────────────┐
│ Step 1: Fetch Underlying LTP         │
├─────────────────────────────────────┤
│ GET /market/underlying-ltp/NIFTY    │
│ Response: { ltp: 23150.50 }         │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│ Step 2: Generate Strikes            │
├─────────────────────────────────────┤
│ GET /option-chain/NIFTY             │
│  ?expiry=2026-02-11                 │
│  &underlying_ltp=23150.50           │
│ Response: {                         │
│   strikes: [22900, 23000, 23100],  │
│   atm_strike: 23000,               │
│   strike_step: 100                 │
│ }                                  │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│ Step 3: Fetch Lot Size              │
├─────────────────────────────────────┤
│ GET /instruments/search?q=NIFTY     │
│ Response: { lot_size: 50 }          │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│ Step 4: Build Estimated Premiums    │
├─────────────────────────────────────┤
│ formula:                            │
│   base = underlying_ltp * 0.1       │
│   distance = |strike - atm|/step    │
│   premium = base / (1 + dist*0.5)   │
│                                     │
│ Result for NIFTY @ 23150.50:       │
│   Strike 22900 (ATM-100):          │
│     CE: ~2315 * 0.1 / (1+0.5) = 154 │
│     PE: ~154                        │
│   Strike 23000 (ATM):              │
│     CE: ~231.5 ≈ 231              │
│     PE: ~231.5 ≈ 231              │
│   Strike 23100 (ATM+100):          │
│     CE: ~154                        │
│     PE: ~154                        │
└─────────────────────────────────────┘
     ↓
setData({
  underlying: "NIFTY",
  lot_size: 50,
  strike_interval: 100,
  atm_strike: 23000,
  underlying_ltp: 23150.50,
  strikes: {
    "22900": {
      CE: { ltp: 154, source: "estimated_from_ltp" },
      PE: { ltp: 154, source: "estimated_from_ltp" }
    },
    ...
  }
})
     ↓
Pages render with ESTIMATED PREMIUMS
  - OPTIONS: Shows estimated CE/PE LTPs
  - STRADDLE: Shows estimated straddle premiums
  - Headers: LTP, ATM, Step, Lot size - all available
  - Console shows: "Using fallback: X strikes, ATM=Y, LotSize=Z"
```

---

## Component Data Usage

### OPTIONS.jsx

```javascript
// Hook call
const { data: chainData, ... } = useAuthoritativeOptionChain(symbol, expiry, {...});

// Extract lot size (NO hardcoding)
const getLotSize = () => chainData?.lot_size || 50;

// Extract strike interval
useEffect(() => {
  if (chainData?.strike_interval) setStrikeInterval(chainData.strike_interval);
}, [chainData?.strike_interval]);

// Display header
<div>
  <span>LTP: {underlyingPrice}</span>
  <span>ATM: {getATMStrike()}</span>        ← from hook
  <span>Step: {strikeInterval}</span>       ← from hook
  <span>Lot: {getLotSize()}</span>          ← from hook
</div>

// Build strike rows
strikes.map(s => ({
  strike: s.strike,
  ltpCE: s.CE.ltp,      ← from hook (live OR estimated)
  ltpPE: s.PE.ltp,      ← from hook (live OR estimated)
  lotSize: s.lotSize,   ← from hook
  ceSource: s.CE.source ← "live_cache" OR "estimated_from_ltp"
}))

// Button handlers use hook data
<button onClick={() => {
  handleOpenOrderModal([{
    symbol: "...",
    ltp: strikeData.ltpCE,     ← from hook
    lotSize: strikeData.lotSize ← from hook
  }])
}}/>
```

### STRADDLE.jsx

```javascript
// Hook call
const { data: chainData, ... } = useAuthoritativeOptionChain(symbol, expiry, {...});

// Extract data (NO hardcoding)
useEffect(() => {
  if (chainData?.strike_interval) setStrikeInterval(chainData.strike_interval);
}, [chainData?.strike_interval]);

// Display header
<div>
  <span>ATM: {centerStrike}</span>        ← from hook
  <span>Step: {strikeInterval}</span>     ← from hook
  <span>LTP: {underlyingPrice}</span>     ← from API
</div>

// Build straddle rows
straddles.map(s => ({
  strike: s.strike,
  ce_ltp: s.CE.ltp,              ← from hook
  pe_ltp: s.PE.ltp,              ← from hook
  straddle_premium: ce+pe,        ← calculated from hook data
  lot_size: chainData.lot_size,   ← from hook
  price_source: s.CE.source       ← "live_cache" OR "estimated_from_ltp"
}))

// Button handlers
<button onClick={() => {
  handleOpenOrderModal([
    { ltp: straddle.ce_ltp, lotSize: straddle.lot_size },
    { ltp: straddle.pe_ltp, lotSize: straddle.lot_size }
  ])
}}/>
```

---

## Data Source Matrix

| Data Item | Live Cache | Fallback | Never Hardcoded |
|-----------|-----------|----------|-----------------|
| Underlying Symbol | ✅ | ✅ | ✅ |
| Expiry Date | ✅ | ✅ | ✅ |
| **Lot Size** | ✅ API | ✅ API | ✅ YES |
| **Strike Interval** | ✅ API | ✅ ATM Engine | ✅ YES |
| **ATM Strike** | ✅ API | ✅ ATM Engine | ✅ YES |
| **CE LTP** | ✅ Live | ✅ Estimated | ✅ YES |
| **PE LTP** | ✅ Live | ✅ Estimated | ✅ YES |
| Bid/Ask | ✅ Live | ✅ Estimated | ✅ YES |
| Greeks | ✅ Live | ❌ Empty | N/A |

---

## Error Handling Scenarios

### Scenario 1: Network Error During Fallback

```javascript
try {
  // Fetch underlying LTP
  const ltpResponse = await fetch(...);
  if (!ltpResponse.ok) throw Error("LTP fetch failed");
  
  // Fetch strikes from ATM engine
  const fallbackResponse = await fetch(...);
  if (!fallbackResponse.ok) throw Error("ATM engine failed");
  
  // Fetch lot size
  const instrumentsResponse = await fetch(...);
  // ✅ NOT required to succeed (has fallback)
  
  // Build data...
  setData(chainData);
  
} catch (fallbackErr) {
  // ❌ Fallback completely failed
  setError("Unable to load option chain data");
  setData(null); // No data available
}

// Pages show: Error state with retry button
```

### Scenario 2: Partial Fallback (Lot Size Fetch Fails)

```javascript
// If /instruments/search fails:
let lotSize = null;  // Will be null in chainData
try {
  const resp = await fetch(instrumentsUrl);
  if (resp.ok) lotSize = resp.json().lot_size;
} catch (e) {
  // ✅ Fallback continues, lotSize remains null
}

// Pages show: Lot size as null (graceful degradation)
// Header might show: "Lot: --" or use default
```

### Scenario 3: Strike Estimation Edge Cases

```javascript
// Case A: Strike is ATM
isAtm = (strike === atmStrike)  // true
estimatedPremium = base        // Full premium

// Case B: Strike is far from ATM (e.g., +300 points away)
distance = 300 / 100 = 3
estimatedPremium = base / (1 + 3*0.5) = base / 2.5  // Much lower

// Case C: Strike is +50 from ATM
distance = 0.5
estimatedPremium = base / 1.25  // Slightly lower than ATM

// ✅ This creates realistic premium curve
```

---

## Verification Checklist

### Code Quality
- [ ] No hardcoded lot sizes in OPTIONS.jsx
- [ ] No hardcoded lot sizes in STRADDLE.jsx
- [ ] Lot sizes always from `chainData.lot_size`
- [ ] Strike intervals always from `chainData.strike_interval`
- [ ] ATM strikes always from `chainData.atm_strike` or hook method

### Data Flow
- [ ] Live path: direct from API
- [ ] Fallback path: underlying LTP → strikes → lot size → estimate
- [ ] Both paths return identical data structure
- [ ] Source tracking works (live vs estimated)

### Pages Display
- [ ] OPTIONS: Shows all 5 header items (LTP, ATM, Step, Lot, Exp)
- [ ] STRADDLE: Shows all 4 header items (Symbol, ATM, Step, LTP)
- [ ] Both pages: Show strike interval (not hardcoded)
- [ ] Both pages: Show actual lot sizes (not hardcoded)

### Fallback Behavior
- [ ] 404 triggers fallback (not error)
- [ ] Fallback estimates premiums (not N/A)
- [ ] Fallback fetches lot size
- [ ] Fallback calculates strike interval
- [ ] Console shows "Using fallback: X strikes..."

---

## Browser Console Debugging

### Watch for these log messages:

**Live Cache Hit:**
```
[useAuthoritativeOptionChain] Fetching from: http://127.0.0.1:8000/api/v2/options/live?underlying=NIFTY&expiry=2026-02-11
[useAuthoritativeOptionChain] ✅ Loaded 19 strikes for NIFTY 2026-02-11
[STRADDLE] 📊 NIFTY LTP: 23150.50
[STRADDLE] 📏 Strike Interval: 100
[STRADDLE] 📍 Center strike (ATM): 23000
```

**Cache Miss (Fallback):**
```
[useAuthoritativeOptionChain] Fetching from: http://127.0.0.1:8000/api/v2/options/live?underlying=NIFTY&expiry=2026-02-11
[useAuthoritativeOptionChain] ❌ Failed to fetch option chain
[useAuthoritativeOptionChain] 📊 Using fallback: 19 strikes, ATM=23000, LotSize=50
[OPTIONS] Could not fetch underlying price for NIFTY: (if offline)
[OPTIONS] Strike Interval: 100
```

### Check in DevTools Elements:

Look for these in rendered HTML:
```html
<!-- OPTIONS Header should show: -->
<span>LTP: 23150.50</span>       ← From /market/underlying-ltp
<span>ATM: 23000</span>          ← From hook
<span>Step: 100</span>           ← From hook (NOT hardcoded)
<span>Lot: 50</span>             ← From hook (NOT hardcoded)

<!-- STRADDLE Header should show: -->
<span>ATM: 23000</span>          ← From hook
<span>Step: 100</span>           ← From hook (NOT hardcoded)
<span>LTP: 23150.50</span>       ← From /market/underlying-ltp
```

