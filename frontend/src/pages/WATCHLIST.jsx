import React, { useState, useEffect, useCallback, useMemo } from 'react';
import apiService from '../services/apiService';
import { authService } from '../services/authService';

// HUMAN-READABLE INSTRUMENT DISPLAY FORMATTING
// PRESENTATION LAYER ONLY - Canonical data remains unchanged
const formatInstrumentDisplay = (instrument) => {
  const { symbol, instrumentType, expiry, strike } = instrument;

  // Extract month from expiry (2026-01-29 → JAN)
  const getMonthAbbreviation = (expiryDate) => {
    if (!expiryDate) return '';
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
      'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const monthIndex = new Date(expiryDate).getMonth();
    return months[monthIndex] || '';
  };

  // Extract day from expiry (2026-01-29 → 29)
  const getDayNumber = (expiryDate) => {
    if (!expiryDate) return '';
    return new Date(expiryDate).getDate();
  };

  const month = getMonthAbbreviation(expiry);
  const day = getDayNumber(expiry);

  // PRIMARY DISPLAY TEXT (MANDATORY FORMAT)
  let primaryDisplay = '';

  if (instrumentType === 'FUT') {
    // FOR FUTURES: <UNDERLYING> FUT <MONTH>
    primaryDisplay = `${symbol} FUT ${month}`;
  } else if (instrumentType === 'CE' || instrumentType === 'PE') {
    // FOR OPTIONS: <UNDERLYING> <MONTH> <STRIKE> <CE/PE>
    primaryDisplay = `${symbol} ${month} ${strike || ''} ${instrumentType}`;
  } else {
    // For INDEX or STOCK: just the symbol
    primaryDisplay = symbol;
  }

  // SUBTEXT (MANDATORY): <DD> <MON>
  const subtext = expiry ? `${day} ${month}` : '';

  return {
    primaryDisplay,
    subtext
  };
};

const WatchlistComponent = ({ handleOpenOrderModal }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedWatchlist, setSelectedWatchlist] = useState(1);
  const [watchlists, setWatchlists] = useState({ 1: [], 2: [], 3: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchResults, setSearchResults] = useState([]);

  const getBaseUrl = () => import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';

  const getUnderlyingLtp = async (symbol) => {
    try {
      const ltpUrl = `${getBaseUrl()}/market/underlying-ltp/${symbol}`;
      const ltpResponse = await fetch(ltpUrl);
      if (ltpResponse.ok) {
        const ltpData = await ltpResponse.json();
        return ltpData.ltp || ltpData.data?.ltp || null;
      }
    } catch (err) {
      console.warn('[WATCHLIST] Failed to fetch underlying LTP:', err);
    }
    return null;
  };

  const isIndexSymbol = (symbol) => {
    const indexSet = new Set(['NIFTY', 'BANKNIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY', 'BANKEX']);
    return indexSet.has((symbol || '').toUpperCase());
  };

  // Add instrument to current watchlist (subscribe if on-demand)
  const addToWatchlist = useCallback(async (instrument) => {
    const currentList = watchlists[selectedWatchlist] || [];

    // Check if instrument already exists in watchlist
    const exists = currentList.some(item =>
      item.id === instrument.id && item.exchange === instrument.exchange
    );

    if (exists) {
      setError('Instrument already exists in watchlist');
      setTimeout(() => setError(''), 3000);
      return;
    }

    try {
      // If already subscribed (Tier B), just add locally
      if (instrument.isSubscribed) {
        setWatchlists(prev => ({
          ...prev,
          [selectedWatchlist]: [...currentList, instrument]
        }));
      } else {
        if (!instrument.expiry) {
          throw new Error('No expiry available for this instrument');
        }
        const instrumentType = isIndexSymbol(instrument.symbol) ? 'INDEX_OPTION' : 'STOCK_OPTION';
        const underlyingLtp = await getUnderlyingLtp(instrument.symbol);

        const payload = {
          user_id: 1,
          symbol: instrument.symbol,
          expiry: instrument.expiry,
          instrument_type: instrumentType,
          underlying_ltp: underlyingLtp
        };

        const response = await fetch(`${getBaseUrl()}/watchlist/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const data = await response.json().catch(() => ({}));
          throw new Error(data?.detail || 'Failed to add to watchlist');
        }

        setWatchlists(prev => ({
          ...prev,
          [selectedWatchlist]: [...currentList, instrument]
        }));
      }

      // Clear search after adding
      setSearchTerm('');
      setSearchResults([]);

      // Show success message
      setError('Instrument added to watchlist successfully!');
      setTimeout(() => setError(''), 2000);
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      setError(err.message || 'Failed to add instrument to watchlist');
      setTimeout(() => setError(''), 2000);
    }
  }, [watchlists, selectedWatchlist]);

  // Remove instrument from watchlist
  const removeFromWatchlist = useCallback(async (instrumentId, exchange) => {
    const currentList = watchlists[selectedWatchlist] || [];
    const updatedList = currentList.filter(item =>
      !(item.id === instrumentId && item.exchange === exchange)
    );

    try {
      // Remove from watchlist via API
      const foundItem = currentList.find(item => item.id === instrumentId);
      const payload = {
        user_id: 1,
        symbol: foundItem?.symbol || '',
        expiry: foundItem?.expiry || ''
      };

      await fetch(`${getBaseUrl()}/watchlist/remove`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      // Update local state
      setWatchlists(prev => ({
        ...prev,
        [selectedWatchlist]: updatedList
      }));

      // Show success message
      setError('Instrument removed from watchlist');
      setTimeout(() => setError(''), 2000);
    } catch (err) {
      console.error('Error removing from watchlist:', err);
      setError('Failed to remove instrument from watchlist');
      setTimeout(() => setError(''), 2000);
    }
  }, [watchlists, selectedWatchlist]);

  // Fetch available instruments from live API
  const fetchInstruments = useCallback(async (exchange, searchText = '') => {
    try {
      setError('');

      // Use FastAPI market instruments endpoint
      const response = await apiService.get('/market/instruments/' + exchange, {
        search: searchText,
        limit: 50
      });

      if (response && response.data) {
        return response.data.map(instrument => {
          // Calculate human-readable display formatting
          const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);

          return {
            // === CANONICAL DATA (unchanged) ===
            id: instrument.instrumentId,
            symbol: instrument.symbol,
            name: instrument.displayName || instrument.symbol,
            exchange: instrument.exchange || exchange,
            ltp: instrument.ltp || 0,
            change: instrument.change || 0,
            changePercent: instrument.changePercent || 0,
            lotSize: instrument.lotSize || 1,
            instrumentType: instrument.instrumentType || 'EQ',
            strike: instrument.strike,
            optionType: instrument.instrumentType, // CE/PE
            expiry: instrument.expiry,

            // === UI-ONLY FORMATTED DISPLAY FIELDS ===
            primaryDisplay,  // "NIFTY JAN 25200 CE" or "NIFTY FUT JAN"
            subtext,        // "29 Jan"
          };
        });
      }

      console.warn(`No data received from API for ${exchange}`);
      return [];
    } catch (err) {
      console.error(`Error fetching instruments from ${exchange}:`, err);

      // More specific error messages - only show for critical errors
      if (err.message.includes('Invalid openalgo apikey')) {
        setError('Invalid API key. Please check configuration.');
      } else if (err.message.includes('Failed to fetch') && exchange === 'MCX') {
        // Don't show error for MCX, just log it
        console.warn('MCX data temporarily unavailable');
      } else if (err.message.includes('Failed to fetch') && exchange === 'NSE_INDEX') {
        // Don't show error for NSE_INDEX, just log it
        console.warn('Index data temporarily unavailable');
      } else if (err.message.includes('Failed to fetch')) {
        // Only show error for other critical exchanges
        setError(`Failed to load ${exchange} data. Please try again.`);
      } else {
        // Don't show generic errors to avoid spam
        console.warn(`Error loading ${exchange} data:`, err.message);
      }

      return [];
    }
  }, []);

  const fetchTierBSuggestions = useCallback(async (searchText) => {
    try {
      const url = `${getBaseUrl()}/subscriptions/search?q=${encodeURIComponent(searchText)}&tier=TIER_B&limit=20`;
      const response = await fetch(url);
      if (!response.ok) return [];
      const data = await response.json();
      return (data.results || []).map((sub) => {
        const instrument = {
          symbol: sub.symbol,
          instrumentType: sub.option_type || 'EQUITY',
          expiry: sub.expiry,
          strike: sub.strike,
        };
        const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);
        return {
          id: sub.token,
          symbol: sub.symbol,
          exchange: sub.exchange || 'NSE',
          instrumentType: sub.option_type || 'EQUITY',
          expiry: sub.expiry,
          strike: sub.strike,
          lotSize: sub.lot_size || 1,
          ltp: 0,
          change: 0,
          changePercent: 0,
          primaryDisplay,
          subtext,
          tier: 'TIER_B',
          isSubscribed: true,
        };
      });
    } catch (err) {
      console.warn('[WATCHLIST] Tier B suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const fetchTierASuggestions = useCallback(async (searchText) => {
    try {
      const url = `${getBaseUrl()}/instruments/search?q=${encodeURIComponent(searchText)}&limit=10`;
      const response = await fetch(url);
      if (!response.ok) return [];
      const data = await response.json();
      const symbols = (data.results || []).map((item) => item.symbol).slice(0, 5);

      const expiryResults = await Promise.all(
        symbols.map(async (symbol) => {
          try {
            // Get expiries from authoritative API endpoint
            const expRes = await fetch(`${getBaseUrl()}/options/available/expiries?underlying=${symbol}`);
            if (!expRes.ok) return { symbol, expiries: [] };
            const expData = await expRes.json();
            // Filter to only current and future expiries (not past)
            const today = new Date().toISOString().split('T')[0];
            const validExpiries = (expData.data || []).filter(exp => exp >= today).sort();
            return { symbol, expiries: validExpiries };
          } catch (err) {
            // Fallback: try alternative endpoint
            try {
              const fallbackRes = await fetch(`${getBaseUrl()}/instruments/${symbol}/expiries`);
              if (!fallbackRes.ok) return { symbol, expiries: [] };
              const fallbackData = await fallbackRes.json();
              const today = new Date().toISOString().split('T')[0];
              const validExpiries = (fallbackData.expiries || []).filter(exp => exp >= today).sort();
              return { symbol, expiries: validExpiries };
            } catch (e) {
              return { symbol, expiries: [] };
            }
          }
        })
      );

      return expiryResults.map((entry) => {
        // Use current or next expiry, not past expiries
        const expiry = entry.expiries?.[0] || '';
        const instrumentType = isIndexSymbol(entry.symbol) ? 'INDEX_OPTION' : 'STOCK_OPTION';
        const instrument = {
          symbol: entry.symbol,
          instrumentType: instrumentType === 'INDEX_OPTION' ? 'CE' : 'CE',
          expiry,
          strike: null,
        };
        const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);
        return {
          id: `${entry.symbol}_${expiry || 'NA'}`,
          symbol: entry.symbol,
          exchange: isIndexSymbol(entry.symbol) ? 'NSE_INDEX' : 'NSE',
          instrumentType,
          expiry,
          strike: null,
          lotSize: 1,
          ltp: 0,
          change: 0,
          changePercent: 0,
          primaryDisplay,
          subtext,
          tier: 'TIER_A',
          isSubscribed: false,
        };
      });
    } catch (err) {
      console.warn('[WATCHLIST] Tier A suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const searchAllExchanges = useCallback(async (searchText) => {
    if (!searchText || searchText.length < 2) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const [tierB, tierA] = await Promise.all([
        fetchTierBSuggestions(searchText),
        fetchTierASuggestions(searchText)
      ]);

      const merged = [...tierB, ...tierA].slice(0, 20);
      setSearchResults(merged);
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to search instruments');
    } finally {
      setLoading(false);
    }
  }, [fetchTierBSuggestions, fetchTierASuggestions]);

  // Load default watchlist data
  useEffect(() => {
    const loadDefaultWatchlists = async () => {
      try {
        setLoading(true);
        const allowedExchanges = authService.getAllowedExchanges();

        // Execute fetches in parallel for speed
        // Watchlist 1: NSE - Index options (NIFTY) + Index futures
        // Watchlist 2: BSE - Index options (SENSEX) + Index futures  
        // Watchlist 3: MCX - Commodity futures (GOLD)
        const [nseOptionsRes, nseOptionFutRes, bseRes, mcxRes] = await Promise.all([
          allowedExchanges.includes('NSE_INDEX') ? fetchInstruments('NSE_INDEX', 'NIFTY').catch(() => []) : Promise.resolve([]),
          allowedExchanges.includes('NSE_INDEX') ? fetchInstruments('NSE_INDEX', 'NIFTY FUT').catch(() => []) : Promise.resolve([]),
          allowedExchanges.includes('BSE_INDEX') ? fetchInstruments('BSE_INDEX', 'SENSEX').catch(() => []) : Promise.resolve([]),
          allowedExchanges.includes('MCX') ? fetchInstruments('MCX', 'GOLD').catch(() => []) : Promise.resolve([])
        ]);
        
        // Combine NSE options and futures, limit to 20 total
        const nseRes = [...nseOptionsRes, ...nseOptionFutRes].slice(0, 20);

        setWatchlists({
          1: nseRes,  // Already sliced to 20 above
          2: bseRes.slice(0, 20),
          3: mcxRes.slice(0, 20)
        });
      } catch (err) {
        console.error('Error loading watchlists:', err);
        setError('Failed to load market data.');
      } finally {
        setLoading(false);
      }
    };

    loadDefaultWatchlists();
  }, [fetchInstruments]);

  // Handle search with debouncing
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchTerm) {
        searchAllExchanges(searchTerm);
      } else {
        setSearchResults([]);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchTerm, searchAllExchanges]);

  // Get current display data
  const currentWatchlist = watchlists[selectedWatchlist] || [];
  const displayData = currentWatchlist;

  return (
    <div className="h-[80vh] bg-gray-50 flex flex-col">
      {/* Header - Full Width */}
      <div className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold text-gray-900">Watchlist</h1>
            <span className="text-sm text-gray-500">Total Scripts: {displayData.length}</span>
          </div>
        </div>

        {/* Search Bar - Full Width */}
        <div className="px-6 pb-4">
          <div className="relative max-w-4xl mx-auto">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              {loading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></div>
              ) : (
                <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              )}
            </div>
            <input
              type="text"
              placeholder="Search instruments..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="block w-full rounded-md border-0 py-2 pl-10 pr-3 text-gray-900 ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-5 bg-gray-50"
            />

            {searchTerm && searchResults.length > 0 && (
              <div className="absolute z-20 mt-2 w-full rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
                <ul className="max-h-60 overflow-y-auto py-1 text-sm text-gray-700">
                  {searchResults.map((item) => (
                    <li
                      key={`${item.tier}-${item.id}`}
                      className="cursor-pointer px-3 py-2 hover:bg-gray-100"
                      onClick={() => addToWatchlist(item)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-gray-900">
                            {item.primaryDisplay || item.symbol}
                          </div>
                          {item.subtext && (
                            <div className="text-xs text-gray-500">{item.subtext}</div>
                          )}
                        </div>
                        <span className={`text-xs font-semibold px-2 py-1 rounded ${item.tier === 'TIER_B'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'}`}
                        >
                          {item.tier === 'TIER_B' ? 'Subscribed' : 'Available'}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {searchTerm && !loading && searchResults.length === 0 && (
              <div className="absolute z-20 mt-2 w-full rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
                <div className="px-3 py-2 text-sm text-gray-500">
                  No suggestions found.
                </div>
              </div>
            )}
          </div>
          {error && (
            <div className={`mt-2 rounded-md p-2 text-xs max-w-4xl mx-auto ${error.includes('already exists')
              ? 'bg-yellow-50 text-yellow-800 ring-1 ring-inset ring-yellow-200'
              : error.includes('successfully')
                ? 'bg-green-50 text-green-800 ring-1 ring-inset ring-green-200'
                : 'bg-red-50 text-red-800 ring-1 ring-inset ring-red-200'
              }`}>
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Content - Full Width Scrollable */}
      <div className="flex-1 overflow-hidden">
        {displayData.length === 0 && !loading ? (
          <div className="flex flex-col items-center justify-center h-full text-gray-500">
            <svg className="h-12 w-12 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No instruments in watchlist
            </h3>
            <p className="text-sm text-gray-500">
              Add instruments to your watchlist
            </p>
          </div>
        ) : (
          <div className="h-full overflow-y-auto">
            <div className="max-w-7xl mx-auto min-w-full">
              {/* Table Header - Sticky */}
              <div className="sticky top-0 z-10 bg-white border-b border-gray-200">
                <div className="grid grid-cols-12 px-6 py-2 text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <div className="col-span-4">Symbol</div>
                  <div className="col-span-2 text-center">Exchange</div>
                  <div className="col-span-2 text-right">LTP</div>
                  <div className="col-span-2 text-right">Change</div>
                  <div className="col-span-2 text-center">Actions</div>
                </div>
              </div>

              {/* Table Body */}
              <div className="bg-white">
                {displayData.map((item, index) => (
                  <div
                    key={`${item.exchange}-${item.id}-${index}`}
                    className="grid grid-cols-12 px-6 py-2 border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  >
                    {/* Symbol Column */}
                    <div className="col-span-4 flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {item.primaryDisplay || item.symbol}
                        </div>
                        {item.subtext && (
                          <div className="text-xs text-gray-500 mt-0.5">
                            {item.subtext}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Exchange Column */}
                    <div className="col-span-2 flex items-center justify-center">
                      <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-800">
                        {item.exchange}
                      </span>
                    </div>

                    {/* LTP Column */}
                    <div className="col-span-2 flex items-center justify-end">
                      <div className="text-sm font-semibold text-gray-900">
                        {item.ltp > 0 ? `₹${item.ltp.toFixed(2)}` : '--'}
                      </div>
                    </div>

                    {/* Change Column */}
                    <div className="col-span-2 flex items-center justify-end">
                      {item.change !== 0 && (
                        <div className="text-right">
                          <div className={`text-sm font-medium ${item.change >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                            {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}
                          </div>
                          <div className={`text-xs ${item.changePercent >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                            {item.changePercent >= 0 ? '↑' : '↓'} {Math.abs(item.changePercent).toFixed(2)}%
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Actions Column */}
                    <div className="col-span-2 flex items-center justify-center space-x-1">
                      <button
                        onClick={() =>
                          handleOpenOrderModal([{
                            symbol: item.symbol,
                            action: 'BUY',
                            ltp: item.ltp,
                            lotSize: item.lotSize,
                            expiry: item.expiry,
                            exchange: item.exchange,
                            instrumentType: item.instrumentType,
                            strike: item.strike
                          }])
                        }
                        className="inline-flex items-center rounded-md bg-blue-600 px-2 py-1 text-xs font-medium text-white shadow-sm hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 transition-colors"
                        title="Buy"
                      >
                        BUY
                      </button>
                      <button
                        onClick={() =>
                          handleOpenOrderModal([{
                            symbol: item.symbol,
                            action: 'SELL',
                            ltp: item.ltp,
                            lotSize: item.lotSize,
                            expiry: item.expiry,
                            exchange: item.exchange,
                            instrumentType: item.instrumentType,
                            strike: item.strike
                          }])
                        }
                        className="inline-flex items-center rounded-md bg-orange-600 px-2 py-1 text-xs font-medium text-white shadow-sm hover:bg-orange-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500 transition-colors"
                        title="Sell"
                      >
                        SELL
                      </button>
                      <button
                        onClick={() => removeFromWatchlist(item.id, item.exchange)}
                        className="inline-flex items-center rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white shadow-sm hover:bg-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 transition-colors"
                        title="Remove from Watchlist"
                      >
                        REMOVE
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Watchlist Numbers - Full Width Footer */}
      {!searchTerm && (
        <div className="bg-white border-t border-gray-200 px-6 py-3 flex-shrink-0">
          <div className="flex justify-center space-x-2 max-w-4xl mx-auto">
            {Object.keys(watchlists).map((num) => (
              <button
                key={num}
                onClick={() => setSelectedWatchlist(parseInt(num))}
                className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${selectedWatchlist === parseInt(num)
                  ? 'bg-blue-600 text-white shadow-sm ring-2 ring-blue-500 ring-offset-2'
                  : 'bg-gray-100 text-gray-700 ring-1 ring-gray-300 hover:bg-gray-50 hover:ring-gray-400'
                  }`}
              >
                Watchlist {num}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default WatchlistComponent;