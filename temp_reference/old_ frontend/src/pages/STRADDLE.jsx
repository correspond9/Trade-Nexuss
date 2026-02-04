import React, { useState, useEffect, useMemo } from 'react';
import { apiService } from '../services/apiService';

const StraddleMatrix = ({ handleOpenOrderModal, selectedIndex = 'NIFTY 50', expiry = null }) => {
  const [straddles, setStraddles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [indexData, setIndexData] = useState({});
  const [centerStrike, setCenterStrike] = useState(null);
  const [instrumentData, setInstrumentData] = useState({});

  // Convert selectedIndex to symbol for API calls
  const getSymbolFromIndex = (index) => {
    const indexMap = {
      'NIFTY 50': 'NIFTY',
      'BANKNIFTY': 'BANKNIFTY',
      'SENSEX': 'SENSEX'
    };
    return indexMap[index] || 'NIFTY';
  };

  // Get actual instrument data from backend
  const fetchInstrumentData = async (symbol, expiry) => {
    try {
      const response = await apiService.get(`/debug/instrument/${symbol}`);
      if (response && (response.status === 'success' || response.status === 'fallback')) {
        setInstrumentData(prev => ({
          ...prev,
          [symbol]: {
            lotSize: response.lotSize,
            strikeInterval: response.strikeInterval,
            hasOptions: response.hasOptions,
            totalInstruments: response.totalInstruments
          }
        }));
        return response;
      }
    } catch (err) {
      console.warn('Could not fetch instrument data:', err);
    }
    return null;
  };

  // Compute center strike based on lowest straddle premium
  const computeCenterStrike = useMemo(() => {
    const validStraddles = straddles.filter(s => 
      s.ce_ltp > 0 && s.pe_ltp > 0 && s.straddle_premium > 0
    );
    
    if (validStraddles.length === 0) return null;
    
    const lowestPremiumStraddle = validStraddles.reduce((min, current) => 
      current.straddle_premium < min.straddle_premium ? current : min
    );
    
    return lowestPremiumStraddle.strike;
  }, [straddles]);

  // Generate ATM-based strike range (25 strikes around ATM)
  const generateStrikeRange = (centerStrike, strikeInterval) => {
    const strikes = [];
    const numStrikes = 25;
    const halfRange = Math.floor(numStrikes / 2);
    
    for (let i = -halfRange; i <= halfRange; i++) {
      strikes.push(centerStrike + (i * strikeInterval));
    }
    
    return strikes;
  };

  // PRICE AUTHORITY MODEL - STRICT VALIDATION
  const validateUnderlyingPrice = (priceData, symbol) => {
    // Handle new API format: {ltp, timestamp, price_type, instrument_token, source}
    if (!priceData || priceData.ltp === undefined) {
      return { isValid: false, error: 'No price data available', priceType: 'UNKNOWN' };
    }

    const price = priceData.ltp;
    const timestamp = priceData.timestamp ? new Date(priceData.timestamp) : new Date();
    const now = new Date();
    
    // Special handling for market closed scenarios
    if (price === 0 || price === 0.0) {
      // Market is closed, use last close price from initialization
      const lastClosePrices = {
        'NIFTY': 25320.66,
        'BANKNIFTY': 44525.75,
        'SENSEX': 84000.00
      };
      
      const lastClosePrice = lastClosePrices[symbol];
      if (lastClosePrice) {
        return { 
          isValid: true, 
          price: lastClosePrice, 
          priceType: 'LAST_CLOSE',
          timestamp: now,
          source: 'INITIALIZED',
          note: 'Market closed - using initialized last close'
        };
      }
    }
    
    // Check if price is stale (older than 1 trading day)
    const isStale = timestamp && (now - timestamp) > (24 * 60 * 60 * 1000); // 24 hours
    
    // Check if price is within reasonable market range
    const niftyRange = { min: 15000, max: 30000 };
    const bankniftyRange = { min: 20000, max: 55000 };
    const sensexRange = { min: 60000, max: 100000 };
    
    let isValidRange = true;
    let expectedRange = '';
    
    if (symbol === 'NIFTY') {
      isValidRange = price >= niftyRange.min && price <= niftyRange.max;
      expectedRange = `${niftyRange.min}-${niftyRange.max}`;
    } else if (symbol === 'BANKNIFTY') {
      isValidRange = price >= bankniftyRange.min && price <= bankniftyRange.max;
      expectedRange = `${bankniftyRange.min}-${bankniftyRange.max}`;
    } else if (symbol === 'SENSEX') {
      isValidRange = price >= sensexRange.min && price <= sensexRange.max;
      expectedRange = `${sensexRange.min}-${sensexRange.max}`;
    }
    
    if (!isValidRange && price > 0) {
      return { 
        isValid: false, 
        error: `Price ${price} outside expected range ${expectedRange}`, 
        priceType: 'STALE',
        isCorrupted: true
      };
    }
    
    if (isStale && priceData.price_type !== 'LAST_CLOSE' && price > 0) {
      return { 
        isValid: false, 
        error: `Price data stale - timestamp: ${timestamp?.toISOString()}`, 
        priceType: 'STALE'
      };
    }
    
    return { 
      isValid: true, 
      price, 
      priceType: priceData.price_type || (isStale ? 'LAST_CLOSE' : 'LIVE'),
      timestamp,
      source: priceData.source || 'UNKNOWN'
    };
  };

  // Calculate ATM strike based on VALIDATED LTP only
  const calculateATMStrike = (validatedPrice, strikeInterval) => {
    if (!validatedPrice.isValid) {
      throw new Error('Cannot calculate ATM: Invalid underlying price');
    }
    return Math.round(validatedPrice.price / strikeInterval) * strikeInterval;
  };

  // Generate strikes based on VALIDATED ATM calculation only
  const strikeRange = useMemo(() => {
    const currentSymbol = getSymbolFromIndex(selectedIndex);
    const lotSize = instrumentData[currentSymbol]?.lotSize || 50;
    const strikeInterval = instrumentData[currentSymbol]?.strikeInterval || 50;
    
    // PRICE AUTHORITY: Validate underlying price first
    if (!indexData.validatedPrice || !indexData.validatedPrice.isValid) {
      const errorMsg = indexData.validatedPrice?.error || 'Underlying price unavailable or stale';
      console.error('❌ PRICE AUTHORITY VALIDATION FAILED:', errorMsg);
      setError(errorMsg);
      return []; // DO NOT display misleading strikes
    }
    
    try {
      const atmStrike = calculateATMStrike(indexData.validatedPrice, strikeInterval);
      console.log(`✅ PRICE AUTHORITY: ${currentSymbol} LTP=${indexData.validatedPrice.price} (${indexData.validatedPrice.priceType}) → ATM=${atmStrike}`);
      return generateStrikeRange(atmStrike, strikeInterval);
    } catch (error) {
      console.error('❌ ATM CALCULATION FAILED:', error.message);
      setError('Market data syncing… strike list unavailable');
      return [];
    }
  }, [selectedIndex, indexData.validatedPrice, instrumentData]);

  // Fetch straddle data from backend APIs
  useEffect(() => {
    const fetchStraddleData = async () => {
      const currentSymbol = getSymbolFromIndex(selectedIndex);
      
      try {
        setLoading(true);
        setError('');
        
        // Use expiry prop directly
        const actualExpiry = expiry;
        if (!actualExpiry) {
          throw new Error('No expiry dates available');
        }
        
        // Step 1: Fetch instrument data
        const instData = await fetchInstrumentData(currentSymbol, actualExpiry);
        console.log('Instrument data:', instData);
        
        // Step 2: Get straddle chain from backend
        const straddleUrl = `/option-chain-v2/straddles/${currentSymbol}/${actualExpiry}`;
        console.log('🔍 Fetching straddles from:', straddleUrl);
        const straddleResponse = await apiService.get(straddleUrl);
        console.log('🔍 Raw straddle response from API:', straddleResponse);
        
        if (!straddleResponse) {
          console.error('❌ No response from API');
          throw new Error('No response from straddle API');
        }
        
        if (straddleResponse.status !== 'success') {
          console.error('❌ API returned error:', straddleResponse);
          throw new Error(`API error: ${straddleResponse.message || 'Unknown error'}`);
        }
        
        if (!straddleResponse.chain || !Array.isArray(straddleResponse.chain)) {
          console.error('❌ Invalid chain data:', straddleResponse);
          throw new Error('Invalid chain data from API');
        }
        
        console.log(`✅ Received ${straddleResponse.chain.length} straddles`);
        console.log('🔍 First straddle sample:', JSON.stringify(straddleResponse.chain[0], null, 2));
        console.log('🔍 Second straddle sample:', JSON.stringify(straddleResponse.chain[1], null, 2));
        
        if (straddleResponse && straddleResponse.status === 'success') {
          // Process straddle data for frontend
          const processedStraddles = straddleResponse.chain.map(straddle => {
            const ce_ltp = parseFloat(straddle.ce_ltp) || 0;
            const pe_ltp = parseFloat(straddle.pe_ltp) || 0;
            const isValid = ce_ltp > 0 && pe_ltp > 0;
            return {
              strike: straddle.strike,
              ce_ltp: ce_ltp,
              pe_ltp: pe_ltp,
              straddle_premium: parseFloat(straddle.straddle_premium) || 0,
              lot_size: straddle.lot_size,
              ceSymbol: `${currentSymbol}_${straddle.strike}_CE`,
              peSymbol: `${currentSymbol}_${straddle.strike}_PE`,
              timestamp: straddle.timestamp,
              price_source: straddle.price_source,
              isValid: isValid,
              isMarketClosed: straddle.price_source === 'simulated_market_closed'
            };
          });
          
          console.log('🔍 Processed straddles sample:', JSON.stringify(processedStraddles[0], null, 2));
          console.log('🔍 Processed straddles sample 2:', JSON.stringify(processedStraddles[1], null, 2));
          
          // Sort strikes in ascending order
          processedStraddles.sort((a, b) => a.strike - b.strike);
          
          console.log('🔍 Setting straddles state with', processedStraddles.length, 'items');
          console.log('🔍 First item after sort:', JSON.stringify(processedStraddles[0], null, 2));
          setStraddles(processedStraddles);
        } else {
          throw new Error('Failed to fetch straddle chain');
        }
        
        // Step 3: Get index data from AUTHORITATIVE UnderlyingPriceStore API
        try {
          // 🎯 CRITICAL: Use ONLY the authoritative underlying LTP API
          const indexResponse = await apiService.get(`/market/underlying-ltp/${currentSymbol}`);
          if (indexResponse && indexResponse.ltp !== undefined) {
            // PRICE AUTHORITY VALIDATION
            const validatedPrice = validateUnderlyingPrice(indexResponse, currentSymbol);
            
            if (validatedPrice.isCorrupted) {
              console.error('🚨 CACHE CORRUPTION DETECTED:', validatedPrice.error);
              setError('Cache corruption detected - syncing fresh data');
              return;
            }
            
            setIndexData({
              validatedPrice,
              lotSize: instrumentData[currentSymbol]?.lotSize || 50,
            });
            
            console.log(`📊 PRICE AUTHORITY: ${currentSymbol} price=${validatedPrice.price} type=${validatedPrice.priceType} valid=${validatedPrice.isValid}`);
          }
        } catch (indexErr) {
          console.warn('Could not fetch index data:', indexErr);
        }
        
      } catch (err) {
        console.error('Error fetching straddle data:', err);
        setError(`Unable to fetch straddle data: ${err.message || 'Market data not available'}`);
        setStraddles([]);
      } finally {
        setLoading(false);
      }
    };

    fetchStraddleData();
  }, [selectedIndex, expiry]);

  // Update center strike when straddles change
  useEffect(() => {
    setCenterStrike(computeCenterStrike);
  }, [computeCenterStrike]);

  // Generate synthetic straddle data for UI display
  const displayStraddles = useMemo(() => {
    const currentSymbol = getSymbolFromIndex(selectedIndex);
    const lotSize = instrumentData[currentSymbol]?.lotSize || 50;
    
    return strikeRange.map(strike => {
      // Try to find real data first
      const realStraddle = straddles.find(s => Math.abs(s.strike - strike) < 0.01);
      
      if (realStraddle) {
        // Check if we have valid prices (live or cached)
        const hasValidCEPrice = realStraddle.ce_ltp > 0;
        const hasValidPEPrice = realStraddle.pe_ltp > 0;
        const hasValidStraddle = realStraddle.straddle_premium > 0;
        
        return {
          ...realStraddle,
          isValid: hasValidCEPrice && hasValidPEPrice && hasValidStraddle,
          priceSource: realStraddle.price_source || 'cached',
          isMarketClosed: realStraddle.price_source === 'skeleton_fallback' || 
                          (!hasValidCEPrice && !hasValidPEPrice)
        };
      }
      
      // Generate synthetic data for UI testing (only if no real data exists)
      return {
        strike,
        ce_ltp: 0,
        pe_ltp: 0,
        straddle_premium: 0,
        lot_size: lotSize,
        ceSymbol: `${currentSymbol}_${strike}_CE`,
        peSymbol: `${currentSymbol}_${strike}_PE`,
        timestamp: new Date().toISOString(),
        price_source: 'synthetic',
        isValid: false,
        isMarketClosed: false
      };
    });
  }, [strikeRange, straddles, selectedIndex, instrumentData]);

  // Manual refresh function
  const handleRefresh = () => {
    const fetchStraddleData = async () => {
      const currentSymbol = getSymbolFromIndex(selectedIndex);
      
      try {
        setLoading(true);
        setError('');
        
        // Use expiry prop directly
        const actualExpiry = expiry;
        if (!actualExpiry) {
          throw new Error('No expiry dates available');
        }
        
        const straddleResponse = await apiService.get(`/option-chain-v2/straddles/${currentSymbol}/${actualExpiry}`);
        
        if (straddleResponse && straddleResponse.status === 'success') {
          const processedStraddles = straddleResponse.chain.map(straddle => ({
            strike: straddle.strike,
            ce_ltp: straddle.ce_ltp,
            pe_ltp: straddle.pe_ltp,
            straddle_premium: straddle.straddle_premium,
            lot_size: straddle.lot_size,
            ceSymbol: `${currentSymbol}_${straddle.strike}_CE`,
            peSymbol: `${currentSymbol}_${straddle.strike}_PE`,
            timestamp: straddle.timestamp,
            price_source: straddle.price_source
          }));
          
          processedStraddles.sort((a, b) => a.strike - b.strike);
          setStraddles(processedStraddles);
        }
        
      } catch (err) {
        console.error('Error refreshing straddle data:', err);
        setError('Failed to refresh straddle data');
      } finally {
        setLoading(false);
      }
    };

    fetchStraddleData();
  };

  return (
  <div className="flex flex-col h-full bg-white">
    {/* Header with center strike info */}
    <div className="p-3 bg-gray-50 border-b flex justify-between items-center text-xs">
      <div className="flex items-center space-x-2">
        <span className="font-bold">{getSymbolFromIndex(selectedIndex)} Straddles</span>
        {centerStrike && (
          <span className="text-indigo-600 font-semibold">
            Center: {centerStrike}
          </span>
        )}
        {indexData.validatedPrice && indexData.validatedPrice.isValid && (
          <span className="text-green-600 font-bold">
            LTP: {indexData.validatedPrice.price.toFixed(2)}
            {indexData.validatedPrice.priceType === 'LAST_CLOSE' && (
              <span className="text-blue-500 ml-1">(Prev Close)</span>
            )}
          </span>
        )}
        {displayStraddles.some(s => s.isMarketClosed && s.isValid) && (
          <span className="text-blue-500 text-xs">
            Based on previous close
          </span>
        )}
      </div>
      <div className="flex items-center space-x-2">
        <button
          onClick={handleRefresh}
          disabled={loading}
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
    {loading && (
      <div className="flex items-center justify-center p-8">
        <div className="text-gray-500">Loading straddle data...</div>
      </div>
    )}

    {/* Error/Warning state */}
    {error && (
      <div className="flex items-center justify-center p-8">
        <div className={`${error.includes('Unable to fetch') ? 'text-yellow-600' : 'text-red-500'} text-center`}>
          <div className="font-bold">
            {error.includes('Unable to fetch') ? 'Market Data Unavailable' : 'Error'}
          </div>
          <div className="text-sm">{error}</div>
          {error.includes('Unable to fetch') && (
            <div className="text-xs text-gray-500 mt-2">
              {new Date().getHours() >= 9 && new Date().getHours() <= 15 
                ? 'Market is open - trying to fetch live data...' 
                : 'Market is closed - showing last available prices'}
            </div>
          )}
          <button 
            onClick={handleRefresh}
            className="mt-2 px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            Refresh
          </button>
        </div>
      </div>
    )}

    {/* Straddle data */}
    {!loading && !error && (
      <div className="overflow-y-auto flex-grow">
        <div className="flex items-center bg-gray-100 px-2 py-1 text-[10px] sm:text-xs font-bold text-gray-500 uppercase">
          <div className="flex-1 text-left">Strike</div>
          <div className="flex-1 text-center">Trade</div>
          <div className="flex-1 text-right">Straddle Premium</div>
        </div>
        
        {displayStraddles.map((straddle) => {
          const isValidStraddle = straddle.isValid;
          const lotSize = instrumentData[getSymbolFromIndex(selectedIndex)]?.lotSize;
          const displayValue = isValidStraddle ? straddle.straddle_premium.toFixed(2) : 'N/A';
          const isMarketClosed = straddle.isMarketClosed;
          
          // Debug log for first few straddles
          if (straddle.strike <= 24800) {
            console.log(`🔍 Render - Strike: ${straddle.strike}, CE: ${straddle.ce_ltp}, PE: ${straddle.pe_ltp}, isValid: ${isValidStraddle}`);
          }
          
          return (
            <div
              key={straddle.strike}
              className={`flex items-center border-b p-2 text-xs sm:h-10 ${!isValidStraddle ? 'opacity-50' : ''}`}
            >
              <div className="flex-1 text-left text-xs sm:text-xs pr-2">
                <div className="font-semibold">
                  {straddle.strike}
                </div>
                <div className="text-gray-500 text-[10px]">
                {isValidStraddle ? '🟢' : '🔴'} 
                {' CE: ' + (straddle.ce_ltp > 0 ? straddle.ce_ltp.toFixed(2) : 'N/A') + 
                ' | PE: ' + (straddle.pe_ltp > 0 ? straddle.pe_ltp.toFixed(2) : 'N/A')}
                </div>
              </div>
              
              <div className="flex-1 flex justify-center">
                <button
                  onClick={() => {
                    if (!isValidStraddle || !lotSize) return;
                    console.log('BUY straddle clicked for:', straddle.strike);
                    handleOpenOrderModal([
                      {
                        symbol: straddle.ceSymbol,
                        action: 'BUY',
                        ltp: straddle.ce_ltp,
                        lotSize: lotSize,
                      },
                      {
                        symbol: straddle.peSymbol,
                        action: 'BUY',
                        ltp: straddle.pe_ltp,
                        lotSize: lotSize,
                      },
                    ]);
                  }}
                  disabled={!isValidStraddle || !lotSize}
                  className="px-2 py-1 sm:px-3 sm:py-2 text-black text-xs sm:text-[11px] font-bold hover:opacity-90 transition-opacity ring-1 ring-gray-100 hover:ring-gray-300 rounded-md mx-1 my-0 hover:bg-blue-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  BUY
                </button>
                <button
                  onClick={() => {
                    if (!isValidStraddle || !lotSize) return;
                    console.log('SELL straddle clicked for:', straddle.strike);
                    handleOpenOrderModal([
                      {
                        symbol: straddle.ceSymbol,
                        action: 'SELL',
                        ltp: straddle.ce_ltp,
                        lotSize: lotSize,
                      },
                      {
                        symbol: straddle.peSymbol,
                        action: 'SELL',
                        ltp: straddle.pe_ltp,
                        lotSize: lotSize,
                      },
                    ]);
                  }}
                  disabled={!isValidStraddle || !lotSize}
                  className="px-2 py-1 sm:px-3 sm:py-2 text-black text-xs sm:text-[11px] font-bold hover:opacity-90 transition-opacity ring-1 ring-gray-100 hover:ring-gray-300 rounded-md mx-1 my-0 hover:bg-orange-600 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  SELL
                </button>
              </div>
              
              <div className="flex-1 text-right font-bold text-black text-xs sm:text-xs pl-2">
                <div>
                  {displayValue}
                </div>
                {!isValidStraddle && (
                  <div className="text-[10px] text-red-500">
                    {straddle.price_source === 'synthetic' ? 'No data available' : 'Invalid prices'}
                  </div>
                )}
                {isMarketClosed && isValidStraddle && (
                  <div className="text-[10px] text-blue-500">
                    Based on previous close
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {displayStraddles.length === 0 && !loading && (
          <div className="flex items-center justify-center p-8 text-gray-500">
            {error ? 'No straddle data available due to error' : 'No straddle data available'}
          </div>
        )}
      </div>
    )}
  </div>
);
};

export default StraddleMatrix;
