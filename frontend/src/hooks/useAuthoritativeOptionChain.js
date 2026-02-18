import { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * useAuthoritativeOptionChain Hook
 * 
 * Fetches realtime option chain data from the authoritative central cache API
 * Handles caching, polling, errors, and provides automatic refresh capability
 * 
 * Features:
 * - Real-time data from central cache (WebSocket enhanced)
 * - Smart caching to reduce API calls
 * - Auto-refresh with configurable interval
 * - Error handling without fallback pricing
 * - Loading states and metadata
 */
import { apiService } from '../services/apiService';
import { useWebSocket } from './useWebSocket';

export const useAuthoritativeOptionChain = (underlying, expiry, options = {}) => {
  // State management
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [timestamp, setTimestamp] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [retryCount, setRetryCount] = useState(0); // Add retry counter
  const [servedExpiry, setServedExpiry] = useState(expiry || null);
  
  // Options with defaults
  const {
    autoRefresh = true,
    refreshInterval = 1000,
  } = options;

  const streamUrl = useMemo(() => {
    if (!underlying || !servedExpiry) {
      return null;
    }
    const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000';
    const endpoint = `/api/v2/options/ws/live?underlying=${encodeURIComponent(underlying)}&expiry=${encodeURIComponent(servedExpiry)}`;
    try {
      const base = new URL(apiService.baseURL, fallbackOrigin);
      const wsProtocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${base.host}${endpoint}`;
    } catch (_error) {
      const wsProtocol = fallbackOrigin.startsWith('https') ? 'wss:' : 'ws:';
      const host = fallbackOrigin.replace(/^https?:\/\//, '');
      return `${wsProtocol}//${host}${endpoint}`;
    }
  }, [underlying, servedExpiry]);

  const { lastMessage, readyState } = useWebSocket(streamUrl);

  // Construct API URL
  const apiUrl = useCallback(() => {
    return `/options/live?underlying=${underlying}&expiry=${servedExpiry || expiry}`;
  }, [underlying, expiry, servedExpiry]);

  // Clear stale data immediately when selection changes
  useEffect(() => {
    setData(null);
    setError(null);
    setTimestamp(null);
    setCacheStats(null);
    setRetryCount(0);
    setServedExpiry(expiry || null);
  }, [underlying, expiry]);

  // Fetch function
  const fetchChain = useCallback(async () => {
    if (!underlying || !expiry) {
      console.warn('[useAuthoritativeOptionChain] Missing underlying or expiry');
      return null;
    }

    try {
      setLoading(true);
      setError(null);

      console.log('[useAuthoritativeOptionChain] Fetching from authoritative API', underlying, expiry);
      const result = await apiService.get('/options/live', { underlying, expiry: servedExpiry || expiry });
      
      if (!result) {
        throw new Error('CACHE_MISS');
      }

      if (result.status !== 'success') {
        throw new Error(result.detail || 'API returned non-success status');
      }

      // Reset retry count on success
      setRetryCount(0);

      // Extract data
      const chainData = {
        ...(result.data || {}),
        underlying_ltp: result.underlying_ltp ?? result.data?.underlying_ltp ?? null,
      };
      
      setData(chainData);
      setTimestamp(new Date(result.timestamp));
      setCacheStats(result.cache_stats || {});
      if (result.served_expiry) {
        setServedExpiry(result.served_expiry);
      }

      console.log(
        `[useAuthoritativeOptionChain] ✅ Loaded ${chainData?.strikes ? Object.keys(chainData.strikes).length : 0} strikes for ${underlying} ${expiry}`
      );

      return chainData;

    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch option chain';
      console.error('[useAuthoritativeOptionChain] ❌', errorMsg);
      setError(errorMsg);
      // Keep last known good chain on transient failures
      
      // Increment retry count
      setRetryCount(prev => prev + 1);
      
      return null;

    } finally {
      setLoading(false);
    }
  }, [underlying, expiry, apiUrl]);

  // WebSocket push stream effect
  useEffect(() => {
    if (!autoRefresh || !underlying || !expiry || !lastMessage?.data) {
      return;
    }

    try {
      const result = JSON.parse(lastMessage.data);
      if (!result || result.status !== 'success') {
        if (result?.detail) {
          setError(result.detail);
        }
        return;
      }

      const chainData = {
        ...(result.data || {}),
        underlying_ltp: result.underlying_ltp ?? result.data?.underlying_ltp ?? null,
      };
      setData(chainData);
      setTimestamp(new Date(result.timestamp));
      setCacheStats(result.cache_stats || {});
      if (result.served_expiry) {
        setServedExpiry(result.served_expiry);
      }
      setRetryCount(0);
      setError(null);
      setLoading(false);
    } catch (_error) {
      setError('Invalid stream payload');
    }
  }, [autoRefresh, underlying, expiry, lastMessage]);

  // Initial fetch for first paint + websocket fallback
  useEffect(() => {
    if (!underlying || !expiry) {
      return;
    }

    fetchChain();
  }, [underlying, expiry, fetchChain]);

  useEffect(() => {
    if (!autoRefresh || !underlying || !expiry) {
      return;
    }
    if (readyState === WebSocket.CLOSED) {
      fetchChain();
    }
  }, [readyState, autoRefresh, underlying, expiry, fetchChain, refreshInterval]);

  // Manual refresh function
  const refresh = useCallback(() => {
    console.log('[useAuthoritativeOptionChain] Manual refresh triggered');
    setRetryCount(0); // Reset retries on manual action
    return fetchChain();
  }, [fetchChain]);

  // Helper: Get strike data by strike price
  const getStrikeData = useCallback((strike) => {
    if (!data?.strikes) return null;
    return data.strikes[strike.toString()];
  }, [data]);

  // Helper: Get all strikes as sorted array
  const getStrikesArray = useCallback(() => {
    if (!data?.strikes) return [];
    
    return Object.entries(data.strikes)
      .map(([strikeStr, strikeData]) => ({
        strike: parseFloat(strikeStr),
        ...strikeData
      }))
      .sort((a, b) => a.strike - b.strike);
  }, [data]);

  // Helper: Get ATM strike
  const getATMStrike = useCallback(() => {
    return data?.atm_strike || null;
  }, [data]);

  // Helper: Get lot size
  const getLotSize = useCallback(() => {
    return data?.lot_size || null;
  }, [data]);

  // Helper: Get available expiries for underlying
  const getAvailableExpiries = useCallback(async (underlyingSymbol) => {
    try {
      const result = await apiService.get('/options/available/expiries', { underlying: underlyingSymbol });
      if (result && result.status === 'success') return result.data || [];
      return [];

    } catch (err) {
      console.error('[useAuthoritativeOptionChain] Failed to fetch expiries:', err);
      return [];
    }
  }, []);

  // Helper: Get available underlyings
  const getAvailableUnderlyings = useCallback(async () => {
    try {
      const result = await apiService.get('/options/available/underlyings');
      if (result && result.status === 'success') return result.data || [];
      return [];

    } catch (err) {
      console.error('[useAuthoritativeOptionChain] Failed to fetch underlyings:', err);
      return [];
    }
  }, []);

  return {
    // Data
    data,
    loading,
    error,
    timestamp,
    cacheStats,
    
    // Actions
    refresh,
    
    // Helpers
    getStrikeData,
    getStrikesArray,
    getATMStrike,
    getLotSize,
    getAvailableExpiries,
    getAvailableUnderlyings,
    
    // Metadata
    strikeCount: data?.strikes ? Object.keys(data.strikes).length : 0,
    isReady: !loading && !error && data !== null,
    hasCacheStats: !!cacheStats,
    servedExpiry,
  };
};

export default useAuthoritativeOptionChain;
