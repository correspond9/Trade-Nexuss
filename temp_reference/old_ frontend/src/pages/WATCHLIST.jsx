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

  // Add instrument to current watchlist
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
      // Add to watchlist via API
      await apiService.post('/market/watchlist/' + instrument.security_id);
      
      // Add to local state
      setWatchlists(prev => ({
        ...prev,
        [selectedWatchlist]: [...currentList, instrument]
      }));

      // Clear search after adding
      setSearchTerm('');
      setSearchResults([]);

      // Show success message
      setError('Instrument added to watchlist successfully!');
      setTimeout(() => setError(''), 2000);
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      setError('Failed to add instrument to watchlist');
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
      await apiService.delete('/market/watchlist/' + instrumentId);
      
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

  // Search across all exchanges using Instrument Master ONLY
  const searchAllExchanges = useCallback(async (searchText) => {
    if (!searchText || searchText.length < 2) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      // Use FastAPI market instruments endpoint - NO WebSocket dependency
      const response = await apiService.get('/market/instruments/NSE', {
        search: searchText,
        limit: 50
      });

      if (response && response.data) {
        // Transform data to match expected format
        // KEEP CANONICAL DATA - Add formatted display fields for UI only
        const transformedResults = response.data.map(instrument => {
          // Calculate human-readable display formatting
          const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);

          return {
            // === CANONICAL DATA (unchanged) ===
            id: instrument.instrumentId,
            symbol: instrument.symbol,
            name: instrument.displayName || instrument.symbol,
            exchange: instrument.exchange,
            instrumentType: instrument.instrumentType,
            expiry: instrument.expiry,
            strike: instrument.strike,
            lotSize: instrument.lotSize,
            ltp: 0,
            change: 0,
            changePercent: 0,
            primaryDisplay,
            subtext,
            tradingSymbol: instrument.tradingSymbol
          };
        });

        setSearchResults(transformedResults);
        console.log(`Found ${transformedResults.length} instruments from master`);
      }
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to search instruments');
    } finally {
      setLoading(false);
    }
  }, []);

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

  // Load default watchlist data
  useEffect(() => {
    const loadDefaultWatchlists = async () => {
      try {
        setLoading(true);
        const allowedExchanges = authService.getAllowedExchanges();

        // Execute fetches in parallel for speed
        const [nseRes, bseRes, mcxRes] = await Promise.all([
          allowedExchanges.includes('NSE_INDEX') ? fetchInstruments('NSE_INDEX', 'NIFTY').catch(() => []) : Promise.resolve([]),
          allowedExchanges.includes('BSE_INDEX') ? fetchInstruments('BSE_INDEX', 'SENSEX').catch(() => []) : Promise.resolve([]),
          allowedExchanges.includes('MCX') ? fetchInstruments('MCX', 'GOLD').catch(() => []) : Promise.resolve([])
        ]);

        setWatchlists({
          1: nseRes.slice(0, 20),
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
  const displayData = searchTerm ? searchResults : currentWatchlist;

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
              {searchTerm ? 'No instruments found' : 'No instruments in watchlist'}
            </h3>
            <p className="text-sm text-gray-500">
              {searchTerm ? 'Try a different search term' : 'Add instruments to your watchlist'}
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
                    className={`grid grid-cols-12 px-6 py-2 border-b border-gray-100 hover:bg-gray-50 transition-colors ${searchTerm ? 'bg-blue-50' : ''
                      }`}
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
                        {searchTerm && (
                          <span className="mt-1 inline-flex items-center rounded-md bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-800">
                            SEARCH RESULT
                          </span>
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
                      {searchTerm ? (
                        // Search result buttons
                        <>
                          <button
                            onClick={() => addToWatchlist(item)}
                            className="inline-flex items-center rounded-md bg-green-600 px-2 py-1 text-xs font-medium text-white shadow-sm hover:bg-green-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-green-500 transition-colors"
                            title="Add to Watchlist"
                          >
                            ADD
                          </button>
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
                        </>
                      ) : (
                        // Watchlist item buttons
                        <>
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
                        </>
                      )}
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