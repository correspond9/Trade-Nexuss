import React, { useState, useEffect, useMemo, useRef } from 'react';
import { apiService } from '../services/apiService';
import { useAuthoritativeOptionChain } from '../hooks/useAuthoritativeOptionChain';
import normalizeUnderlying from '../utils/underlying';
import { getLotSize as getConfiguredLotSize } from '../config/tradingConfig';

const StraddleMatrix = ({ handleOpenOrderModal, selectedIndex = 'NIFTY 50', expiry = null }) => {
  const [centerStrike, setCenterStrike] = useState(null);
  const [underlyingPrice, setUnderlyingPrice] = useState(null);
  const [snapshotStrikes, setSnapshotStrikes] = useState([]);
  const listRef = useRef(null);
  const didInitialScroll = useRef(false);

  // Convert selectedIndex to symbol for API calls
  // Get symbol
  const symbol = normalizeUnderlying(selectedIndex);
  
  // ✨ Use the authoritative hook to fetch realtime cached data
  const {
    data: chainData,
    loading: chainLoading,
    error: chainError,
    refresh: refreshChain,
  } = useAuthoritativeOptionChain(symbol, expiry, {
    autoRefresh: true,
    refreshInterval: 1000, // 1 second real-time updates
  });

  // Fetch underlying price for center strike calculation
  useEffect(() => {
    const fetchUnderlyingPrice = async () => {
      try {
        const response = await apiService.get(`/market/underlying-ltp/${symbol}`);
        if (response && response.ltp !== undefined) {
          setUnderlyingPrice(response.ltp);
          console.log(`📊 [STRADDLE] ${symbol} LTP: ${response.ltp}`);
        }
      } catch (err) {
        console.warn(`[STRADDLE] Could not fetch underlying price for ${symbol}:`, err);
      }
    };

    if (symbol) {
      fetchUnderlyingPrice();
    }
  }, [symbol]);

  // STRADDLE ATM RULE:
  // Prefer authoritative ATM from cache; fallback to min CE+PE when ATM is missing.
  const straddleAtmStrike = useMemo(() => {
    if (chainData?.atm_strike) {
      return chainData.atm_strike;
    }
    if (!chainData?.strikes) {
      return null;
    }

    let bestStrike = null;
    let bestPremium = null;

    Object.entries(chainData.strikes).forEach(([strikeStr, strikeData]) => {
      const strike = parseFloat(strikeStr);
      const ce = strikeData.CE?.ltp || 0;
      const pe = strikeData.PE?.ltp || 0;
      if (strike <= 0 || ce <= 0 || pe <= 0) return;

      const straddle = ce + pe;
      if (bestPremium === null || straddle < bestPremium) {
        bestPremium = straddle;
        bestStrike = strike;
      }
    });

    return bestStrike;
  }, [chainData]);

  // Compute center strike from straddle ATM (exclusive logic for this tab)
  useEffect(() => {
    if (straddleAtmStrike) {
      setCenterStrike(straddleAtmStrike);
      console.log(`📍 [STRADDLE] Center strike (ATM): ${straddleAtmStrike}`);
    }
  }, [straddleAtmStrike]);

  // Fallback snapshot loader when authoritative chain is unavailable
  useEffect(() => {
    const loadSnapshot = async () => {
      try {
        // Try v2-style builder: /option-chain/{symbol}?expiry=...&underlying_ltp=...
        if (underlyingPrice) {
          const res2 = await apiService.get(`/option-chain/${symbol}`, {
            expiry: expiry,
            underlying_ltp: underlyingPrice,
          });
          const payload2 = res2?.chain || res2?.data || res2;
          const arr2 = Array.isArray(payload2) ? payload2 : [];
          const normalized = arr2.map((item) => ({
            strike: Number(item.strike || item.strike_price || 0),
            ltpCE: Number(
              item?.ce?.ltp ??
              item?.CE?.ltp ??
              item?.ce?.close ??
              item?.CE?.close ??
              item?.ce?.last_price ??
              item?.CE?.last_price ??
              0
            ),
            ltpPE: Number(
              item?.pe?.ltp ??
              item?.PE?.ltp ??
              item?.pe?.close ??
              item?.PE?.close ??
              item?.pe?.last_price ??
              item?.PE?.last_price ??
              0
            ),
          }));
          if (normalized.length) {
            setSnapshotStrikes(normalized);
            console.log('[STRADDLE] Loaded snapshot from /option-chain builder', symbol, normalized.length);
            return;
          }
        }
        setSnapshotStrikes([]);
      } catch (e) {
        console.log('[STRADDLE] Snapshot load failed', symbol, e?.message || e);
        setSnapshotStrikes([]);
      }
    };
    loadSnapshot();
  }, [symbol, expiry, underlyingPrice]);

  // Convert authoritative chain data to straddle format
  const straddles = useMemo(() => {
    if (!chainData || !chainData.strikes) {
      if (snapshotStrikes.length) {
        const configuredLot = getConfiguredLotSize(symbol);
        const lotSize = chainData?.lot_size && chainData.lot_size > 0 ? chainData.lot_size : configuredLot;
        return snapshotStrikes
          .map((s) => {
            const strike = Number(s.strike);
            const ceLtp = Number(s.ltpCE || 0);
            const peLtp = Number(s.ltpPE || 0);
            const hasCe = ceLtp > 0;
            const hasPe = peLtp > 0;
            const isDisplayValid = hasCe || hasPe;
            const isTradeReady = hasCe && hasPe;
            return {
              strike,
              isATM: false,
              ce_ltp: ceLtp,
              pe_ltp: peLtp,
              straddle_premium: (ceLtp + peLtp).toFixed(2),
              lot_size: lotSize,
              ceSymbol: `${symbol}_${strike}_CE`,
              peSymbol: `${symbol}_${strike}_PE`,
              ceToken: null,
              peToken: null,
              timestamp: new Date().toISOString(),
              price_source: 'snapshot',
              isValid: isDisplayValid,
              trade_ready: isTradeReady,
            };
          })
          .sort((a, b) => a.strike - b.strike);
      }
      return [];
    }

    const atmStrike = straddleAtmStrike;
    const configuredLot = getConfiguredLotSize(symbol);
    const lotSize = chainData?.lot_size && chainData.lot_size > 0 ? chainData.lot_size : configuredLot;
    const snapshotMap = Object.fromEntries(
      (snapshotStrikes || []).map((s) => [Number(s.strike), s])
    );

    return Object.entries(chainData.strikes)
      .map(([strikeStr, strikeData]) => {
        const strike = parseFloat(strikeStr);
        let ceLtp = Number(
          strikeData.CE?.ltp ??
          strikeData.CE?.close ??
          strikeData.CE?.last_price ??
          0
        );
        let peLtp = Number(
          strikeData.PE?.ltp ??
          strikeData.PE?.close ??
          strikeData.PE?.last_price ??
          0
        );
        if (ceLtp <= 0 && snapshotMap[strike]?.ltpCE) {
          ceLtp = Number(snapshotMap[strike].ltpCE);
        }
        if (peLtp <= 0 && snapshotMap[strike]?.ltpPE) {
          peLtp = Number(snapshotMap[strike].ltpPE);
        }
        const hasCe = ceLtp > 0;
        const hasPe = peLtp > 0;
        const isDisplayValid = hasCe || hasPe;
        const isTradeReady = hasCe && hasPe;
        
        return {
          strike,
          isATM: atmStrike && strike === atmStrike,
          ce_ltp: ceLtp,
          pe_ltp: peLtp,
          straddle_premium: (ceLtp + peLtp).toFixed(2),
          lot_size: lotSize, // From hook, not hardcoded
          ceSymbol: `${symbol}_${strike}_CE`,
          peSymbol: `${symbol}_${strike}_PE`,
          ceToken: strikeData.CE?.token,
          peToken: strikeData.PE?.token,
          timestamp: new Date().toISOString(),
          price_source: (strikeData.CE?.source || 'live_cache') + (snapshotMap[strike] ? '|snapshot_merge' : ''),
          isValid: isDisplayValid,
          trade_ready: isTradeReady,
        };
      })
      .sort((a, b) => a.strike - b.strike);
  }, [chainData, symbol, straddleAtmStrike, snapshotStrikes]);

  const displayedStraddles = useMemo(() => {
    if (!straddles.length) return [];
    const strikesSorted = straddles.map(s => s.strike).sort((a, b) => a - b);
    const atm = centerStrike ?? (straddleAtmStrike || null);
    if (atm == null) return straddles;
    let centerIdx = strikesSorted.findIndex(v => v === atm);
    if (centerIdx < 0) {
      let nearest = 0;
      let minDiff = Infinity;
      strikesSorted.forEach((v, i) => {
        const d = Math.abs(v - atm);
        if (d < minDiff) {
          minDiff = d;
          nearest = i;
        }
      });
      centerIdx = nearest;
    }
    const total = 31;
    let start = Math.max(0, centerIdx - 15);
    let end = start + total - 1;
    if (end > strikesSorted.length - 1) {
      end = strikesSorted.length - 1;
      start = Math.max(0, end - total + 1);
    }
    const allowed = new Set(strikesSorted.slice(start, end + 1));
    return straddles.filter(s => allowed.has(s.strike));
  }, [straddles, centerStrike, straddleAtmStrike]);

  useEffect(() => {
    if (didInitialScroll.current) return;
    const el = listRef.current;
    if (!el) return;
    const atmEl = el.querySelector('[data-atm="true"]');
    if (!atmEl) return;
    const elRect = el.getBoundingClientRect();
    const rowRect = atmEl.getBoundingClientRect();
    const delta = rowRect.top - elRect.top;
    const target = el.scrollTop + delta - (el.clientHeight / 2) + (atmEl.clientHeight / 2);
    el.scrollTo({ top: Math.max(target, 0), behavior: 'smooth' });
    didInitialScroll.current = true;
  }, [displayedStraddles]);

  // Manual refresh
  const handleRefresh = () => {
    refreshChain();
  };

  return (
  <div className="flex flex-col h-full bg-white">
    {/* Header with center strike info */}
    <div className="p-3 bg-gray-50 border-b flex justify-between items-center text-xs">
      <div className="flex items-center space-x-2">
        <span className="font-bold">{symbol} Straddles</span>
        {centerStrike && (
          <span className="text-indigo-600 font-semibold">
            ATM: {centerStrike}
          </span>
        )}
        {underlyingPrice && (
          <span className="text-green-600 font-bold">
            LTP: {underlyingPrice.toFixed(2)}
          </span>
        )}
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={handleRefresh}
          disabled={chainLoading}
          className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
          title="Refresh data"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    {/* Loading state */}
    {chainLoading && !straddles.length && (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">
          <div className="animate-spin inline-block mr-2">⚙️</div>
          Loading straddle data...
        </div>
      </div>
    )}

    {/* Error state */}
    {chainError && !straddles.length && (
      <div className="flex items-center justify-center p-8">
        <div className="text-red-500 text-center">
          <div className="font-bold">Unable to Load</div>
          <div className="text-sm">{chainError}</div>
          <button 
            onClick={handleRefresh}
            className="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            Retry
          </button>
        </div>
      </div>
    )}

    {/* Straddle data */}
    {displayedStraddles.length > 0 && (
      <div className="overflow-y-auto flex-grow" ref={listRef} style={{ maxHeight: '640px' }}>
        <div className="flex items-center bg-gray-100 px-2 py-1 text-[10px] sm:text-xs font-bold text-gray-500 uppercase sticky top-0 z-10">
          <div className="flex-1 text-left">Strike</div>
          <div className="flex-1 text-center">Trade</div>
          <div className="flex-1 text-right">Premium</div>
        </div>
        
        {displayedStraddles.map((straddle) => {
          const isValidStraddle = straddle.isValid;
          const isTradeReady = straddle.trade_ready;
          const displayValue = isValidStraddle ? parseFloat(straddle.straddle_premium).toFixed(2) : '0.00';
          
          return (
            <div
              key={straddle.strike}
              data-atm={straddle.isATM ? 'true' : 'false'}
              className={`flex items-center border-b p-2 text-xs h-10 sm:h-10 ${
                straddle.isATM ? 'bg-indigo-50 font-bold' : ''
              } ${!isValidStraddle ? 'opacity-50' : ''}`}
            >
              <div className="flex-1 text-left text-xs sm:text-xs pr-2">
                <div className="font-semibold">
                  {straddle.strike} {straddle.isATM ? ' (ATM)' : ''}
                </div>
                <div className="text-gray-500 text-[10px]">
                  {isValidStraddle ? '🟢' : '🔴'} 
                  {' CE: ' + (straddle.ce_ltp > 0 ? straddle.ce_ltp.toFixed(2) : '0.00') + 
                   ' | PE: ' + (straddle.pe_ltp > 0 ? straddle.pe_ltp.toFixed(2) : '0.00')}
                </div>
              </div>
              
              <div className="flex-1 flex justify-center">
                <button
                  onClick={() => {
                    if (!isTradeReady) return;
                    handleOpenOrderModal([
                      {
                        symbol: straddle.ceSymbol,
                        action: 'BUY',
                        ltp: straddle.ce_ltp,
                        lotSize: straddle.lot_size,
                        underlying: symbol,
                      },
                      {
                        symbol: straddle.peSymbol,
                        action: 'BUY',
                        ltp: straddle.pe_ltp,
                        lotSize: straddle.lot_size,
                        underlying: symbol,
                      },
                    ]);
                  }}
                  disabled={!isTradeReady}
                  className="px-2 py-1 sm:px-3 sm:py-2 text-black text-xs sm:text-[11px] font-bold hover:opacity-90 transition-opacity ring-1 ring-gray-100 hover:ring-gray-300 rounded-md mx-1 my-0 hover:bg-blue-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  BUY
                </button>
                <button
                  onClick={() => {
                    if (!isTradeReady) return;
                    handleOpenOrderModal([
                      {
                        symbol: straddle.ceSymbol,
                        action: 'SELL',
                        ltp: straddle.ce_ltp,
                        lotSize: straddle.lot_size,
                        underlying: symbol,
                      },
                      {
                        symbol: straddle.peSymbol,
                        action: 'SELL',
                        ltp: straddle.pe_ltp,
                        lotSize: straddle.lot_size,
                        underlying: symbol,
                      },
                    ]);
                  }}
                  disabled={!isTradeReady}
                  className="px-2 py-1 sm:px-3 sm:py-2 text-black text-xs sm:text-[11px] font-bold hover:opacity-90 transition-opacity ring-1 ring-gray-100 hover:ring-gray-300 rounded-md mx-1 my-0 hover:bg-orange-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  SELL
                </button>
              </div>
              
              <div className="flex-1 text-right font-bold text-black text-xs sm:text-xs pl-2">
                <div>{displayValue}</div>
                {!isValidStraddle && (
                  <div className="text-[10px] text-red-500">No data</div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    )}

    {/* No data state */}
    {!chainLoading && !chainError && straddles.length === 0 && (
      <div className="flex items-center justify-center p-8 text-gray-500">
        No straddle data available
      </div>
    )}
  </div>
);
};

export default StraddleMatrix;
