import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { RefreshCw } from 'lucide-react';
import { useMarketPulse } from '../hooks/useMarketPulse';

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
  const { user } = useAuth();
  const { pulse, marketActive } = useMarketPulse();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedWatchlist, setSelectedWatchlist] = useState(1);
  const [watchlists, setWatchlists] = useState({ 1: [], 2: [], 3: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [sortBy] = useState('AZ');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchContainerRef = useRef(null);
  const [depthOpen, setDepthOpen] = useState({});
  const [depthCache, setDepthCache] = useState({});
  const [depthLoading, setDepthLoading] = useState({});
  const [pendingLtpByKey, setPendingLtpByKey] = useState({});

  const getItemKey = useCallback((item) => `${item?.exchange || 'NSE'}:${item?.id}`, []);
  const getDepthKey = useCallback((item) => {
    const exchange = item?.exchange || 'NSE';
    const symbol = item?.symbol || '';
    const expiry = item?.expiry || '';
    const strike = item?.strike ?? '';
    const instrumentType = item?.instrumentType || '';
    return `${exchange}:${symbol}:${expiry}:${strike}:${instrumentType}`;
  }, []);

  const getUnderlyingLtp = useCallback(async (symbol) => {
    try {
      const res = await apiService.get(`/market/underlying-ltp/${symbol}`);
      return res?.ltp || res?.data?.ltp || null;
    } catch (err) {
      console.warn('[WATCHLIST] Failed to fetch underlying LTP:', err);
    }
    return null;
  }, []);

  const isIndexSymbol = (symbol) => {
    const indexSet = new Set(['NIFTY', 'BANKNIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY', 'BANKEX']);
    return indexSet.has((symbol || '').toUpperCase());
  };

  const fetchFutureQuote = useCallback(async (symbol, expiry, exchange = 'NSE') => {
    try {
      const payload = await apiService.get('/futures/quote', { exchange, symbol, expiry });
      return payload?.data || null;
    } catch {
      return null;
    }
  }, []);

  const fetchOptionLegLtp = useCallback(async (symbol, expiry, strike, optionType) => {
    try {
      if (!symbol || !expiry || strike === null || strike === undefined || !optionType) {
        return null;
      }
      const payload = await apiService.get('/options/live', { underlying: symbol, expiry });
      const strikes = payload?.data?.strikes || {};
      const strikeKey = Number(strike).toString();
      const altKey = Number(strike).toFixed(1);
      const leg = (strikes[strikeKey] || strikes[altKey] || strikes[String(strike)] || {})[String(optionType).toUpperCase()];
      const ltp = Number(leg?.ltp);
      if (Number.isFinite(ltp) && ltp > 0) {
        return ltp;
      }
      return null;
    } catch {
      return null;
    }
  }, []);

  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const getUnderlyingLtpWithRetry = useCallback(async (symbol, attempts = 6, delayMs = 400) => {
    for (let index = 0; index < attempts; index++) {
      const ltp = await getUnderlyingLtp(symbol);
      if (ltp !== null && ltp !== undefined && Number.isFinite(Number(ltp)) && Number(ltp) > 0) {
        return Number(ltp);
      }
      if (index < attempts - 1) {
        await sleep(delayMs);
      }
    }
    return null;
  }, [getUnderlyingLtp]);

  // Add instrument to current watchlist (subscribe if on-demand)
  const addToWatchlist = useCallback(async (instrument) => {
    const currentList = watchlists[selectedWatchlist] || [];
    const userId = user?.id;
    if (!userId) {
      setError('User not available');
      setTimeout(() => setError(''), 2000);
      return;
    }

    // Check if instrument already exists in watchlist
    const exists = currentList.some(item =>
      item.id === instrument.id && item.exchange === instrument.exchange
    );

    if (exists) {
      setError('Instrument already exists in watchlist');
      setTimeout(() => setError(''), 3000);
      return;
    }

    const optimisticKey = getItemKey(instrument);
    const optimisticItem = {
      ...instrument,
      _pendingSubscription: true,
    };

    setWatchlists(prev => ({
      ...prev,
      [selectedWatchlist]: [...(prev[selectedWatchlist] || []), optimisticItem]
    }));
    setPendingLtpByKey(prev => ({ ...prev, [optimisticKey]: true }));
    setSearchTerm('');
    setSearchResults([]);
    setShowSuggestions(false);

    try {
      let result = null;
      const normalizedType = (instrument.instrumentType || '').toUpperCase();

      if (normalizedType !== 'FUT') {
        let payload;
        if (normalizedType === 'EQUITY') {
          payload = {
            user_id: userId,
            symbol: instrument.symbol,
            expiry: instrument.expiry || null,
            instrument_type: 'EQUITY',
            underlying_ltp: null
          };
        } else {
          if (!instrument.expiry) {
            throw new Error('No expiry available for this instrument');
          }
          const instrumentType = isIndexSymbol(instrument.symbol) ? 'INDEX_OPTION' : 'STOCK_OPTION';
          const underlyingLtp = await getUnderlyingLtp(instrument.symbol);
          payload = {
            user_id: userId,
            symbol: instrument.symbol,
            expiry: instrument.expiry,
            instrument_type: instrumentType,
            underlying_ltp: underlyingLtp
          };
        }

        result = await apiService.post('/watchlist/add', payload);
        if (!result || (!result.success && result.error !== 'DUPLICATE')) {
          throw new Error((result && (result.detail || result.message)) || 'Failed to add to watchlist');
        }
      }

      let ltpUpdate = null;
      let changeUpdate = null;
      let changePercentUpdate = null;
      let lotSizeUpdate = null;

      if (normalizedType === 'FUT' && instrument.expiry) {
        const fut = await fetchFutureQuote(instrument.symbol, instrument.expiry, instrument.exchange || 'NSE');
        if (fut) {
          ltpUpdate = fut.ltp || 0;
          changeUpdate = fut.change || 0;
          changePercentUpdate = fut.changePercent || 0;
          lotSizeUpdate = fut.lot_size || instrument.lotSize || 1;
        }
      } else if (normalizedType === 'CE' || normalizedType === 'PE') {
        const optLtp = await fetchOptionLegLtp(instrument.symbol, instrument.expiry, instrument.strike, normalizedType);
        if (optLtp !== null) {
          ltpUpdate = optLtp;
        }
      } else {
        let liveLtp = Number(result?.ltp);
        if (!Number.isFinite(liveLtp) || liveLtp <= 0) {
          const fallback = await getUnderlyingLtp(instrument.symbol);
          liveLtp = Number(fallback);
        }
        if (Number.isFinite(liveLtp) && liveLtp > 0) {
          ltpUpdate = liveLtp;
        }
      }

      setWatchlists(prev => ({
        ...prev,
        [selectedWatchlist]: (prev[selectedWatchlist] || []).map((item) => {
          if (getItemKey(item) !== optimisticKey) return item;
          return {
            ...item,
            ltp: ltpUpdate !== null ? ltpUpdate : item.ltp,
            change: changeUpdate !== null ? changeUpdate : item.change,
            changePercent: changePercentUpdate !== null ? changePercentUpdate : item.changePercent,
            lotSize: lotSizeUpdate !== null ? lotSizeUpdate : item.lotSize,
            _pendingSubscription: false,
          };
        })
      }));

      setError('Instrument added to watchlist successfully!');
      setTimeout(() => setError(''), 2000);
    } catch (err) {
      console.error('Error adding to watchlist:', err);
      setWatchlists(prev => ({
        ...prev,
        [selectedWatchlist]: (prev[selectedWatchlist] || []).filter((item) => getItemKey(item) !== optimisticKey)
      }));
      setError(err.message || 'Failed to add instrument to watchlist');
      setTimeout(() => setError(''), 2000);
    } finally {
      setPendingLtpByKey(prev => ({ ...prev, [optimisticKey]: false }));
    }
  }, [watchlists, selectedWatchlist, user, fetchFutureQuote, fetchOptionLegLtp, getUnderlyingLtp, getItemKey]);

  // Remove instrument from watchlist
  const removeFromWatchlist = useCallback(async (instrumentId, exchange) => {
    const currentList = watchlists[selectedWatchlist] || [];
    const updatedList = currentList.filter(item =>
      !(item.id === instrumentId && item.exchange === exchange)
    );
    const userId = user?.id;
    if (!userId) {
      setError('User not available');
      setTimeout(() => setError(''), 2000);
      return;
    }

    try {
      // Remove from watchlist via API
      const foundItem = currentList.find(item => item.id === instrumentId);
      const payload = {
        user_id: userId,
        symbol: foundItem?.symbol || '',
        expiry: foundItem?.expiry || ''
      };

      await apiService.post('/watchlist/remove', payload);
      
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
  }, [watchlists, selectedWatchlist, user]);

  const extractUnderlyingFromQuery = (text) => {
    const tokens = (text || '').trim().toUpperCase().split(/\s+/);
    const indexSet = new Set(['NIFTY', 'BANKNIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY', 'BANKEX']);
    for (const t of tokens) {
      if (indexSet.has(t)) return t;
    }
    return null;
  };

  const fetchOptionStrikeSuggestions = useCallback(async (searchText) => {
    try {
      const underlying = extractUnderlyingFromQuery(searchText);
      const endpoint = `/options/strikes/search?q=${encodeURIComponent(searchText)}&limit=20${underlying ? `&underlying=${encodeURIComponent(underlying)}` : ''}`;
      const data = await apiService.get(endpoint).catch(() => null);
      if (!data) return [];
      return (data.results || []).map((row) => {
        const instrument = {
          symbol: row.symbol,
          instrumentType: row.option_type,
          expiry: row.expiry,
          strike: row.strike,
        };
        const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);
        return {
          id: row.token,
          symbol: row.symbol,
          exchange: row.exchange || 'NSE',
          instrumentType: row.option_type, // CE/PE
          expiry: row.expiry,
          strike: row.strike,
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
      console.warn('[WATCHLIST] Option strike suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const fetchOptionDepth = useCallback(async (symbol, expiry, strike, optionType) => {
    try {
      const endpoint = `/market/option-depth?underlying=${encodeURIComponent(symbol)}&expiry=${encodeURIComponent(expiry)}&strike=${encodeURIComponent(strike)}&option_type=${encodeURIComponent(optionType)}`;
      const data = await apiService.get(endpoint).catch(() => null);
      return data?.data || null;
    } catch {
      return null;
    }
  }, []);

  const fetchMarketDepth = useCallback(async (symbol) => {
    try {
      const data = await apiService.get(`/market/depth/${encodeURIComponent(symbol)}`).catch(() => null);
      return data?.data || null;
    } catch {
      return null;
    }
  }, []);

  const toggleDepth = useCallback(async (item) => {
    const isOption = item.instrumentType === 'CE' || item.instrumentType === 'PE';
    const depthKey = getDepthKey(item);
    const opened = !!depthOpen[depthKey];
    if (opened) {
      setDepthOpen(prev => ({ ...prev, [depthKey]: false }));
      return;
    }
    setDepthLoading(prev => ({ ...prev, [depthKey]: true }));
    const data = isOption
      ? await fetchOptionDepth(item.symbol, item.expiry, item.strike, item.instrumentType)
      : await fetchMarketDepth(item.symbol);
    if (data) {
      setDepthCache(prev => ({ ...prev, [depthKey]: data }));
    }
    setDepthLoading(prev => ({ ...prev, [depthKey]: false }));
    setDepthOpen(prev => ({ ...prev, [depthKey]: true }));
  }, [depthOpen, fetchOptionDepth, fetchMarketDepth, getDepthKey]);

  const fetchTierBSuggestions = useCallback(async (searchText) => {
    try {
      const endpoint = `/subscriptions/search?q=${encodeURIComponent(searchText)}&tier=TIER_B&limit=20`;
      const data = await apiService.get(endpoint).catch(() => null);
      if (!data) return [];
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
          isSubscribed: sub.is_subscribed !== false,
        };
      });
    } catch (err) {
      console.warn('[WATCHLIST] Tier B suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const fetchTierASubscriptionSuggestions = useCallback(async (searchText) => {
    try {
      const endpoint = `/subscriptions/search?q=${encodeURIComponent(searchText)}&tier=TIER_A&limit=20`;
      const data = await apiService.get(endpoint).catch(() => null);
      if (!data) return [];
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
          tier: 'TIER_A',
          isSubscribed: sub.is_subscribed !== false,
        };
      });
    } catch (err) {
      console.warn('[WATCHLIST] Tier A subscription suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const fetchFuturesSuggestions = useCallback(async (searchText) => {
    try {
      const endpoint = `/instruments/futures/search?q=${encodeURIComponent(searchText)}&limit=20`;
      const data = await apiService.get(endpoint).catch(() => null);
      if (!data) return [];
      return (data.results || []).map((fut) => {
        const instrument = {
          symbol: fut.symbol,
          instrumentType: 'FUT',
          expiry: fut.expiry,
          strike: null,
        };
        const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);
        return {
          id: fut.token,
          symbol: fut.symbol,
          exchange: fut.exchange || 'NSE',
          instrumentType: 'FUT',
          expiry: fut.expiry,
          strike: null,
          lotSize: fut.lot_size || 1,
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
      console.warn('[WATCHLIST] Futures suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const fetchEquitySuggestions = useCallback(async (searchText) => {
    try {
      const endpoint = `/instruments/search?q=${encodeURIComponent(searchText)}&limit=20`;
      const data = await apiService.get(endpoint).catch(() => null);
      if (!data) return [];
      return (data.results || [])
      .filter((row) => Boolean(row?.is_equity || row?.is_etf))
      .map((row) => {
        const instrument = {
          symbol: row.symbol,
          instrumentType: 'EQUITY',
          expiry: null,
          strike: null,
        };
        const { primaryDisplay, subtext } = formatInstrumentDisplay(instrument);
        return {
          id: `EQUITY_${row.symbol}`,
          symbol: row.symbol,
          exchange: 'NSE',
          instrumentType: 'EQUITY',
          expiry: null,
          strike: null,
          lotSize: 1,
          ltp: 0,
          change: 0,
          changePercent: 0,
          primaryDisplay,
          subtext,
          tier: row.f_o_eligible ? 'TIER_A' : 'TIER_B',
          isSubscribed: false,
        };
      });
    } catch (err) {
      console.warn('[WATCHLIST] Equity suggestion fetch failed:', err);
      return [];
    }
  }, []);

  const handleRefresh = useCallback(async () => {
    const currentList = watchlists[selectedWatchlist] || [];
    const optionChainCache = {};

    const getOptionChain = async (symbol, expiry) => {
      const cacheKey = `${symbol}_${expiry}`;
      if (optionChainCache[cacheKey]) {
        return optionChainCache[cacheKey];
      }
      try {
        const payload = await apiService.get('/options/live', { underlying: symbol, expiry });
        const strikes = payload?.data?.strikes || {};
        optionChainCache[cacheKey] = strikes;
        return strikes;
      } catch {
        optionChainCache[cacheKey] = {};
        return {};
      }
    };

    const updatedList = await Promise.all(currentList.map(async (item) => {
      if (item.instrumentType === 'FUT' && item.expiry) {
        const fut = await fetchFutureQuote(item.symbol, item.expiry, item.exchange || 'NSE');
        if (fut) {
          return {
            ...item,
            ltp: fut.ltp || item.ltp || 0,
            change: fut.change || item.change || 0,
            changePercent: fut.changePercent || item.changePercent || 0,
            lotSize: fut.lot_size || item.lotSize || 1
          };
        }
      } else if ((item.instrumentType === 'CE' || item.instrumentType === 'PE') && item.expiry && item.strike !== null && item.strike !== undefined) {
        const strikes = await getOptionChain(item.symbol, item.expiry);
        const strikeKey = Number(item.strike).toString();
        const altKey = Number(item.strike).toFixed(1);
        const leg = (strikes[strikeKey] || strikes[altKey] || strikes[String(item.strike)] || {})[item.instrumentType];
        const ltp = Number(leg?.ltp);
        if (Number.isFinite(ltp) && ltp > 0) {
          return {
            ...item,
            ltp,
          };
        }
      } else {
        const ltp = await getUnderlyingLtp(item.symbol);
        if (ltp !== null && ltp !== undefined) {
          return {
            ...item,
            ltp: ltp,
          };
        }
      }
      return item;
    }));
    setWatchlists(prev => ({
      ...prev,
      [selectedWatchlist]: updatedList
    }));
  }, [watchlists, selectedWatchlist, fetchFutureQuote, getUnderlyingLtp]);

  const searchAllExchanges = useCallback(async (searchText) => {
    if (!searchText || searchText.length < 2) {
      setSearchResults([]);
      return;
    }

    setLoading(true);
    try {
      const [tierB, tierASubs, futures, optionStrikes, equities] = await Promise.all([
        fetchTierBSuggestions(searchText),
        fetchTierASubscriptionSuggestions(searchText),
        fetchFuturesSuggestions(searchText),
        fetchOptionStrikeSuggestions(searchText),
        fetchEquitySuggestions(searchText)
      ]);

      const isOptionIntent = /\b(CE|PE)\b/i.test(searchText) || /\d/.test(searchText);
      const onlyOptions = (arr) => arr.filter(i => i.instrumentType === 'CE' || i.instrumentType === 'PE');
      const onlyFutures = (arr) => arr.filter(i => i.instrumentType === 'FUT');
      const other = (arr) => arr.filter(i => !(i.instrumentType === 'CE' || i.instrumentType === 'PE' || i.instrumentType === 'FUT'));
      let merged;
      if (isOptionIntent) {
        merged = [
          ...onlyOptions(optionStrikes),
          ...onlyOptions(tierASubs),
          ...onlyOptions(tierB),
          ...onlyFutures(futures),
          ...equities,
          ...other(tierASubs),
          ...other(tierB),
        ].slice(0, 20);
      } else {
        merged = [
          ...onlyFutures(futures),
          ...equities,
          ...onlyOptions(optionStrikes),
          ...tierASubs,
          ...tierB,
        ].slice(0, 20);
      }
      setSearchResults(merged);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Search error:', error);
      setError('Failed to search instruments');
    } finally {
      setLoading(false);
    }
  }, [fetchTierBSuggestions, fetchTierASubscriptionSuggestions, fetchFuturesSuggestions, fetchOptionStrikeSuggestions, fetchEquitySuggestions]);

  // Do not auto-load any default watchlist data on mount
  useEffect(() => {
    const load = async () => {
      try {
        if (!user?.id) return;
        const data = await apiService.get(`/watchlist/${user.id}`).catch(() => null);
        if (!data) return;
        const entries = data.watchlist || data.data || [];
        const mapped = await Promise.all(entries.map(async (e) => {
          const normalizedInstrumentType = String(e.instrument_type || '').toUpperCase();
          const displayInstrumentType = (normalizedInstrumentType === 'CE' || normalizedInstrumentType === 'PE' || normalizedInstrumentType === 'FUT')
            ? normalizedInstrumentType
            : (normalizedInstrumentType === 'EQUITY' ? 'EQUITY' : 'INDEX');
          const instrument = {
            id: `${e.symbol}_${e.expiry_date}`,
            symbol: e.symbol,
            exchange: isIndexSymbol(e.symbol) ? 'NSE_INDEX' : 'NSE',
            instrumentType: normalizedInstrumentType,
            expiry: e.expiry_date,
            strike: null,
            lotSize: 1,
            ltp: 0,
            change: 0,
            changePercent: 0,
            ...formatInstrumentDisplay({
              symbol: e.symbol,
              instrumentType: displayInstrumentType,
              expiry: e.expiry_date,
              strike: null
            })
          };
          if (instrument.instrumentType === 'FUT' && instrument.expiry) {
            const fut = await fetchFutureQuote(instrument.symbol, instrument.expiry, instrument.exchange || 'NSE');
            if (fut) {
              instrument.ltp = fut.ltp || 0;
              instrument.change = fut.change || 0;
              instrument.changePercent = fut.changePercent || 0;
              instrument.lotSize = fut.lot_size || 1;
            }
          } else {
            if (instrument.instrumentType === 'EQUITY') {
              const liveLtp = await getUnderlyingLtpWithRetry(instrument.symbol);
              if (liveLtp !== null && liveLtp !== undefined) {
                instrument.ltp = Number(liveLtp) || 0;
              }
            } else {
              const ltp = Number(e?.ltp);
              if (Number.isFinite(ltp) && ltp > 0) {
                instrument.ltp = ltp;
              } else {
                const liveLtp = await getUnderlyingLtp(instrument.symbol);
                if (liveLtp !== null && liveLtp !== undefined) {
                  instrument.ltp = Number(liveLtp) || 0;
                }
              }
            }
          }
          return instrument;
        }));
        setWatchlists(prev => ({ ...prev, 1: mapped }));
      } catch (err) {
        console.warn('Failed to load persisted watchlist:', err);
      }
    };
    load();
  }, [user, fetchFutureQuote, getUnderlyingLtp, getUnderlyingLtpWithRetry]);

  // Handle search with debouncing
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchTerm) {
        searchAllExchanges(searchTerm);
      } else {
        setSearchResults([]);
        setShowSuggestions(false);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timeoutId);
  }, [searchTerm, searchAllExchanges]);

  useEffect(() => {
    const currentList = watchlists[selectedWatchlist] || [];
    if (!marketActive || !pulse?.timestamp || !currentList.length) {
      return;
    }
    handleRefresh();
  }, [pulse?.timestamp, marketActive, watchlists, selectedWatchlist, handleRefresh]);

  useEffect(() => {
    const handler = (e) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Get current display data
  const currentWatchlist = watchlists[selectedWatchlist] || [];
  const displayData = currentWatchlist;
  const sortedDisplayData = useMemo(() => {
    const arr = [...displayData];
    if (sortBy === 'AZ') {
      arr.sort((a, b) => (a.symbol || '').localeCompare(b.symbol || ''));
    } else if (sortBy === 'PERCENT') {
      arr.sort((a, b) => (b.changePercent || 0) - (a.changePercent || 0));
    } else if (sortBy === 'LTP') {
      arr.sort((a, b) => (b.ltp || 0) - (a.ltp || 0));
    }
    return arr;
  }, [displayData, sortBy]);

  return (
    <div className="h-[80vh] bg-gray-50 flex flex-col">
      {/* Header - Full Width (merged row) */}
      <div className="bg-white shadow-sm border-b border-gray-200 flex-shrink-0">
        <div className="px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900">Watchlist</h1>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">Total Scripts: {displayData.length}</span>
              <button
                onClick={handleRefresh}
                className="p-1 text-blue-600 hover:text-blue-800"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
        {/* Search Bar */}
        <div className="px-6 pb-3">
          <div ref={searchContainerRef} className="relative max-w-4xl mx-auto">
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

            {showSuggestions && searchTerm && searchResults.length > 0 && (
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
                        <span className={`text-xs font-semibold px-2 py-1 rounded ${item.isSubscribed
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'}`}
                        >
                          {item.isSubscribed ? 'Subscribed' : 'Available'}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {showSuggestions && searchTerm && !loading && searchResults.length === 0 && (
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
                  <div className="col-span-2 text-center">Depth</div>
                  <div className="col-span-2 text-right">LTP</div>
                  <div className="col-span-2 text-right">Change</div>
                  <div className="col-span-2 text-center">Actions</div>
                </div>
              </div>

              {/* Table Body */}
              <div className="bg-white">
                {sortedDisplayData.map((item, index) => {
                  const isOption = item.instrumentType === 'CE' || item.instrumentType === 'PE';
                  const canDepth = isOption || item.instrumentType === 'EQUITY' || item.instrumentType === 'FUT' || item.instrumentType === 'INDEX';
                  const itemKey = getItemKey(item);
                  const depthKey = getDepthKey(item);
                  const isPendingQuote = !!item._pendingSubscription || !!pendingLtpByKey[itemKey];
                  return (
                  <React.Fragment key={`${item.exchange}-${item.id}-${index}`}>
                  <div
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

                    {/* Depth Column (replaces Exchange) */}
                    <div className="col-span-2 flex items-center justify-center">
                      <button
                        onClick={() => toggleDepth(item)}
                        disabled={!canDepth}
                        className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium shadow-sm transition-colors ${
                          canDepth
                            ? 'bg-gray-700 text-white hover:bg-gray-800'
                            : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                        }`}
                        title="Top-5 Bid/Ask"
                      >
                        DEPTH
                      </button>
                    </div>

                    {/* LTP Column */}
                    <div className="col-span-2 flex items-center justify-end">
                      {isPendingQuote ? (
                        <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" title="Subscribing" />
                      ) : (
                        <div className="text-sm font-semibold text-gray-900">
                          {item.ltp > 0 ? `₹${item.ltp.toFixed(2)}` : '--'}
                        </div>
                      )}
                    </div>

                    {/* Change Column */}
                    <div className="col-span-2 flex items-center justify-end">
                      {!isPendingQuote && item.change !== 0 && (
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
                    <div className="col-span-2 flex items-center justify-end gap-1 flex-nowrap whitespace-nowrap">
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
                        className="inline-flex items-center rounded-md bg-blue-600 px-2 py-1 text-[11px] font-medium text-white shadow-sm hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-500 transition-colors"
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
                        className="inline-flex items-center rounded-md bg-orange-600 px-2 py-1 text-[11px] font-medium text-white shadow-sm hover:bg-orange-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-500 transition-colors"
                        title="Sell"
                      >
                        SELL
                      </button>
                      <button
                        onClick={() => removeFromWatchlist(item.id, item.exchange)}
                        className="inline-flex items-center rounded-md bg-red-600 px-1 py-1 text-[11px] font-medium text-white shadow-sm hover:bg-red-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 transition-colors"
                        title="Remove from Watchlist"
                      >
                        REMOVE
                      </button>
                    </div>
                  </div>
                  {depthOpen[depthKey] && (
                    <div className="px-6 py-2 border-b border-gray-100 bg-gray-50">
                      {depthLoading[depthKey] ? (
                        <div className="text-xs text-gray-600">Loading depth...</div>
                      ) : (
                        <div className="grid grid-cols-12 gap-4">
                          <div className="col-span-6">
                            <div className="text-xs font-semibold text-gray-700 mb-1">Bids</div>
                            <ul className="text-xs">
                              {(depthCache[depthKey]?.bids || []).slice(0,5).map((b, i) => (
                                <li key={`bid-${i}`} className="flex justify-between py-0.5">
                                  <span>{(b.price ?? b[0] ?? '--')}</span>
                                  <span className="text-gray-500">{(b.qty ?? b[1] ?? '')}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div className="col-span-6">
                            <div className="text-xs font-semibold text-gray-700 mb-1">Asks</div>
                            <ul className="text-xs">
                              {(depthCache[depthKey]?.asks || []).slice(0,5).map((a, i) => (
                                <li key={`ask-${i}`} className="flex justify-between py-0.5">
                                  <span>{(a.price ?? a[0] ?? '--')}</span>
                                  <span className="text-gray-500">{(a.qty ?? a[1] ?? '')}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  </React.Fragment>
                );})}
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
                  ? 'bg-blue-600 !text-white shadow-sm ring-2 ring-blue-500 ring-offset-2'
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
