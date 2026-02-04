import { useState, useEffect } from 'react';

// Custom hook for localStorage with JSON serialization
export const useLocalStorage = (key, initialValue) => {
  // Get from local storage then parse stored json or return initialValue
  const readValue = () => {
    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  };

  const [storedValue, setStoredValue] = useState(readValue);

  // Return a wrapped version of useState's setter function that ...
  // ... persists the new value to localStorage.
  const setValue = (value) => {
    try {
      // Allow value to be a function so we have the same API as useState
      const valueToStore =
        value instanceof Function ? value(storedValue) : value;
      
      // Save state
      setStoredValue(valueToStore);
      
      // Save to local storage
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  };

  useEffect(() => {
    const handleStorageChange = () => {
      setStoredValue(readValue());
    };

    // this only works for other documents, not the current one
    window.addEventListener('storage', handleStorageChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  return [storedValue, setValue];
};

// Hook for storing theme preference
export const useTheme = () => {
  return useLocalStorage('theme', 'light');
};

// Hook for storing user preferences
export const useUserPreferences = () => {
  return useLocalStorage('userPreferences', {
    language: 'en',
    timezone: 'Asia/Kolkata',
    dateFormat: 'DD-MM-YYYY',
    currency: 'INR',
  });
};

// Hook for storing sidebar state
export const useSidebarState = () => {
  return useLocalStorage('sidebarOpen', true);
};

// Hook for storing table preferences (column visibility, page size, etc.)
export const useTablePreferences = (tableId) => {
  return useLocalStorage(`table_${tableId}_preferences`, {
    pageSize: 10,
    columns: {},
    sort: { column: null, direction: 'asc' },
    filters: {},
  });
};

// Hook for storing recent searches
export const useRecentSearches = (maxItems = 5) => {
  const [searches, setSearches] = useLocalStorage('recentSearches', []);

  const addSearch = (search) => {
    if (!search || typeof search !== 'string') return;
    
    const trimmedSearch = search.trim();
    if (!trimmedSearch) return;

    setSearches(prev => {
      const filtered = prev.filter(item => item !== trimmedSearch);
      const updated = [trimmedSearch, ...filtered];
      return updated.slice(0, maxItems);
    });
  };

  const clearSearches = () => {
    setSearches([]);
  };

  return [searches, { addSearch, clearSearches }];
};

// Hook for storing form data (auto-save)
export const useFormStorage = (formId, initialData = {}) => {
  const [formData, setFormData] = useLocalStorage(`form_${formId}`, initialData);

  const updateField = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const updateFields = (updates) => {
    setFormData(prev => ({
      ...prev,
      ...updates,
    }));
  };

  const clearForm = () => {
    setFormData(initialData);
  };

  return [formData, { updateField, updateFields, clearForm }];
};

// Hook for storing API cache with expiration
export const useCache = (defaultTTL = 5 * 60 * 1000) => { // 5 minutes default
  const [cache, setCache] = useLocalStorage('apiCache', {});

  const set = (key, data, ttl = defaultTTL) => {
    const item = {
      data,
      timestamp: Date.now(),
      ttl,
    };
    
    setCache(prev => ({
      ...prev,
      [key]: item,
    }));
  };

  const get = (key) => {
    const item = cache[key];
    if (!item) return null;

    const now = Date.now();
    if (now - item.timestamp > item.ttl) {
      // Expired, remove from cache
      setCache(prev => {
        const newCache = { ...prev };
        delete newCache[key];
        return newCache;
      });
      return null;
    }

    return item.data;
  };

  const clear = (key) => {
    if (key) {
      setCache(prev => {
        const newCache = { ...prev };
        delete newCache[key];
        return newCache;
      });
    } else {
      setCache({});
    }
  };

  const clearExpired = () => {
    const now = Date.now();
    const newCache = {};
    
    Object.keys(cache).forEach(key => {
      const item = cache[key];
      if (now - item.timestamp <= item.ttl) {
        newCache[key] = item;
      }
    });
    
    setCache(newCache);
  };

  return { get, set, clear, clearExpired };
};

// Hook for storing notification preferences
export const useNotificationPreferences = () => {
  return useLocalStorage('notificationPreferences', {
    email: true,
    push: true,
    sms: false,
    tradeAlerts: true,
    priceAlerts: true,
    systemAlerts: true,
  });
};

// Hook for storing dashboard layout
export const useDashboardLayout = () => {
  return useLocalStorage('dashboardLayout', {
    widgets: [
      { id: 'stats', type: 'stats', position: { x: 0, y: 0, w: 4, h: 2 } },
      { id: 'chart', type: 'chart', position: { x: 4, y: 0, w: 8, h: 4 } },
      { id: 'recent', type: 'recent', position: { x: 0, y: 2, w: 4, h: 3 } },
    ],
    locked: false,
  });
};

// Hook for storing trading preferences
export const useTradingPreferences = () => {
  return useLocalStorage('tradingPreferences', {
    defaultOrderType: 'LIMIT',
    defaultProductType: 'NORMAL',
    defaultQuantity: 1,
    confirmOrders: true,
    showAdvancedOptions: false,
    autoRefresh: true,
    refreshInterval: 5000,
  });
};