# Debug Audit Report: Data Flow Issues in STRADDLE, OPTIONS, WATCHLIST

**Date**: 2026-02-04  
**Status**: CRITICAL ISSUES FOUND

---

## Executive Summary

Three critical issues found across the frontend pages:

1. **Hardcoded lot sizes** in OPTIONS.jsx and STRADDLE.jsx (should come from hook)
2. **Inconsistent fallback logic** - Hook builds skeleton but pages don't handle it properly
3. **LTP not used as fallback** - Pages should fall back to underlying LTP when option data unavailable

---

## Issues by File

### 1. STRADDLE.jsx

#### Issue 1.1: Hardcoded Lot Size
**Location**: Lines 19-20
```jsx
const lotSize = symbol === 'NIFTY' ? 50 : symbol === 'BANKNIFTY' ? 25 : symbol === 'SENSEX' ? 10 : 50;
```
**Problem**: Hardcoded lot size lookup. Should come from hook's `data.lot_size`  
**Impact**: If backend changes lot sizes, UI won't reflect changes  
**Fix**: Use `chainData.lot_size` from hook instead

#### Issue 1.2: Lot Size Fallback
**Location**: Line 89
```jsx
lot_size: chainData.lot_size || lotSize,
```
**Problem**: Falls back to hardcoded value if hook has null  
**Fix**: Ensure hook always returns lot_size (from cache or backend)

#### Issue 1.3: Strike Data Structure Inconsistency
**Location**: Lines 72-101
```jsx
return Object.entries(chainData.strikes)
  .map(([strikeStr, strikeData]) => {
    const strike = parseFloat(strikeStr);
    const ceLtp = strikeData.CE?.ltp || 0;
    const peLtp = strikeData.PE?.ltp || 0;
```
**Problem**: When hook uses fallback (404 response), strikes object may have different structure  
**Impact**: Properties like `ltp` won't exist, causing 0 values everywhere  
**Fix**: Ensure hook standardizes strike data structure before returning

#### Issue 1.4: No Strike Interval Info
**Location**: No reference to `chainData.strike_interval`  
**Problem**: Strike interval (step size) not used. Should be displayed or validated  
**Fix**: Use `chainData.strike_interval` for visual feedback

---

### 2. OPTIONS.jsx

#### Issue 2.1: Hardcoded Lot Size
**Location**: Lines 19-25
```jsx
const getLotSize = (symbol) => {
  switch(symbol) {
    case 'NIFTY': return 50;
    case 'BANKNIFTY': return 25;
    case 'SENSEX': return 10;
    default: return 50;
  }
};
```
**Problem**: Identical issue to STRADDLE.jsx  
**Fix**: Use hook's `getLotSize()` helper instead

#### Issue 2.2: Strike Data Extraction
**Location**: Lines 82-103
```jsx
return Object.entries(chainData.strikes)
  .map(([strikeStr, strikeData]) => {
    const strike = parseFloat(strikeStr);
    return {
      strike,
      isATM: atmStrike && strike === atmStrike,
      ltpCE: strikeData.CE?.ltp || 0,
      ltpPE: strikeData.PE?.ltp || 0,
```
**Problem**: Same structure issue as STRADDLE - fallback data won't have `ltp` properties  
**Fix**: Ensure hook normalizes data structure

#### Issue 2.3: No Strike Interval or ATM Calculation Info
**Location**: Missing display of strike interval  
**Problem**: UI doesn't show strike interval (e.g., "5-point intervals")  
**Fix**: Display `chainData.strike_interval` in header

---

### 3. WATCHLIST.jsx

#### Issue 3.1: No Data Fetch from Hook
**Location**: Lines 1-200 (entire component)
**Problem**: WATCHLIST doesn't use `useAuthoritativeOptionChain` hook at all  
**Impact**: Expiry dates, strike prices not fetched dynamically  
**Fix**: When displaying watchlist items that are options, use hook to fetch their chain data

#### Issue 3.2: Manual Expiry Formatting
**Location**: Lines 10-28 (formatInstrumentDisplay function)
```jsx
const getMonthAbbreviation = (expiryDate) => {
  if (!expiryDate) return '';
  const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', ...];
  const monthIndex = new Date(expiryDate).getMonth();
  return months[monthIndex] || '';
};
```
**Problem**: Expiry dates are formatted locally, not fetched from backend  
**Note**: This is OK for display purposes, but dates should come from backend first

---

### 4. useAuthoritativeOptionChain Hook

#### Issue 4.1: Fallback Doesn't Normalize Strike Data
**Location**: Lines 84-107
```jsx
const strikesMap = {};
strikes.forEach((strike) => {
  const strikeKey = String(strike);
  strikesMap[strikeKey] = {
    strike_price: strike,
    CE: { token: fallbackData?.strikes_ce_pe?.[strikeKey]?.CE || ... },
    PE: { token: fallbackData?.strikes_ce_pe?.[strikeKey]?.PE || ... },
  };
});
```
**Problem**: Fallback builds map with only `token`, not `ltp` or other pricing data  
**Impact**: When fallback is used, all LTP values will be undefined (causing 0 in components)  
**Fix**: Fallback should mark data as "estimated" and return underlying LTP as proxy

#### Issue 4.2: Fallback Returns Incomplete Data
**Location**: Lines 109-119
```jsx
const chainData = {
  underlying,
  expiry,
  lot_size: null,  // ← NULL!
  strike_interval: fallbackData?.strike_step,
  atm_strike: fallbackData?.atm_strike,
  strikes: strikesMap,
};
```
**Problem**: `lot_size` is null in fallback - should get from backend  
**Fix**: Fetch lot size from instruments API

#### Issue 4.3: No LTP Fallback for Individual Options
**Location**: Entire hook
**Problem**: When option data unavailable, should fall back to underlying LTP for estimation  
**Fix**: Add option pricing estimation using ATM + Greeks or show underlying LTP

---

## Summary Table

| File | Issue | Severity | Type |
|------|-------|----------|------|
| STRADDLE.jsx | Hardcoded lot sizes | HIGH | Hardcode |
| STRADDLE.jsx | Fallback data structure mismatch | HIGH | Logic |
| STRADDLE.jsx | No strike interval display | MEDIUM | Missing |
| OPTIONS.jsx | Hardcoded lot sizes | HIGH | Hardcode |
| OPTIONS.jsx | Fallback data structure mismatch | HIGH | Logic |
| OPTIONS.jsx | No strike interval display | MEDIUM | Missing |
| WATCHLIST.jsx | Doesn't use option chain hook | HIGH | Architecture |
| useAuthoritativeOptionChain.js | Fallback doesn't normalize data | CRITICAL | Logic |
| useAuthoritativeOptionChain.js | Fallback lot_size is null | HIGH | Logic |
| useAuthoritativeOptionChain.js | No LTP fallback for options | HIGH | Logic |

---

## Required Fixes (Priority Order)

1. **CRITICAL**: Fix hook fallback to normalize strike data structure (must have `ltp` field)
2. **CRITICAL**: Fix hook fallback to return proper lot_size
3. **HIGH**: Remove hardcoded lot sizes from OPTIONS and STRADDLE
4. **HIGH**: Ensure hook provides fallback pricing (underlying LTP or estimation)
5. **MEDIUM**: Add strike interval display to OPTIONS and STRADDLE headers
6. **MEDIUM**: Consider using hook in WATCHLIST when displaying option chain data

---

## Test Cases

After fixes, verify:

1. ✅ OPTIONS tab shows strikes with real premiums OR underlying LTP as proxy
2. ✅ STRADDLE tab shows straddle premiums OR fallback to underlying LTP sum
3. ✅ Strike intervals display correctly (e.g., "5-point steps")
4. ✅ ATM strike highlighted correctly
5. ✅ All data comes from hook, not hardcoded
6. ✅ Fallback works when API returns 404 or timeout
7. ✅ No hardcoded values (except UI defaults like spinner text)
