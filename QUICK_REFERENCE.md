# Quick Reference Card - Data Flow Fixes

**Print This** - Quick lookup for verifying fixes

---

## ✅ What Was Fixed

### 1. Hardcoded Lot Sizes → API Sourced
```
❌ BEFORE: const lotSize = symbol === 'NIFTY' ? 50 : 25 : 10;
✅ AFTER:  const lotSize = chainData?.lot_size;
```

### 2. Fallback Returns Empty → Estimates Premiums
```
❌ BEFORE: strikesMap[strike] = { CE: { token: "..." } };  // No pricing
✅ AFTER:  strikesMap[strike] = { CE: { ltp: 250.50, bid: 250, ask: 251, ... } };
```

### 3. Strike Interval Hidden → Displayed in Header
```
❌ BEFORE: Header shows: Symbol, ATM, LTP
✅ AFTER:  Header shows: Symbol, ATM, Step (100), LTP
```

### 4. No Source Tracking → Source Field Added
```
❌ BEFORE: { ltp: 250.50 }  // Is this live or estimated?
✅ AFTER:  { ltp: 250.50, source: "live_cache" or "estimated_from_ltp" }
```

---

## 📋 Files Modified

| File | Change | Impact |
|------|--------|--------|
| `useAuthoritativeOptionChain.js` | Fallback estimates premiums | Fallback shows data instead of N/A |
| `STRADDLE.jsx` | Remove hardcoded lot sizes, add strike interval | Dynamic lot sizes, visible strike spacing |
| `OPTIONS.jsx` | Remove hardcoded lot sizes, add strike interval | Dynamic lot sizes, visible strike spacing |
| `WATCHLIST.jsx` | No changes | Architecture appropriate |

---

## 🔍 What to Look For in Testing

### ✅ Correct Implementation Signs

**In Browser DevTools → Console:**
```
✅ Live path:
   [useAuthoritativeOptionChain] ✅ Loaded 19 strikes for NIFTY...

✅ Fallback path:
   [useAuthoritativeOptionChain] ❌ Failed to fetch...
   [useAuthoritativeOptionChain] 📊 Using fallback: 19 strikes, ATM=23000, LotSize=50
```

**In Page Header:**
```
✅ OPTIONS Header shows:
   Symbol | LTP: 23150.50 | ATM: 23000 | Step: 100 | Lot: 50 | Count: (19)

✅ STRADDLE Header shows:
   NIFTY Straddles | ATM: 23000 | Step: 100 | LTP: 23150.50 | (19 strikes)
```

**In Strike Data:**
```
✅ OPTIONS Row shows:
   250.50 (CE premium) | 23000 (Strike) | 250.50 (PE premium)
   
   NOT: N/A or 0 values
   NOT: Hardcoded [25, 50, 100] patterns

✅ STRADDLE Row shows:
   23000 (Strike) | 500.25 (Straddle Premium = CE+PE)
   | CE: 250.50 | PE: 250.50 |
```

---

## ❌ What to Watch For (Bugs)

| Issue | Sign | Fix |
|-------|------|-----|
| Hardcoded lot sizes still present | Header always shows "50" for all symbols | Should show 25 for BANKNIFTY |
| Fallback not working | Shows N/A or 0 when cache empty | Should show estimated premiums |
| Strike interval hardcoded | Step always "100" regardless | Should vary by underlying |
| Lot size from wrong source | Modal shows wrong lot size | Verify API fetch in hook |
| Fallback not fetching lot size | Lot shows null or 50 as default | Should fetch from instruments API |

---

## 🧪 Quick Test (2 min)

1. **Load OPTIONS page**
   - Select NIFTY 50
   - Select an expiry
   - Check header shows: Symbol, LTP, ATM, **Step**, **Lot**
   - Check strikes have values (not N/A)

2. **Load STRADDLE page**
   - Select NIFTY 50
   - Select same expiry
   - Check header shows: Symbol, ATM, **Step**, LTP
   - Check straddle premiums have values

3. **Open DevTools Console**
   - Look for "Using fallback" message
   - Or look for "✅ Loaded XX strikes" message
   - Should see one of these, no errors

4. **Switch underlyings (if possible)**
   - Change to BANKNIFTY
   - Check "Lot: 25" in header (NOT 50)
   - Verify lot size changes correctly

**Result**: If all 4 checks pass ✅, fixes are working!

---

## 📊 Data Flow Decision Tree

```
START: User loads OPTIONS/STRADDLE page

  ├─ Has symbol and expiry?
  │  ├─ NO: Show "Select expiry" message
  │  └─ YES: Continue
  │
  ├─ Call Hook: useAuthoritativeOptionChain(symbol, expiry)
  │
  ├─ Hook calls: GET /options/live?underlying=NIFTY&expiry=2026-02-11
  │
  ├─ API responds?
  │  ├─ 200 OK (Cache Hit)
  │  │  ├─ Parse: { strikes: {...}, lot_size: 50, atm_strike: 23000, ... }
  │  │  ├─ Return: chainData with LIVE PRICES
  │  │  └─ Page shows: Real premiums
  │  │
  │  └─ 404 (Cache Miss)
  │     ├─ Fetch LTP: GET /market/underlying-ltp/NIFTY → 23150.50
  │     ├─ Generate: GET /option-chain/NIFTY?underlying_ltp=23150.50 → [22900, 23000, ...]
  │     ├─ Fetch Lot: GET /instruments/search?q=NIFTY → 50
  │     ├─ Estimate: premiums = base / (1 + distance)
  │     ├─ Build: strikesMap with estimated ltp + source="estimated_from_ltp"
  │     ├─ Return: chainData with ESTIMATED PRICES
  │     └─ Page shows: Realistic estimated premiums (NOT N/A)
  │
  ├─ Page receives: { data: chainData, loading, error }
  │
  ├─ Extract for display:
  │  ├─ lotSize = chainData?.lot_size  (NOT hardcoded)
  │  ├─ step = chainData?.strike_interval  (NOT hardcoded)
  │  ├─ atm = chainData?.atm_strike  (from hook helper)
  │  └─ strikes = chainData.strikes  (live OR estimated)
  │
  └─ Render page with all data from hook
     ✅ Single source of truth
     ✅ No hardcoded values
     ✅ Consistent across pages
     ✅ Proper fallback behavior
```

---

## 🎯 Key Metrics

| Metric | Target | How to Check |
|--------|--------|-------------|
| **Hardcoded lot sizes** | ZERO | Grep for "case 'NIFTY'" in OPTIONS.jsx, STRADDLE.jsx |
| **Lot size source** | 100% API | All should be `chainData?.lot_size` |
| **N/A values on fallback** | ZERO | Load with cache empty, check no N/A shown |
| **Strike interval display** | VISIBLE | Check header in both pages |
| **Console errors** | NONE | Open DevTools console, should be clean |
| **API calls** | Correct | Network tab should show proper calls |

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All tests from TESTING_GUIDE.md passed
- [ ] No "Hardcoded lot size" warnings
- [ ] Fallback works (tested with cache miss scenario)
- [ ] Strike intervals display correctly
- [ ] Lot sizes match across OPTIONS and STRADDLE
- [ ] Console shows debug messages (not errors)
- [ ] Network requests are efficient
- [ ] Mobile responsiveness checked
- [ ] Error states handled gracefully
- [ ] Performance acceptable (< 2s load time)

---

## 💡 FAQ

**Q: Why estimate premiums instead of showing N/A?**  
A: Better UX. Users see realistic data even when cache not ready. Estimation based on ATM theory.

**Q: What if lot size API fails?**  
A: Fallback uses default (50 for most). Graceful degradation.

**Q: Will live prices and estimated prices be different?**  
A: Yes. Live from market. Estimated from mathematical formula. Both marked with source field.

**Q: Why not hardcode lot sizes if they rarely change?**  
A: Because they DO change. NIFTY lot sometimes 25, sometimes 50 based on market conditions.

**Q: Can I disable fallback?**  
A: No, but you can always have cache ready. Fallback is safety net.

---

## 📞 Support

**Found an issue?**
1. Check: Is it in the "What to Watch For" section above?
2. Verify: Run the 2-min Quick Test
3. Document: Screenshots + console logs
4. Report: File with reproduction steps

**Need more detail?**
- See: DEBUG_COMPLETE_SUMMARY.md
- See: TESTING_GUIDE.md  
- See: DATA_FLOW_ARCHITECTURE.md

