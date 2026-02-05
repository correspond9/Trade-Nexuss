/**
 * Market Data Cache Service
 * Caches expiry dates, lot sizes, and other market data
 * Fetches once per day and uses cached data throughout the day
 */

class MarketDataCache {
  constructor() {
    this.cache = new Map();
    this.CACHE_KEY = 'market_data_cache';
    this.CACHE_EXPIRY_HOURS = 24; // Cache for 24 hours
    
    // Initialize cache from localStorage
    this.loadCache();
  }

  loadCache() {
    try {
      const cached = localStorage.getItem(this.CACHE_KEY);
      if (cached) {
        const data = JSON.parse(cached);
        this.cache = new Map(Object.entries(data));
      }
    } catch (error) {
      console.warn('Failed to load market data cache:', error);
      this.cache = new Map();
    }
  }

  saveCache() {
    try {
      const data = Object.fromEntries(this.cache);
      localStorage.setItem(this.CACHE_KEY, JSON.stringify(data));
    } catch (error) {
      console.warn('Failed to save market data cache:', error);
    }
  }

  isCacheValid(cacheKey) {
    const cached = this.cache.get(cacheKey);
    if (!cached) return false;
    
    const cacheTime = new Date(cached.timestamp);
    const now = new Date();
    const hoursDiff = (now - cacheTime) / (1000 * 60 * 60);
    
    return hoursDiff < this.CACHE_EXPIRY_HOURS;
  }

  async getExpiryDates(symbol) {
    const cacheKey = `expiries_${symbol}`;
    
    // Return cached data if valid
    if (this.isCacheValid(cacheKey)) {
      return this.cache.get(cacheKey).data;
    }

    // Fetch fresh data
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
      const response = await fetch(`${baseUrl}/options/available/expiries?underlying=${encodeURIComponent(symbol)}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch expiries: ${response.statusText}`);
      }

      const data = await response.json();
      
      // Process the data
      const weeklyExpiries = data.data || [];
      const monthlyExpiries = [];
      const allExpiries = weeklyExpiries.slice(0, 2);
      
      // Convert to display format
      const formatExpiry = (dateStr) => {
        const date = new Date(dateStr);
        const day = date.getDate();
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${day} ${months[date.getMonth()]}`;
      };

      const result = {
        displayExpiries: allExpiries.length > 0 ? allExpiries.map(formatExpiry) : ['30 Jan', '6 Feb'],
        isoExpiries: allExpiries.length > 0 ? allExpiries : ['2026-01-30', '2026-02-06'],
        weekly: weeklyExpiries,
        monthly: monthlyExpiries,
        allExpiries: allExpiries
      };

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: new Date().toISOString()
      });
      this.saveCache();

      return result;
      
    } catch (error) {
      console.error('Error fetching expiry dates:', error);
      
      // Return fallback data
      return {
        displayExpiries: ['30 Jan', '6 Feb'],
        isoExpiries: ['2026-01-30', '2026-02-06'],
        weekly: [],
        monthly: [],
        allExpiries: ['2026-01-30', '2026-02-06']
      };
    }
  }

  async getInstrumentData(symbol) {
    const cacheKey = `instrument_${symbol}`;
    const fallbackData = {
      'NIFTY': { lotSize: 50, strikeInterval: 50 },
      'BANKNIFTY': { lotSize: 25, strikeInterval: 100 },
      'SENSEX': { lotSize: 10, strikeInterval: 100 }
    };
    
    // Return cached data if valid
    if (this.isCacheValid(cacheKey)) {
      return this.cache.get(cacheKey).data;
    }

    // Fetch fresh data
    try {
      const baseUrl = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
      const response = await fetch(`${baseUrl}/instruments/${encodeURIComponent(symbol)}/expiries`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch instrument data: ${response.statusText}`);
      }

      const data = await response.json();
      
      const defaults = fallbackData[symbol] || fallbackData['NIFTY'];
      const result = {
        lotSize: defaults.lotSize,
        strikeInterval: defaults.strikeInterval,
        hasOptions: (data.expiries || []).length > 0,
        totalInstruments: (data.expiries || []).length,
        symbol: symbol
      };

      // Cache the result
      this.cache.set(cacheKey, {
        data: result,
        timestamp: new Date().toISOString()
      });
      this.saveCache();

      return result;
      
    } catch (error) {
      console.error('Error fetching instrument data:', error);
      
      // Return fallback data based on symbol
      return {
        ...fallbackData[symbol] || fallbackData['NIFTY'],
        hasOptions: true,
        totalInstruments: 0,
        symbol: symbol
      };
    }
  }

  async getLotSize(symbol) {
    const instrumentData = await this.getInstrumentData(symbol);
    return instrumentData.lotSize;
  }

  async getStrikeInterval(symbol) {
    const instrumentData = await this.getInstrumentData(symbol);
    return instrumentData.strikeInterval;
  }

  // Clear cache (for testing or force refresh)
  clearCache() {
    this.cache.clear();
    localStorage.removeItem(this.CACHE_KEY);
  }

  // Get cache info for debugging
  getCacheInfo() {
    const info = {
      totalEntries: this.cache.size,
      entries: [],
      validEntries: 0
    };

    for (const [key, value] of this.cache.entries()) {
      const isValid = this.isCacheValid(key);
      info.entries.push({
        key,
        timestamp: value.timestamp,
        isValid
      });
      if (isValid) info.validEntries++;
    }

    return info;
  }
}

// Export singleton instance
const marketDataCache = new MarketDataCache();
export default marketDataCache;
