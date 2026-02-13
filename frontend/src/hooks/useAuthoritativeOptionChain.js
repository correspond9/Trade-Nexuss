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
import { apiService } from '../services/apiService';

export const useAuthoritativeOptionChain = (underlying, expiry, options = {}) => {
  // State management
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [timestamp, setTimestamp] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [retryCount, setRetryCount] = useState(0); // Add retry counter
  
  // Options with defaults
  const {
    autoRefresh = true,
    refreshInterval = 1000, // 1 second default for realtime
  } = options;

  // Construct API URL
  const apiUrl = useCallback(() => {
    return `/options/live?underlying=${underlying}&expiry=${expiry}`;
  }, [underlying, expiry]);

  // Fetch function
  const fetchChain = useCallback(async () => {
    if (!underlying || !expiry) {
      console.warn('[useAuthoritativeOptionChain] Missing underlying or expiry');
      return null;
    }

    // Prevent infinite loops if error persists
    if (retryCount > 3) {
      console.warn('[useAuthoritativeOptionChain] Max retries reached, pausing auto-refresh');
      return null;
    }

    try {
      setLoading(true);
      setError(null);

      console.log('[useAuthoritativeOptionChain] Fetching from authoritative API', underlying, expiry);
      const result = await apiService.get('/options/live', { underlying, expiry });
      
      if (!result) {
        throw new Error('CACHE_MISS');
      }

      if (result.status !== 'success') {
        throw new Error(result.detail || 'API returned non-success status');
      }

      // Reset retry count on success
      setRetryCount(0);

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
      
      // Increment retry count
      setRetryCount(prev => prev + 1);
      
      return null;

    } finally {
      setLoading(false);
    }
  }, [underlying, expiry, apiUrl, retryCount]);

  // Auto-refresh effect
  useEffect(() => {
    if (!autoRefresh || !underlying || !expiry || retryCount > 3) {
      return;
    }

    // Initial fetch
    fetchChain();

    // Set up polling interval
    const interval = setInterval(() => {
      fetchChain();
    }, refreshInterval);

    return () => clearInterval(interval);

  }, [underlying, expiry, autoRefresh, refreshInterval, fetchChain, retryCount]);

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
  };
};

export default useAuthoritativeOptionChain;
