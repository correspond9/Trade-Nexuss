import { useState, useEffect, useCallback } from 'react';

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
export const useAuthoritativeOptionChain = (underlying, expiry, options = {}) => {
  // State management
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [timestamp, setTimestamp] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  
  // Options with defaults
  const {
    autoRefresh = true,
    refreshInterval = 1000, // 1 second default for realtime
    pollStale = false, // Set to true to keep polling even when data is fresh
  } = options;

  // Construct API URL
  const apiUrl = useCallback(() => {
    const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
    return `${baseUrl}/options/live?underlying=${underlying}&expiry=${expiry}`;
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

      const url = apiUrl();
      console.log('[useAuthoritativeOptionChain] Fetching from:', url);

      const response = await fetch(url);

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('CACHE_MISS');
        }
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.status !== 'success') {
        throw new Error(result.detail || 'API returned non-success status');
      }

      // Extract data
      const chainData = result.data;
      
      setData(chainData);
      setTimestamp(new Date(result.timestamp));
      setCacheStats(result.cache_stats || {});

      console.log(
        `[useAuthoritativeOptionChain] ✅ Loaded ${chainData?.strikes ? Object.keys(chainData.strikes).length : 0} strikes for ${underlying} ${expiry}`
      );

      return chainData;

    } catch (err) {
      const errorMsg = err.message || 'Failed to fetch option chain';
      console.error('[useAuthoritativeOptionChain] ❌', errorMsg);
      setError(errorMsg);
      setData(null);
      return null;

    } finally {
      setLoading(false);
    }
  }, [underlying, expiry, apiUrl]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !underlying || !expiry) {
      return;
    }

    // Initial fetch
    fetchChain();

    // Set up polling interval
    const interval = setInterval(() => {
      fetchChain();
    }, refreshInterval);

    return () => clearInterval(interval);

  }, [underlying, expiry, autoRefresh, refreshInterval, fetchChain]);

  // Manual refresh function
  const refresh = useCallback(() => {
    console.log('[useAuthoritativeOptionChain] Manual refresh triggered');
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
      const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
      const url = `${baseUrl}/options/available/expiries?underlying=${underlyingSymbol}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      
      if (result.status === 'success') {
        return result.data || [];
      }
      
      return [];

    } catch (err) {
      console.error('[useAuthoritativeOptionChain] Failed to fetch expiries:', err);
      return [];
    }
  }, []);

  // Helper: Get available underlyings
  const getAvailableUnderlyings = useCallback(async () => {
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
      const url = `${baseUrl}/options/available/underlyings`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      
      if (result.status === 'success') {
        return result.data || [];
      }
      
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
  };
};

export default useAuthoritativeOptionChain;
