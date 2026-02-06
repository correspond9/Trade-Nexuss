import React, { useState, useEffect } from 'react';
import { useAuthoritativeOptionChain } from '../hooks/useAuthoritativeOptionChain';
import normalizeUnderlying from '../utils/underlying';

const Options = ({ handleOpenOrderModal, selectedIndex = 'NIFTY 50', expiry }) => {
  const [underlyingPrice, setUnderlyingPrice] = useState(null);
  const [strikeInterval, setStrikeInterval] = useState(null);

  // Convert selectedIndex to symbol for API calls
  const symbol = normalizeUnderlying(selectedIndex);
  const resolveOptionSegment = (underlyingSymbol) => {
    const upper = String(underlyingSymbol || '').toUpperCase();
    if (upper === 'SENSEX' || upper === 'BANKEX') {
      return 'BSE_FNO';
    }
    return 'NSE_FNO';
  };

  // ✨ Use the authoritative hook to fetch realtime cached data
  const {
    data: chainData,
    loading: chainLoading,
    error: chainError,
    strikeCount,
    refresh: refreshChain,
    getATMStrike,
  } = useAuthoritativeOptionChain(symbol, expiry, {
    autoRefresh: true,
    refreshInterval: 1000, // 1 second real-time updates
  });

  // Get lot size from hook (never hardcoded)
  const getLotSize = () => chainData?.lot_size || 50;

  // Fetch underlying price for display
  useEffect(() => {
    const fetchPrice = async () => {
      try {
        const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
        const response = await fetch(`${baseUrl}/market/underlying-ltp/${symbol}`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.ltp) {
            setUnderlyingPrice(data.ltp);
          }
        }
      } catch (err) {
        console.warn(`[OPTIONS] Could not fetch underlying price for ${symbol}:`, err);
      }
    };

    if (symbol) {
      fetchPrice();
    }
  }, [symbol]);

  // Extract strike interval from hook data
  useEffect(() => {
    if (chainData?.strike_interval) {
      setStrikeInterval(chainData.strike_interval);
      console.log(`📏 [OPTIONS] Strike Interval: ${chainData.strike_interval}`);
    }
  }, [chainData?.strike_interval]);

  // Convert authoritative chain data to strike format
  const strikes = React.useMemo(() => {
    if (!chainData || !chainData.strikes) {
      return [];
    }

    const atmStrike = getATMStrike();
    const lotSize = getLotSize();

    return Object.entries(chainData.strikes)
      .map(([strikeStr, strikeData]) => {
        const strike = parseFloat(strikeStr);
        return {
          strike,
          isATM: atmStrike && strike === atmStrike,
          ltpCE: strikeData.CE?.ltp || 0,
          ltpPE: strikeData.PE?.ltp || 0,
          bidCE: strikeData.CE?.bid || 0,
          askCE: strikeData.CE?.ask || 0,
          bidPE: strikeData.PE?.bid || 0,
          askPE: strikeData.PE?.ask || 0,
          depthCE: strikeData.CE?.depth || null,
          depthPE: strikeData.PE?.depth || null,
          ceToken: strikeData.CE?.token || null,
          peToken: strikeData.PE?.token || null,
          ceGreeks: strikeData.CE?.greeks || {},
          peGreeks: strikeData.PE?.greeks || {},
          ceSource: strikeData.CE?.source || 'live',
          peSource: strikeData.PE?.source || 'live',
          lotSize: lotSize,
        };
      })
      .sort((a, b) => a.strike - b.strike);
  }, [chainData, getATMStrike]);

  const atmStrike = getATMStrike();

  // Manual refresh
  const handleRefresh = () => {
    refreshChain();
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="p-3 bg-gray-50 border-b flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <h3 className="font-semibold text-gray-800">{symbol} OPTIONS</h3>
          {underlyingPrice && (
            <span className="text-xs text-gray-600 font-medium">
              LTP: {underlyingPrice.toFixed(2)}
            </span>
          )}
          {getATMStrike() && (
            <span className="text-xs text-green-600 font-medium">
              ATM: {getATMStrike()}
            </span>
          )}
          {strikeInterval && (
            <span className="text-xs text-purple-600 font-medium">
              Step: {strikeInterval}
            </span>
          )}
          {getLotSize() && (
            <span className="text-xs text-blue-600 font-medium">
              Lot: {getLotSize()}
            </span>
          )}
          {strikeCount > 0 && (
            <span className="text-xs text-gray-500">
              ({strikeCount} strikes)
            </span>
          )}
          {expiry && (
            <span className="text-xs text-orange-600 font-medium">
              Exp: {expiry}
            </span>
          )}
        </div>
        <button
          onClick={handleRefresh}
          disabled={chainLoading}
          className="p-1 hover:bg-gray-200 rounded transition-colors disabled:opacity-50"
          title="Refresh data"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Options Matrix */}
      <div className="overflow-y-auto flex-grow">
        {/* Loading State */}
        {chainLoading && !strikes.length && (
          <div className="m-2 p-3 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm text-center">
            <div className="animate-spin inline-block mr-2">⚙️</div>
            Loading option chain...
          </div>
        )}

        {/* Error State */}
        {chainError && !strikes.length && (
          <div className="m-2 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm text-center">
            <strong>Error:</strong> {chainError}
            <button 
              onClick={handleRefresh}
              className="ml-2 px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700"
            >
              Retry
            </button>
          </div>
        )}
        
        {/* No Data State */}
        {!chainLoading && !chainError && strikes.length === 0 && (
          <div className="m-2 p-3 bg-yellow-50 border border-yellow-200 rounded text-yellow-700 text-sm text-center">
            {expiry ? 'No strikes available for this expiry.' : 'Select an expiry date to view options.'}
          </div>
        )}
        
        {/* Column Headers */}
        {strikes.length > 0 && (
          <div className="grid grid-cols-3 bg-gray-100 p-2 text-xs font-bold text-gray-500 uppercase sticky top-0 z-10">
            <div className="text-left">CE Premium</div>
            <div className="text-center">Strike</div>
            <div className="text-right">PE Premium</div>
          </div>
        )}

        {/* Strike Rows */}
        {strikes.map((strikeData) => (
          <div
            key={strikeData.strike}
            className={`grid grid-cols-3 p-2 border-b items-center text-xs ${
              strikeData.isATM ? 'bg-indigo-50 font-bold' : 'bg-white hover:bg-gray-50'
            }`}
          >
            {/* CE Premium Column - Left */}
            <div className="flex items-center justify-between pr-2">
              <span className="text-sm font-semibold text-gray-900">
                {strikeData.ltpCE > 0 ? strikeData.ltpCE.toFixed(2) : '0.00'}
              </span>
            <div className="flex space-x-1 ml-2">
                <button
                  onClick={() => {
                    if (strikeData.ltpCE <= 0) return;
                    handleOpenOrderModal([{
                      symbol: `${symbol} ${strikeData.strike} CE`,
                      action: 'BUY',
                      ltp: strikeData.ltpCE,
                      lotSize: strikeData.lotSize,
                      security_id: strikeData.ceToken,
                      exchange_segment: resolveOptionSegment(symbol),
                      bid: strikeData.bidCE,
                      ask: strikeData.askCE,
                      strike: strikeData.strike,
                      optionType: 'CE',
                      depth: strikeData.depthCE,
                      expiry,
                    }]);
                  }}
                  disabled={strikeData.ltpCE <= 0}
                  className="px-2 py-1 text-xs font-semibold bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Buy CE"
                >
                  B
                </button>
                <button
                  onClick={() => {
                    if (strikeData.ltpCE <= 0) return;
                    handleOpenOrderModal([{
                      symbol: `${symbol} ${strikeData.strike} CE`,
                      action: 'SELL',
                      ltp: strikeData.ltpCE,
                      lotSize: strikeData.lotSize,
                      security_id: strikeData.ceToken,
                      exchange_segment: resolveOptionSegment(symbol),
                      bid: strikeData.bidCE,
                      ask: strikeData.askCE,
                      strike: strikeData.strike,
                      optionType: 'CE',
                      depth: strikeData.depthCE,
                      expiry,
                    }]);
                  }}
                  disabled={strikeData.ltpCE <= 0}
                  className="px-2 py-1 text-xs font-semibold bg-red-500 text-white rounded hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Sell CE"
                >
                  S
                </button>
              </div>
            </div>

            {/* Strike Column - Center */}
            <div className="flex items-center justify-center">
              <span className="text-sm font-bold text-gray-900">
                {strikeData.strike}
              </span>
            </div>

            {/* PE Premium Column - Right */}
            <div className="flex items-center justify-between pl-2">
              <div className="flex space-x-1 mr-2">
                <button
                  onClick={() => {
                    if (strikeData.ltpPE <= 0) return;
                    handleOpenOrderModal([{
                      symbol: `${symbol} ${strikeData.strike} PE`,
                      action: 'BUY',
                      ltp: strikeData.ltpPE,
                      lotSize: strikeData.lotSize,
                      security_id: strikeData.peToken,
                      exchange_segment: resolveOptionSegment(symbol),
                      bid: strikeData.bidPE,
                      ask: strikeData.askPE,
                      strike: strikeData.strike,
                      optionType: 'PE',
                      depth: strikeData.depthPE,
                      expiry,
                    }]);
                  }}
                  disabled={strikeData.ltpPE <= 0}
                  className="px-2 py-1 text-xs font-semibold bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Buy PE"
                >
                  B
                </button>
                <button
                  onClick={() => {
                    if (strikeData.ltpPE <= 0) return;
                    handleOpenOrderModal([{
                      symbol: `${symbol} ${strikeData.strike} PE`,
                      action: 'SELL',
                      ltp: strikeData.ltpPE,
                      lotSize: strikeData.lotSize,
                      security_id: strikeData.peToken,
                      exchange_segment: resolveOptionSegment(symbol),
                      bid: strikeData.bidPE,
                      ask: strikeData.askPE,
                      strike: strikeData.strike,
                      optionType: 'PE',
                      depth: strikeData.depthPE,
                      expiry,
                    }]);
                  }}
                  disabled={strikeData.ltpPE <= 0}
                  className="px-2 py-1 text-xs font-semibold bg-red-500 text-white rounded hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Sell PE"
                >
                  S
                </button>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {strikeData.ltpPE > 0 ? strikeData.ltpPE.toFixed(2) : '0.00'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Options;