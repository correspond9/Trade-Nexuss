import { useState, useEffect, useCallback, useMemo } from 'react';
import { apiService } from '../services/apiService';
import { useCache } from './useLocalStorage';

// Generic API hook with caching and error handling
export const useApi = (endpoint, options = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  
  const { get: getCached, set: setCached } = useCache();
  
  const {
    immediate = true,
    cache = true,
    cacheTTL = 5 * 60 * 1000, // 5 minutes
    params = {},
    dependencies = [],
    onSuccess,
    onError,
  } = options;

  const fetchData = useCallback(async (requestParams = params) => {
    setLoading(true);
    setError(null);
    
    try {
      // Check cache first
      if (cache) {
        const cacheKey = `${endpoint}?${JSON.stringify(requestParams)}`;
        const cachedData = getCached(cacheKey);
        if (cachedData) {
          setData(cachedData);
          setLastUpdated(Date.now());
          setLoading(false);
          return cachedData;
        }
      }

      // Fetch from API
      const result = await apiService.get(endpoint, requestParams);
      
      setData(result);
      setLastUpdated(Date.now());
      
      // Cache the result
      if (cache) {
        const cacheKey = `${endpoint}?${JSON.stringify(requestParams)}`;
        setCached(cacheKey, result, cacheTTL);
      }
      
      if (onSuccess) onSuccess(result);
      
      return result;
    } catch (err) {
      const errorMessage = err.message || 'An error occurred while fetching data';
      setError(errorMessage);
      
      if (onError) onError(err);
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint, params, cache, cacheTTL, getCached, setCached, onSuccess, onError]);

  const effectDeps = useMemo(() => [fetchData, immediate, ...dependencies], [fetchData, immediate, dependencies]);

  // Auto-fetch on mount and when dependencies change
  useEffect(() => {
    if (immediate) {
      fetchData();
    }
  }, effectDeps);

  const refetch = useCallback((newParams = {}) => {
    return fetchData({ ...params, ...newParams });
  }, [fetchData, params]);

  const clearCache = useCallback(() => {
    const cacheKey = `${endpoint}?${JSON.stringify(params)}`;
    setCached(cacheKey, null);
  }, [endpoint, params, setCached]);

  return {
    data,
    loading,
    error,
    lastUpdated,
    refetch,
    clearCache,
  };
};

// Hook for paginated API calls
export const usePaginatedApi = (endpoint, options = {}) => {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(options.defaultPageSize || 10);
  const [totalItems, setTotalItems] = useState(0);
  
  const params = {
    page,
    limit: pageSize,
    ...options.params,
  };

  const { data, loading, error, refetch } = useApi(endpoint, {
    ...options,
    params,
    dependencies: [page, pageSize, ...(options.dependencies || [])],
    onSuccess: (result) => {
      setTotalItems(result.total || result.length || 0);
      if (options.onSuccess) options.onSuccess(result);
    },
  });

  const goToPage = useCallback((newPage) => {
    setPage(newPage);
  }, []);

  const changePageSize = useCallback((newPageSize) => {
    setPageSize(newPageSize);
    setPage(1); // Reset to first page
  }, []);

  const nextPage = useCallback(() => {
    if (page * pageSize < totalItems) {
      setPage(page + 1);
    }
  }, [page, pageSize, totalItems]);

  const prevPage = useCallback(() => {
    if (page > 1) {
      setPage(page - 1);
    }
  }, [page]);

  const totalPages = Math.ceil(totalItems / pageSize);
  const hasNextPage = page < totalPages;
  const hasPrevPage = page > 1;

  return {
    data,
    loading,
    error,
    page,
    pageSize,
    totalItems,
    totalPages,
    hasNextPage,
    hasPrevPage,
    goToPage,
    nextPage,
    prevPage,
    changePageSize,
    refetch,
  };
};

// Hook for real-time data (WebSocket or polling)
export const useRealTimeData = (endpoint, options = {}) => {
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  
  const {
    interval = 0,
    immediate = true,
    enabled = true,
  } = options;

  useEffect(() => {
    if (!enabled) return;

    let intervalId;
    
    const fetchData = async () => {
      try {
        const result = await apiService.get(endpoint);
        setData(result);
        setConnected(true);
        setError(null);
      } catch (err) {
        setError(err.message);
        setConnected(false);
      }
    };

    if (immediate) {
      fetchData();
    }

    if (interval > 0) {
      intervalId = setInterval(fetchData, interval);
    }

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [endpoint, interval, immediate, enabled]);

  const disconnect = useCallback(() => {
    setConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    setConnected(true);
  }, []);

  return {
    data,
    connected,
    error,
    disconnect,
    reconnect,
  };
};

// Hook for mutations (POST, PUT, DELETE)
export const useMutation = (endpoint, method = 'POST') => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const mutate = useCallback(async (payload, options = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      let result;
      
      switch (method.toUpperCase()) {
        case 'POST':
          result = await apiService.post(endpoint, payload);
          break;
        case 'PUT':
          result = await apiService.put(endpoint, payload);
          break;
        case 'PATCH':
          result = await apiService.patch(endpoint, payload);
          break;
        case 'DELETE':
          result = await apiService.delete(endpoint);
          break;
        default:
          throw new Error(`Unsupported method: ${method}`);
      }
      
      setData(result);
      
      if (options.onSuccess) {
        options.onSuccess(result);
      }
      
      return result;
    } catch (err) {
      const errorMessage = err.message || 'An error occurred during the request';
      setError(errorMessage);
      
      if (options.onError) {
        options.onError(err);
      }
      
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint, method]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return {
    mutate,
    loading,
    error,
    data,
    reset,
  };
};

// Hook for file uploads
export const useFileUpload = (endpoint) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [data, setData] = useState(null);

  const upload = useCallback(async (file, additionalData = {}) => {
    setLoading(true);
    setError(null);
    setProgress(0);
    
    try {
      // Simulate progress (in real app, this would come from the upload progress event)
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      const result = await apiService.upload(endpoint, file, additionalData);
      
      clearInterval(progressInterval);
      setProgress(100);
      setData(result);
      
      return result;
    } catch (err) {
      const errorMessage = err.message || 'Upload failed';
      setError(errorMessage);
      setProgress(0);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
    setProgress(0);
  }, []);

  return {
    upload,
    loading,
    error,
    progress,
    data,
    reset,
  };
};

// Hook for infinite scrolling
export const useInfiniteScroll = (endpoint, options = {}) => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  
  const {
    pageSize = 20,
    initialData = [],
  } = options;

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = {
        page,
        limit: pageSize,
        ...options.params,
      };
      
      const result = await apiService.get(endpoint, params);
      
      if (Array.isArray(result)) {
        setData(prev => [...prev, ...result]);
        setHasMore(result.length === pageSize);
        setPage(page + 1);
      } else if (result.data && Array.isArray(result.data)) {
        setData(prev => [...prev, ...result.data]);
        setHasMore(result.data.length === pageSize);
        setPage(page + 1);
      } else {
        setHasMore(false);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint, page, pageSize, loading, hasMore, options.params]);

  const reset = useCallback(() => {
    setData(initialData);
    setPage(1);
    setHasMore(true);
    setError(null);
    setLoading(false);
  }, [initialData]);

  // Load initial data
  useEffect(() => {
    if (data.length === 0 && initialData.length > 0) {
      setData(initialData);
    } else if (data.length === 0) {
      loadMore();
    }
  }, [data.length, initialData, loadMore]);

  return {
    data,
    loading,
    error,
    hasMore,
    loadMore,
    reset,
  };
};
