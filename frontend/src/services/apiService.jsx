// API service with caching and error handling
class ApiService {
  constructor() {
    // Determine base URL: prefer runtime-config, then Vite env, then relative '/api/v2'
    let rawBase = null;
    try {
      if (typeof window !== 'undefined' && window.__RUNTIME_CONFIG__ && window.__RUNTIME_CONFIG__.API_BASE) {
        rawBase = window.__RUNTIME_CONFIG__.API_BASE;
      }
    } catch (e) {
      // ignore
    }
    rawBase = rawBase || import.meta.env.VITE_API_URL || '/api/v2';

    // In browser production, prefer same-origin API path to avoid cross-origin/CORS/proxy drift.
    try {
      if (typeof window !== 'undefined' && window.location) {
        const host = (window.location.hostname || '').toLowerCase();
        const isProdHost = host === 'tradingnexus.pro' || host === 'www.tradingnexus.pro' || host === 'app.tradingnexus.pro';
        const isLocalHost = host === 'localhost' || host === '127.0.0.1';
        if (isProdHost) {
          rawBase = '/api/v2';
        } else if (isLocalHost && (!rawBase || rawBase === '/api/v2' || rawBase === '/api' || rawBase === '/api/v1')) {
          rawBase = 'http://127.0.0.1:8000/api/v2';
        }
      }
    } catch (_e) {
      // ignore and continue with configured base
    }

    const normalizeBase = (value) => {
      const fallback = '/api/v2';
      try {
        const text = String(value || '').trim();
        if (!text) return fallback;
        if (text.startsWith('/')) {
          const trimmed = text.replace(/\/+$/, '');
          if (trimmed === '/api' || trimmed === '/api/v1' || trimmed === '/api/v2') {
            return '/api/v2';
          }
          return trimmed;
        }
        const url = new URL(text);
        const path = (url.pathname || '/').replace(/\/+$/, '');
        if (!path || path === '/') {
          url.pathname = '/api/v2';
          return url.toString().replace(/\/+$/, '');
        }
        if (path === '/api' || path === '/api/v1' || path === '/api/v2') {
          url.pathname = '/api/v2';
          return url.toString().replace(/\/+$/, '');
        }
        return url.toString().replace(/\/+$/, '');
      } catch (_e) {
        return String(value).replace(/\/+$/, '') || fallback;
      }
    };
    this.baseURL = normalizeBase(rawBase);
    this.cache = new Map();
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    this.useMockData = false;
    this.authToken = null;
    // Initialize auth token from localStorage if present (supports reloads)
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const stored = localStorage.getItem('authToken') || localStorage.getItem('token');
        if (stored) this.authToken = stored;
      }
    } catch (e) {
      // ignore if localStorage not available
    }
    // Monkey-patch global fetch to prepend baseURL for relative paths (e.g., fetch('/admin/...'))
    try {
      if (typeof window !== 'undefined' && window.fetch && !window.__API_SERVICE_FETCH_PATCHED__) {
        const originalFetch = window.fetch.bind(window);
        const buildAbsoluteFromBaseOrigin = (path) => {
          try {
            const base = new URL(this.baseURL, window.location.origin);
            return `${base.origin}${path}`;
          } catch (_e) {
            return path;
          }
        };
        window.fetch = (input, init) => {
          try {
            if (typeof input === 'string' && input.startsWith('/')) {
              if (input.startsWith('/api/v1') || input.startsWith('/api/v2')) {
                input = buildAbsoluteFromBaseOrigin(input);
              } else {
                input = `${this.baseURL}${input}`;
              }
            } else if (input && input.url && typeof input.url === 'string' && input.url.startsWith('/')) {
              const url = input.url;
              if (url.startsWith('/api/v1') || url.startsWith('/api/v2')) {
                input = new Request(buildAbsoluteFromBaseOrigin(url), input);
              } else {
                input = new Request(`${this.baseURL}${url}`, input);
              }
            }
          } catch (e) {
            // fall through to original fetch
          }
          return originalFetch(input, init);
        };
        window.__API_SERVICE_FETCH_PATCHED__ = true;
      }
    } catch (e) {
      // ignore patch failures in non-browser environments
    }
  }

  setAuthToken(token) {
    this.authToken = token;
  }

  getAuthHeaders() {
    const headers = this.authToken ? { Authorization: `Bearer ${this.authToken}` } : {};

    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const rawUser = localStorage.getItem('authUser') || localStorage.getItem('user');
        if (rawUser) {
          const parsed = JSON.parse(rawUser);
          const xUser = (parsed?.user_id || parsed?.mobile || parsed?.username || '').toString().trim();
          if (xUser) {
            headers['X-USER'] = xUser;
          }
        }
      }
    } catch (e) {
      // ignore malformed localStorage user payload
    }

    return headers;
  }

  // Remove credential-like fields from outgoing JSON bodies to avoid accidental leakage
  // EXCEPTION: Allow credentials to be sent to /credentials/save
  sanitizeBody(obj, url) {
    // If the URL is for saving credentials, DO NOT sanitize
    if (url && url.includes('/credentials/save')) {
      console.log('Allowing credential save payload:', obj);
      return obj;
    }
    if (url && url.includes('/auth/login')) {
      return obj;
    }

    const SENSITIVE_KEYS = new Set([
      'api_key','apiKey','api_secret','apiSecret','secret_api','secret',
      'client_id','clientId','access_token','accessToken','auth_token','authToken',
      'daily_token','dailyToken'
    ]);

    const _recurse = (val) => {
      if (val == null) return val;
      if (typeof val !== 'object') return val;
      if (typeof FormData !== 'undefined' && val instanceof FormData) return val;
      if (Array.isArray(val)) return val.map(_recurse);
      const out = {};
      Object.keys(val).forEach((k) => {
        if (SENSITIVE_KEYS.has(k)) return; // skip sensitive key
        out[k] = _recurse(val[k]);
      });
      return out;
    };

    try {
      return _recurse(obj);
    } catch (e) {
      return obj;
    }
  }

  // Helper function to generate dynamic expiry dates based on symbol type
  generateExpiryDates(symbol = 'NIFTY') {
    const now = new Date();
    const currentMonth = now.getMonth();
    const currentYear = now.getFullYear();
    const weeklySymbols = ['NIFTY', 'SENSEX', 'FINNIFTY', 'MIDCPNIFTY'];
    const normalizedSymbol = (symbol || '').toUpperCase().trim();
    const isWeeklySymbol = weeklySymbols.includes(normalizedSymbol);

    const formatExpiry = (date) => {
      const day = date.getDate();
      const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
      return `${day}${months[date.getMonth()]}`;
    };

    if (isWeeklySymbol) {
      // Weekly expiry logic for NIFTY and SENSEX (every Thursday)
      const currentDay = now.getDay();
      const daysUntilThursday = (4 - currentDay + 7) % 7 || 7; // Next Thursday

      const currentWeeklyExpiry = new Date(now);
      currentWeeklyExpiry.setDate(now.getDate() + daysUntilThursday);

      const nextWeeklyExpiry = new Date(currentWeeklyExpiry);
      nextWeeklyExpiry.setDate(currentWeeklyExpiry.getDate() + 7); // Next week Thursday

      return {
        current: formatExpiry(currentWeeklyExpiry),
        next: formatExpiry(nextWeeklyExpiry),
        currentFull: currentWeeklyExpiry.toISOString().split('T')[0],
        nextFull: nextWeeklyExpiry.toISOString().split('T')[0]
      };
    } else {
      // Monthly expiry logic for BANKNIFTY and others (last Thursday of month)
      const currentExpiry = new Date(currentYear, currentMonth + 1, 0); // Last day of current month
      while (currentExpiry.getDay() !== 4) { // Find last Thursday
        currentExpiry.setDate(currentExpiry.getDate() - 1);
      }

      const nextExpiry = new Date(currentYear, currentMonth + 2, 0); // Last day of next month
      while (nextExpiry.getDay() !== 4) { // Find last Thursday
        nextExpiry.setDate(nextExpiry.getDate() - 1);
      }

      return {
        current: formatExpiry(currentExpiry),
        next: formatExpiry(nextExpiry),
        currentFull: currentExpiry.toISOString().split('T')[0],
        nextFull: nextExpiry.toISOString().split('T')[0]
      };
    }
  }

  // Mock data methods
  getMockData(endpoint, params = {}) {
    const expiries = this.generateExpiryDates();

    const mockInstruments = {
      'NSE': [
        { id: '260105', symbol: `NIFTY ${expiries.current} 25000 CE`, ltp: 363.90, change: -36.44, changePercent: -9.10, lotSize: 50, expiry: expiries.current, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 25000 },
        { id: '260106', symbol: `NIFTY ${expiries.current} 25100 CE`, ltp: 283.60, change: -40.02, changePercent: -12.36, lotSize: 50, expiry: expiries.current, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 25100 },
        { id: '260107', symbol: `NIFTY ${expiries.current} 25200 CE`, ltp: 164.80, change: -56.63, changePercent: -25.58, lotSize: 50, expiry: expiries.current, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 25200 },
        { id: '260108', symbol: `NIFTY ${expiries.next} 25000 PE`, ltp: 125.30, change: 12.45, changePercent: 5.35, lotSize: 50, expiry: expiries.next, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 25000 },
        { id: '260109', symbol: `BANKNIFTY ${expiries.current} 46000 CE`, ltp: 245.30, change: 12.45, changePercent: 5.35, lotSize: 25, expiry: expiries.current, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 46000 },
        { id: '260110', symbol: `BANKNIFTY ${expiries.next} 46500 PE`, ltp: 189.50, change: -8.75, changePercent: -4.41, lotSize: 25, expiry: expiries.next, exchange: 'NSE', instrument_type: 'OPTIDX', strike: 46500 },
        { id: '260111', symbol: 'RELIANCE', ltp: 2845.60, change: 15.20, changePercent: 0.54, lotSize: 1, expiry: '', exchange: 'NSE', instrument_type: 'EQUITY' },
        { id: '260112', symbol: 'TCS', ltp: 4125.40, change: -8.60, changePercent: -0.21, lotSize: 1, expiry: '', exchange: 'NSE', instrument_type: 'EQUITY' },
      ],
      'BSE': [
        { id: '438088', symbol: `SENSEX ${expiries.current} 79500 PE`, ltp: 245.80, change: 12.40, changePercent: 5.31, lotSize: 10, expiry: expiries.current, exchange: 'BSE', instrument_type: 'OPTIDX', strike: 79500 },
        { id: '438089', symbol: `SENSEX ${expiries.next} 80000 CE`, ltp: 189.50, change: -8.75, changePercent: -4.41, lotSize: 10, expiry: expiries.next, exchange: 'BSE', instrument_type: 'OPTIDX', strike: 80000 },
      ],
      'MCX': [
        { id: '534982', symbol: `CRUDEOIL ${expiries.current} 6400 CE`, ltp: 125.50, change: -15.30, changePercent: -10.85, lotSize: 100, expiry: expiries.current, exchange: 'MCX', instrument_type: 'OPTCOM', strike: 6400 },
        { id: '534983', symbol: `CRUDEOIL ${expiries.current} 6300 PE`, ltp: 98.25, change: 5.45, changePercent: 5.88, lotSize: 100, expiry: expiries.current, exchange: 'MCX', instrument_type: 'OPTCOM', strike: 6300 },
        { id: '534984', symbol: 'CRUDEOIL', ltp: 6250.40, change: 45.20, changePercent: 0.73, lotSize: 100, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534985', symbol: `CRUDEOIL ${expiries.next}`, ltp: 6285.60, change: 35.40, changePercent: 0.57, lotSize: 100, expiry: expiries.next, exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534986', symbol: `GOLD ${expiries.current} 62000 CE`, ltp: 245.80, change: 8.90, changePercent: 3.76, lotSize: 1, expiry: expiries.current, exchange: 'MCX', instrument_type: 'OPTCOM', strike: 62000 },
        { id: '534987', symbol: 'GOLD', ltp: 62450.30, change: 125.60, changePercent: 0.20, lotSize: 1, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534988', symbol: `SILVER ${expiries.current} 72000 CE`, ltp: 185.40, change: -3.20, changePercent: -1.70, lotSize: 1, expiry: expiries.current, exchange: 'MCX', instrument_type: 'OPTCOM', strike: 72000 },
        { id: '534989', symbol: 'SILVER', ltp: 72580.90, change: -245.30, changePercent: -0.34, lotSize: 1, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534990', symbol: 'NATURALGAS', ltp: 185.60, change: 2.80, changePercent: 1.53, lotSize: 1250, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534991', symbol: 'COPPER', ltp: 745.20, change: -5.40, changePercent: -0.72, lotSize: 1000, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534992', symbol: 'ZINC', ltp: 245.85, change: 1.25, changePercent: 0.51, lotSize: 1000, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
        { id: '534993', symbol: 'ALUMINIUM', ltp: 185.40, change: -2.15, changePercent: -1.15, lotSize: 1000, expiry: '', exchange: 'MCX', instrument_type: 'COMMODITY' },
      ]
    };

    // Handle instrument search endpoints
    if (endpoint.startsWith('/market/instruments/')) {
      const exchange = endpoint.split('/').pop();
      let instruments = mockInstruments[exchange] || [];

      // Filter by search term if provided
      if (params.search && params.search.trim()) {
        const searchTerm = params.search.toLowerCase().trim();
        instruments = instruments.filter(instrument =>
          instrument.symbol.toLowerCase().includes(searchTerm) ||
          instrument.instrument_type.toLowerCase().includes(searchTerm) ||
          instrument.exchange.toLowerCase().includes(searchTerm)
        );
      }

      return {
        success: true,
        data: instruments
      };
    }

    // Handle Dhan instruments endpoint
    if (endpoint === '/market/dhan/instruments') {
      // Generate mock Dhan instruments based on real subscription data
      const mockDhanInstruments = [
        { id: 'NIFTY1100CE', symbol: 'NIFTY 1100 CE', name: 'NIFTY 1100 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1100, option_type: 'CE', lot_size: 50, ltp: 125.50, change: 2.30, changePercent: 1.87 },
        { id: 'NIFTY1150CE', symbol: 'NIFTY 1150 CE', name: 'NIFTY 1150 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1150, option_type: 'CE', lot_size: 50, ltp: 89.25, change: -1.75, changePercent: -1.92 },
        { id: 'NIFTY1200CE', symbol: 'NIFTY 1200 CE', name: 'NIFTY 1200 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1200, option_type: 'CE', lot_size: 50, ltp: 58.75, change: 3.20, changePercent: 5.76 },
        { id: 'NIFTY1100PE', symbol: 'NIFTY 1100 PE', name: 'NIFTY 1100 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1100, option_type: 'PE', lot_size: 50, ltp: 45.30, change: -2.15, changePercent: -4.53 },
        { id: 'NIFTY1150PE', symbol: 'NIFTY 1150 PE', name: 'NIFTY 1150 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1150, option_type: 'PE', lot_size: 50, ltp: 68.90, change: 4.75, changePercent: 7.41 },
        { id: 'NIFTY1200PE', symbol: 'NIFTY 1200 PE', name: 'NIFTY 1200 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 1200, option_type: 'PE', lot_size: 50, ltp: 95.60, change: -3.80, changePercent: -3.82 },
        { id: 'BANKNIFTY44000CE', symbol: 'BANKNIFTY 44000 CE', name: 'BANKNIFTY 44000 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 44000, option_type: 'CE', lot_size: 25, ltp: 245.30, change: 12.45, changePercent: 5.35 },
        { id: 'BANKNIFTY44500CE', symbol: 'BANKNIFTY 44500 CE', name: 'BANKNIFTY 44500 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 44500, option_type: 'CE', lot_size: 25, ltp: 189.50, change: -8.75, changePercent: -4.41 },
        { id: 'BANKNIFTY44000PE', symbol: 'BANKNIFTY 44000 PE', name: 'BANKNIFTY 44000 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 44000, option_type: 'PE', lot_size: 25, ltp: 125.80, change: 6.90, changePercent: 5.81 },
        { id: 'BANKNIFTY44500PE', symbol: 'BANKNIFTY 44500 PE', name: 'BANKNIFTY 44500 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 44500, option_type: 'PE', lot_size: 25, ltp: 168.40, change: -4.20, changePercent: -2.44 },
        { id: 'SENSEX75000CE', symbol: 'SENSEX 75000 CE', name: 'SENSEX 75000 CE', exchange: 'BSE_INDEX', instrument_type: 'OPTIONS', strike: 75000, option_type: 'CE', lot_size: 10, ltp: 425.60, change: 15.30, changePercent: 3.73 },
        { id: 'SENSEX75500CE', symbol: 'SENSEX 75500 CE', name: 'SENSEX 75500 CE', exchange: 'BSE_INDEX', instrument_type: 'OPTIONS', strike: 75500, option_type: 'CE', lot_size: 10, ltp: 389.25, change: -6.80, changePercent: -1.72 },
        { id: 'SENSEX75000PE', symbol: 'SENSEX 75000 PE', name: 'SENSEX 75000 PE', exchange: 'BSE_INDEX', instrument_type: 'OPTIONS', strike: 75000, option_type: 'PE', lot_size: 10, ltp: 185.40, change: 8.90, changePercent: 5.05 },
        { id: 'SENSEX75500PE', symbol: 'SENSEX 75500 PE', name: 'SENSEX 75500 PE', exchange: 'BSE_INDEX', instrument_type: 'OPTIONS', strike: 75500, option_type: 'PE', lot_size: 10, ltp: 212.75, change: -3.25, changePercent: -1.50 },
        { id: 'FINNIFTY18000CE', symbol: 'FINNIFTY 18000 CE', name: 'FINNIFTY 18000 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 18000, option_type: 'CE', lot_size: 40, ltp: 145.80, change: 5.20, changePercent: 3.69 },
        { id: 'FINNIFTY18100CE', symbol: 'FINNIFTY 18100 CE', name: 'FINNIFTY 18100 CE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 18100, option_type: 'CE', lot_size: 40, ltp: 98.45, change: -2.35, changePercent: -2.33 },
        { id: 'FINNIFTY18000PE', symbol: 'FINNIFTY 18000 PE', name: 'FINNIFTY 18000 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 18000, option_type: 'PE', lot_size: 40, ltp: 78.90, change: 3.15, changePercent: 4.15 },
        { id: 'FINNIFTY18100PE', symbol: 'FINNIFTY 18100 PE', name: 'FINNIFTY 18100 PE', exchange: 'NSE_INDEX', instrument_type: 'OPTIONS', strike: 18100, option_type: 'PE', lot_size: 40, ltp: 105.60, change: -1.80, changePercent: -1.68 }
      ];

      let instruments = mockDhanInstruments;

      // Filter by search term if provided
      if (params.search && params.search.trim()) {
        const searchTerm = params.search.toLowerCase().trim();
        instruments = instruments.filter(instrument =>
          instrument.symbol.toLowerCase().includes(searchTerm) ||
          instrument.name.toLowerCase().includes(searchTerm) ||
          instrument.exchange.toLowerCase().includes(searchTerm)
        );
      }

      // Filter by exchange if provided
      if (params.exchange && params.exchange.trim()) {
        const exchange = params.exchange.toUpperCase();
        instruments = instruments.filter(instrument =>
          instrument.exchange.toUpperCase() === exchange
        );
      }

      // Sort by relevance
      if (params.search) {
        const searchLower = params.search.toLowerCase();
        instruments.sort((a, b) => {
          const aSymbol = a.symbol.toLowerCase();
          const bSymbol = b.symbol.toLowerCase();

          // Exact match first
          if (aSymbol === searchLower && bSymbol !== searchLower) return -1;
          if (bSymbol === searchLower && aSymbol !== searchLower) return 1;

          // Prefix match next
          if (aSymbol.startsWith(searchLower) && !bSymbol.startsWith(searchLower)) return -1;
          if (bSymbol.startsWith(searchLower) && !aSymbol.startsWith(searchLower)) return 1;

          // Contains match last
          if (aSymbol.includes(searchLower) && !bSymbol.includes(searchLower)) return -1;
          if (bSymbol.includes(searchLower) && !aSymbol.includes(searchLower)) return 1;

          return 0;
        });
      }

      // Limit results
      const limit = params.limit || 50;
      instruments = instruments.slice(0, limit);

      return {
        success: true,
        data: instruments
      };
    }

    const mockData = {
      '/users': [
        {
          id: 'user-1',
          clientID: 'U1001',
          firstName: 'C.K.',
          lastName: 'Nanaiah',
          email: 'shthit7@gmail.com',
          mobile: '919116555669',
          createdOn: '07-07-2025',
          walletBalance: 1500.0,
          status: 'ACTIVE',
          tradingMode: 'PAPER',
          allocatedMargin: 100000.0,
          pan: 'BDXP9731L',
          aadhar: '293832914915',
          bank: 'HDFC0001234',
          profit: 4,
          sl: -2,
          trialBy: 1,
          trialAfter: 3,
        },
        {
          id: 'user-2',
          clientID: 'U1002',
          firstName: 'Dhruv',
          lastName: 'Gohil',
          email: 'dhruv@example.com',
          mobile: '919819385642',
          createdOn: '07-07-2025',
          walletBalance: 500.5,
          status: 'BLOCKED',
          tradingMode: 'LIVE',
          allocatedMargin: 50000.0,
          pan: 'ABCDE1234F',
          aadhar: '112233445566',
          bank: 'ICIC0005678',
          profit: 10,
          sl: -5,
          trialBy: 0,
          trialAfter: 0,
        },
      ],
      '/orders': [
        {
          id: 'ord-1',
          symbol: 'NIFTY DEC 26100 CE',
          side: 'SELL',
          quantity: 150,
          price: 135.05,
          status: 'EXECUTED',
          time: '09:15:00',
          userId: 'U1001',
        },
        {
          id: 'ord-2',
          symbol: 'NIFTY DEC 26000 CE',
          side: 'BUY',
          quantity: 75,
          price: 141.70,
          status: 'EXECUTED',
          time: '09:30:00',
          userId: 'U1002',
        },
      ],
      '/baskets': [
        {
          id: 'basket-1',
          name: 'Strangle Strategy',
          type: 'STRANGLE',
          description: 'NIFTY Strangle for weekly expiry',
          requiredMargin: 85000,
          status: 'ACTIVE',
          legs: [
            {
              id: 'leg-1',
              side: 'SELL',
              symbol: 'NIFTY AUG 25100 PE',
              productType: 'NORMAL',
              qty: 10,
              price: 23.40,
              exchange: 'NSE',
            },
            {
              id: 'leg-2',
              side: 'SELL',
              symbol: 'NIFTY AUG 25150 CE',
              productType: 'NORMAL',
              qty: 10,
              price: 20.35,
              exchange: 'NSE',
            },
          ],
          createdAt: '2025-01-19T09:15:00Z',
          lastModified: '2025-01-19T14:30:00Z',
        },
      ],
      '/positions': [
        {
          id: 'pos-1',
          symbol: 'NIFTY DEC 26100 CE',
          productType: 'MIS',
          quantity: 150,
          avgPrice: 135.05,
          ltp: 130.25,
          pnl: -592.50,
          status: 'OPEN',
          userId: 'U1001',
        },
        {
          id: 'pos-2',
          symbol: 'NIFTY DEC 26000 CE',
          productType: 'NORMAL',
          quantity: 75,
          avgPrice: 141.70,
          ltp: 165.00,
          pnl: 1747.50,
          status: 'OPEN',
          userId: 'U1002',
        },
      ],
      '/quotes': {
        'NIFTY': {
          symbol: 'NIFTY',
          last_price: 24678.50,
          change: 125.30,
          change_percent: 0.51,
          exchange: 'NSE_INDEX',
          expiry_date: expiries.currentFull,
          next_expiry: expiries.nextFull
        },
        'BANKNIFTY': {
          symbol: 'BANKNIFTY',
          last_price: 23456.80,
          change: -89.20,
          change_percent: -0.38,
          exchange: 'NSE_INDEX',
          expiry_date: expiries.currentFull,
          next_expiry: expiries.nextFull
        },
        'SENSEX': {
          symbol: 'SENSEX',
          last_price: 81234.60,
          change: 234.50,
          change_percent: 0.29,
          exchange: 'BSE_INDEX',
          expiry_date: expiries.currentFull,
          next_expiry: expiries.nextFull
        },
        'CRUDEOIL': {
          symbol: 'CRUDEOIL',
          last_price: 6250.40,
          change: 45.20,
          change_percent: 0.73,
          exchange: 'MCX',
          expiry_date: expiries.currentFull,
          next_expiry: expiries.nextFull
        }
      },
      '/optionchain': {
        'NIFTY': {
          'current': [
            { strike: 22500, ltpCE: 152.96, ltpPE: 0.50, oiCE: 125000, oiPE: 98000 },
            { strike: 22550, ltpCE: 149.35, ltpPE: 0.50, oiCE: 118000, oiPE: 105000 },
            { strike: 22600, ltpCE: 134.98, ltpPE: 0.50, oiCE: 95000, oiPE: 112000 },
            { strike: 22650, ltpCE: 108.76, ltpPE: 0.50, oiCE: 88000, oiPE: 125000 },
            { strike: 22700, ltpCE: 97.93, ltpPE: 0.50, oiCE: 78000, oiPE: 134000 },
            { strike: 22750, ltpCE: 94.64, ltpPE: 0.50, oiCE: 71000, oiPE: 142000 },
            { strike: 22800, ltpCE: 66.79, ltpPE: 0.50, oiCE: 65000, oiPE: 155000 },
            { strike: 22850, ltpCE: 61.67, ltpPE: 0.50, oiCE: 59000, oiPE: 168000 },
            { strike: 22900, ltpCE: 45.75, ltpPE: 0.50, oiCE: 54000, oiPE: 182000 },
            { strike: 22950, ltpCE: 30.92, ltpPE: 0.50, oiCE: 48000, oiPE: 195000 },
            { strike: 23000, ltpCE: 15.97, ltpPE: 4.52, oiCE: 43000, oiPE: 208000 },
            { strike: 23050, ltpCE: 1.60, ltpPE: 31.16, oiCE: 38000, oiPE: 220000 },
            { strike: 23100, ltpCE: 0.50, ltpPE: 38.08, oiCE: 35000, oiPE: 195000 },
            { strike: 23150, ltpCE: 0.50, ltpPE: 61.32, oiCE: 32000, oiPE: 182000 },
            { strike: 23200, ltpCE: 0.50, ltpPE: 58.42, oiCE: 30000, oiPE: 168000 },
            { strike: 23250, ltpCE: 0.50, ltpPE: 92.51, oiCE: 28000, oiPE: 155000 },
            { strike: 23300, ltpCE: 0.50, ltpPE: 103.47, oiCE: 26000, oiPE: 142000 },
            { strike: 23350, ltpCE: 0.50, ltpPE: 117.09, oiCE: 24000, oiPE: 134000 },
            { strike: 23400, ltpCE: 0.50, ltpPE: 129.00, oiCE: 22000, oiPE: 125000 },
            { strike: 23450, ltpCE: 0.50, ltpPE: 134.32, oiCE: 20000, oiPE: 118000 },
            { strike: 23500, ltpCE: 0.50, ltpPE: 149.41, oiCE: 18000, oiPE: 105000 }
          ],
          'next': [
            { strike: 22500, ltpCE: 167.71, ltpPE: 0.50, oiCE: 135000, oiPE: 88000 },
            { strike: 22550, ltpCE: 145.52, ltpPE: 0.50, oiCE: 128000, oiPE: 95000 },
            { strike: 22600, ltpCE: 134.34, ltpPE: 0.50, oiCE: 105000, oiPE: 102000 },
            { strike: 22650, ltpCE: 116.64, ltpPE: 0.50, oiCE: 98000, oiPE: 115000 },
            { strike: 22700, ltpCE: 94.68, ltpPE: 0.50, oiCE: 82000, oiPE: 124000 },
            { strike: 22750, ltpCE: 78.92, ltpPE: 0.50, oiCE: 75000, oiPE: 132000 },
            { strike: 22800, ltpCE: 67.16, ltpPE: 0.50, oiCE: 68000, oiPE: 145000 },
            { strike: 22850, ltpCE: 47.63, ltpPE: 0.50, oiCE: 62000, oiPE: 158000 },
            { strike: 22900, ltpCE: 48.71, ltpPE: 0.50, oiCE: 56000, oiPE: 172000 },
            { strike: 22950, ltpCE: 25.55, ltpPE: 0.50, oiCE: 51000, oiPE: 185000 },
            { strike: 23000, ltpCE: 8.43, ltpPE: 0.50, oiCE: 46000, oiPE: 198000 },
            { strike: 23050, ltpCE: 0.50, ltpPE: 31.21, oiCE: 41000, oiPE: 210000 },
            { strike: 23100, ltpCE: 0.50, ltpPE: 38.74, oiCE: 38000, oiPE: 195000 },
            { strike: 23150, ltpCE: 0.50, ltpPE: 61.84, oiCE: 35000, oiPE: 182000 },
            { strike: 23200, ltpCE: 0.50, ltpPE: 65.74, oiCE: 32000, oiPE: 168000 },
            { strike: 23250, ltpCE: 0.50, ltpPE: 87.31, oiCE: 29000, oiPE: 155000 },
            { strike: 23300, ltpCE: 0.50, ltpPE: 95.56, oiCE: 27000, oiPE: 142000 },
            { strike: 23350, ltpCE: 0.50, ltpPE: 109.78, oiCE: 25000, oiPE: 134000 },
            { strike: 23400, ltpCE: 0.50, ltpPE: 133.17, oiCE: 23000, oiPE: 125000 },
            { strike: 23450, ltpCE: 0.50, ltpPE: 149.46, oiCE: 21000, oiPE: 118000 },
            { strike: 23500, ltpCE: 0.50, ltpPE: 159.29, oiCE: 19000, oiPE: 105000 }
          ]
        },
        'BANKNIFTY': {
          'current': [
            { strike: 46000, ltpCE: 245.30, ltpPE: 0.50, oiCE: 95000, oiPE: 78000 },
            { strike: 46050, ltpCE: 198.75, ltpPE: 0.50, oiCE: 88000, oiPE: 82000 },
            { strike: 46100, ltpCE: 156.30, ltpPE: 0.50, oiCE: 82000, oiPE: 85000 },
            { strike: 46150, ltpCE: 118.90, ltpPE: 0.50, oiCE: 78000, oiPE: 88000 },
            { strike: 46200, ltpCE: 85.25, ltpPE: 0.50, oiCE: 72000, oiPE: 92000 },
            { strike: 46250, ltpCE: 56.60, ltpPE: 0.50, oiCE: 68000, oiPE: 95000 },
            { strike: 46300, ltpCE: 32.85, ltpPE: 0.50, oiCE: 62000, oiPE: 98000 },
            { strike: 46350, ltpCE: 14.45, ltpPE: 0.50, oiCE: 58000, oiPE: 102000 },
            { strike: 46400, ltpCE: 5.30, ltpPE: 12.25, oiCE: 54000, oiPE: 105000 },
            { strike: 46450, ltpCE: 0.50, ltpPE: 28.16, oiCE: 50000, oiPE: 108000 },
            { strike: 46500, ltpCE: 0.50, ltpPE: 45.08, oiCE: 46000, oiPE: 112000 },
            { strike: 46550, ltpCE: 0.50, ltpPE: 67.84, oiCE: 43000, oiPE: 115000 },
            { strike: 46600, ltpCE: 0.50, ltpPE: 94.25, oiCE: 40000, oiPE: 118000 },
            { strike: 46650, ltpCE: 0.50, ltpPE: 124.30, oiCE: 38000, oiPE: 122000 },
            { strike: 46700, ltpCE: 0.50, ltpPE: 157.45, oiCE: 35000, oiPE: 125000 },
            { strike: 46750, ltpCE: 0.50, ltpPE: 193.90, oiCE: 32000, oiPE: 128000 },
            { strike: 46800, ltpCE: 0.50, ltpPE: 233.15, oiCE: 30000, oiPE: 132000 },
            { strike: 46850, ltpCE: 0.50, ltpPE: 274.80, oiCE: 28000, oiPE: 135000 },
            { strike: 46900, ltpCE: 0.50, ltpPE: 318.45, oiCE: 26000, oiPE: 138000 },
            { strike: 46950, ltpCE: 0.50, ltpPE: 364.30, oiCE: 24000, oiPE: 142000 },
            { strike: 47000, ltpCE: 0.50, ltpPE: 412.41, oiCE: 22000, oiPE: 145000 }
          ],
          'next': [
            { strike: 46000, ltpCE: 267.85, ltpPE: 0.50, oiCE: 98000, oiPE: 75000 },
            { strike: 46050, ltpCE: 218.95, ltpPE: 0.50, oiCE: 91000, oiPE: 79000 },
            { strike: 46100, ltpCE: 174.30, ltpPE: 0.50, oiCE: 85000, oiPE: 82000 },
            { strike: 46150, ltpCE: 134.90, ltpPE: 0.50, oiCE: 81000, oiPE: 85000 },
            { strike: 46200, ltpCE: 100.25, ltpPE: 0.50, oiCE: 75000, oiPE: 89000 },
            { strike: 46250, ltpCE: 70.60, ltpPE: 0.50, oiCE: 71000, oiPE: 92000 },
            { strike: 46300, ltpCE: 46.85, ltpPE: 0.50, oiCE: 65000, oiPE: 95000 },
            { strike: 46350, ltpCE: 28.45, ltpPE: 0.50, oiCE: 61000, oiPE: 99000 },
            { strike: 46400, ltpCE: 15.30, ltpPE: 18.25, oiCE: 57000, oiPE: 102000 },
            { strike: 46450, ltpCE: 0.50, ltpPE: 34.16, oiCE: 53000, oiPE: 105000 },
            { strike: 46500, ltpCE: 0.50, ltpPE: 51.08, oiCE: 49000, oiPE: 109000 },
            { strike: 46550, ltpCE: 0.50, ltpPE: 73.84, oiCE: 46000, oiPE: 112000 },
            { strike: 46600, ltpCE: 0.50, ltpPE: 100.25, oiCE: 43000, oiPE: 115000 },
            { strike: 46650, ltpCE: 0.50, ltpPE: 130.30, oiCE: 41000, oiPE: 119000 },
            { strike: 46700, ltpCE: 0.50, ltpPE: 163.45, oiCE: 38000, oiPE: 122000 },
            { strike: 46750, ltpCE: 0.50, ltpPE: 199.90, oiCE: 35000, oiPE: 125000 },
            { strike: 46800, ltpCE: 0.50, ltpPE: 239.15, oiCE: 33000, oiPE: 129000 },
            { strike: 46850, ltpCE: 0.50, ltpPE: 280.80, oiCE: 31000, oiPE: 132000 },
            { strike: 46900, ltpCE: 0.50, ltpPE: 324.45, oiCE: 29000, oiPE: 135000 },
            { strike: 46950, ltpCE: 0.50, ltpPE: 370.30, oiCE: 27000, oiPE: 139000 },
            { strike: 47000, ltpCE: 0.50, ltpPE: 418.41, oiCE: 25000, oiPE: 142000 }
          ]
        },
        'SENSEX': {
          'current': [
            { strike: 81000, ltpCE: 345.60, ltpPE: 0.50, oiCE: 85000, oiPE: 68000 },
            { strike: 81100, ltpCE: 298.75, ltpPE: 0.50, oiCE: 78000, oiPE: 72000 },
            { strike: 81200, ltpCE: 256.30, ltpPE: 0.50, oiCE: 72000, oiPE: 75000 },
            { strike: 81300, ltpCE: 218.90, ltpPE: 0.50, oiCE: 68000, oiPE: 78000 },
            { strike: 81400, ltpCE: 185.25, ltpPE: 0.50, oiCE: 62000, oiPE: 82000 },
            { strike: 81500, ltpCE: 156.60, ltpPE: 0.50, oiCE: 58000, oiPE: 85000 },
            { strike: 81600, ltpCE: 132.85, ltpPE: 0.50, oiCE: 52000, oiPE: 88000 },
            { strike: 81700, ltpCE: 114.45, ltpPE: 0.50, oiCE: 48000, oiPE: 92000 },
            { strike: 81800, ltpCE: 100.30, ltpPE: 2.25, oiCE: 44000, oiPE: 95000 },
            { strike: 81900, ltpCE: 90.50, ltpPE: 8.16, oiCE: 40000, oiPE: 98000 },
            { strike: 82000, ltpCE: 85.08, ltpPE: 15.08, oiCE: 36000, oiPE: 102000 },
            { strike: 82100, ltpCE: 83.84, ltpPE: 27.84, oiCE: 33000, oiPE: 105000 },
            { strike: 82200, ltpCE: 86.25, ltpPE: 44.25, oiCE: 30000, oiPE: 108000 },
            { strike: 82300, ltpCE: 92.30, ltpPE: 64.30, oiCE: 28000, oiPE: 112000 },
            { strike: 82400, ltpCE: 101.45, ltpPE: 87.45, oiCE: 25000, oiPE: 115000 },
            { strike: 82500, ltpCE: 113.90, ltpPE: 113.90, oiCE: 22000, oiPE: 118000 },
            { strike: 82600, ltpCE: 129.15, ltpPE: 143.15, oiCE: 20000, oiPE: 122000 },
            { strike: 82700, ltpCE: 147.80, ltpPE: 174.80, oiCE: 18000, oiPE: 125000 },
            { strike: 82800, ltpCE: 169.45, ltpPE: 208.45, oiCE: 16000, oiPE: 129000 },
            { strike: 82900, ltpCE: 194.30, ltpPE: 244.30, oiCE: 14000, oiPE: 132000 },
            { strike: 83000, ltpCE: 222.41, ltpPE: 282.41, oiCE: 12000, oiPE: 135000 }
          ],
          'next': [
            { strike: 81000, ltpCE: 367.85, ltpPE: 0.50, oiCE: 87000, oiPE: 65000 },
            { strike: 81100, ltpCE: 318.95, ltpPE: 0.50, oiCE: 80000, oiPE: 69000 },
            { strike: 81200, ltpCE: 274.30, ltpPE: 0.50, oiCE: 74000, oiPE: 72000 },
            { strike: 81300, ltpCE: 234.90, ltpPE: 0.50, oiCE: 70000, oiPE: 75000 },
            { strike: 81400, ltpCE: 200.25, ltpPE: 0.50, oiCE: 64000, oiPE: 79000 },
            { strike: 81500, ltpCE: 170.60, ltpPE: 0.50, oiCE: 60000, oiPE: 82000 },
            { strike: 81600, ltpCE: 146.85, ltpPE: 0.50, oiCE: 54000, oiPE: 85000 },
            { strike: 81700, ltpCE: 128.45, ltpPE: 0.50, oiCE: 50000, oiPE: 89000 },
            { strike: 81800, ltpCE: 114.30, ltpPE: 3.25, oiCE: 46000, oiPE: 92000 },
            { strike: 81900, ltpCE: 104.50, ltpPE: 9.16, oiCE: 42000, oiPE: 95000 },
            { strike: 82000, ltpCE: 99.08, ltpPE: 16.08, oiCE: 38000, oiPE: 99000 },
            { strike: 82100, ltpCE: 97.84, ltpPE: 28.84, oiCE: 35000, oiPE: 102000 },
            { strike: 82200, ltpCE: 100.25, ltpPE: 45.25, oiCE: 32000, oiPE: 105000 },
            { strike: 82300, ltpCE: 106.30, ltpPE: 65.30, oiCE: 30000, oiPE: 109000 },
            { strike: 82400, ltpCE: 115.45, ltpPE: 88.45, oiCE: 27000, oiPE: 112000 },
            { strike: 82500, ltpCE: 127.90, ltpPE: 114.90, oiCE: 24000, oiPE: 115000 },
            { strike: 82600, ltpCE: 143.15, ltpPE: 144.15, oiCE: 22000, oiPE: 119000 },
            { strike: 82700, ltpCE: 161.80, ltpPE: 175.80, oiCE: 20000, oiPE: 122000 },
            { strike: 82800, ltpCE: 183.45, ltpPE: 209.45, oiCE: 18000, oiPE: 125000 },
            { strike: 82900, ltpCE: 208.30, ltpPE: 245.30, oiCE: 16000, oiPE: 129000 },
            { strike: 83000, ltpCE: 236.41, ltpPE: 283.41, oiCE: 14000, oiPE: 132000 }
          ]
        }
      },
      '/orderbook': [
        {
          id: 'ord-1',
          symbol: `NIFTY ${expiries.current} 25000 CE`,
          side: 'SELL',
          quantity: 150,
          price: 135.05,
          status: 'EXECUTED',
          time: '09:15:00',
          userId: 'U1001',
        },
        {
          id: 'ord-2',
          symbol: `NIFTY ${expiries.current} 25100 CE`,
          side: 'BUY',
          quantity: 75,
          price: 141.70,
          status: 'PENDING',
          time: '09:30:00',
          userId: 'U1002',
        },
      ],
      '/positionbook': [
        {
          id: 'pos-1',
          symbol: `NIFTY ${expiries.current} 25000 CE`,
          productType: 'MIS',
          quantity: 150,
          avgPrice: 135.05,
          ltp: 130.25,
          pnl: -592.50,
          status: 'OPEN',
          userId: 'U1001',
        },
        {
          id: 'pos-2',
          symbol: `NIFTY ${expiries.current} 25100 CE`,
          productType: 'NORMAL',
          quantity: 75,
          avgPrice: 141.70,
          ltp: 165.00,
          pnl: 1747.50,
          status: 'OPEN',
          userId: 'U1002',
        },
      ],
      '/basketorder': [
        {
          id: 'basket-1',
          name: 'Strangle Strategy',
          type: 'STRANGLE',
          description: 'NIFTY Strangle for weekly expiry',
          requiredMargin: 85000,
          status: 'ACTIVE',
          legs: [
            {
              id: 'leg-1',
              side: 'SELL',
              symbol: 'NIFTY AUG 25100 PE',
              productType: 'NORMAL',
              qty: 10,
              price: 23.40,
              exchange: 'NSE',
            },
            {
              id: 'leg-2',
              side: 'SELL',
              symbol: 'NIFTY AUG 25150 CE',
              productType: 'NORMAL',
              qty: 10,
              price: 20.35,
              exchange: 'NSE',
            },
          ],
          createdAt: '2025-01-19T09:15:00Z',
          lastModified: '2025-01-19T14:30:00Z',
        },
      ]
    };

    // Handle quotes endpoint with symbol parameter
    if (endpoint === '/quotes' && params.symbol) {
      const symbol = params.symbol.toUpperCase();
      const symbolExpiries = this.generateExpiryDates(symbol);

      // Dynamic quote data based on symbol
      const quoteData = {
        symbol: symbol,
        last_price: symbol === 'NIFTY' ? 24678.50 : symbol === 'BANKNIFTY' ? 23456.80 : symbol === 'SENSEX' ? 81234.60 : 6250.40,
        change: symbol === 'NIFTY' ? 125.30 : symbol === 'BANKNIFTY' ? -89.20 : symbol === 'SENSEX' ? 234.50 : 45.20,
        change_percent: symbol === 'NIFTY' ? 0.51 : symbol === 'BANKNIFTY' ? -0.38 : symbol === 'SENSEX' ? 0.29 : 0.73,
        exchange: symbol === 'SENSEX' ? 'BSE_INDEX' : symbol.includes('NIFTY') ? 'NSE_INDEX' : 'MCX',
        expiry_date: symbolExpiries.currentFull,
        next_expiry: symbolExpiries.nextFull
      };

      return {
        success: true,
        data: quoteData
      };
    }

    // Handle optionchain endpoint with symbol and expiry parameters
    if (endpoint === '/optionchain' && params.symbol) {
      const symbol = params.symbol.toUpperCase();
      const expiry = params.expiry || 'current';
      const chainData = mockData['/optionchain'][symbol];

      if (chainData && chainData[expiry]) {
        return {
          success: true,
          data: chainData[expiry]
        };
      }
    }

    return mockData[endpoint] || [];
  }

  async request(endpoint, options = {}) {
    const isAbsoluteApiPath =
      typeof endpoint === 'string' &&
      (endpoint.startsWith('/api/v1') || endpoint.startsWith('/api/v2'));
    const url = endpoint.startsWith('http')
      ? endpoint
      : (isAbsoluteApiPath ? endpoint : `${this.baseURL}${endpoint}`);
    const lowerUrl = String(url || '').toLowerCase();
    if (lowerUrl.includes('api.dhan.co') || lowerUrl.includes('images.dhan.co')) {
      throw new Error('Frontend direct Dhan REST calls are disabled. Use backend API endpoints only.');
    }
    const isLoginEndpoint = endpoint.includes('/auth/login');
    let body = options.body;
    const isFormDataBody = typeof FormData !== 'undefined' && body instanceof FormData;
    const headers = {
      ...this.getAuthHeaders(),
      ...options.headers,
    };

    if (isFormDataBody) {
      Object.keys(headers).forEach((key) => {
        if (key.toLowerCase() === 'content-type') {
          delete headers[key];
        }
      });
    } else {
      const hasContentType = Object.keys(headers).some((key) => key.toLowerCase() === 'content-type');
      if (!hasContentType) {
        headers['Content-Type'] = 'application/json';
      }
    }

    if (body && typeof body === 'object' && !(body instanceof FormData)) {
      // Pass the endpoint URL to sanitizeBody so exceptions can be made
      // Fix: Use the relative endpoint for checking exceptions, not the full URL if possible
      body = JSON.stringify(this.sanitizeBody(body, endpoint));
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
        body,
      });

      // Handle 401 Unauthorized (but do not hijack login endpoint errors)
      if (response.status === 401) {
        const errorData = await response.json().catch(() => ({}));
        const message = errorData.message || errorData.detail || 'Unauthorized';

        if (!isLoginEndpoint) {
          localStorage.removeItem('authToken');
          localStorage.removeItem('authUser');
          window.location.href = '/login';
          throw new Error('Session expired. Please login again.');
        }

        throw new Error(message);
      }

      // Handle other HTTP errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.message || errorData.detail || `HTTP error! status: ${response.status}`);
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      } else {
        return response;
      }
    } catch (error) {
      console.error(`API Error [${options.method || 'GET'}] ${endpoint}:`, error);
      throw error;
    }
  }

  async get(endpoint, params = {}) {
    const cacheKey = `${endpoint}?${JSON.stringify(params)}`;

    // Skip cache for search endpoints to always get fresh data
    const skipCache =
      endpoint.includes('/market/dhan/instruments') ||
      endpoint.includes('/search/search') ||
      endpoint.includes('/options/live') ||
      endpoint.includes('/commodities/') ||
      endpoint.includes('/trading/orders') ||
      endpoint.includes('/portfolio/positions') ||
      endpoint.includes('/trading/basket-orders');

    if (skipCache) {
      this.cache.delete(cacheKey);
    }

    // Check cache first (unless skipping cache)
    if (!skipCache && this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey);
    }

    // Build query string safely for both absolute and relative base URLs
    const searchParams = new URLSearchParams();
    Object.keys(params).forEach((key) => {
      if (params[key] !== undefined && params[key] !== null) {
        searchParams.append(key, params[key]);
      }
    });
    const query = searchParams.toString();
    const requestEndpoint = query
      ? `${endpoint}${endpoint.includes('?') ? '&' : '?'}${query}`
      : endpoint;

    try {
      const data = await this.request(requestEndpoint, {
        method: 'GET',
      });

      // Cache successful responses (unless skipping cache)
      if (!skipCache) {
        this.cache.set(cacheKey, data);

        // Clear cache after 5 minutes
        setTimeout(() => {
          this.cache.delete(cacheKey);
        }, 5 * 60 * 1000);
      }

      return data;
    } catch (error) {
      throw error;
    }
  }

  async post(endpoint, data = {}) {
    const safe = this.sanitizeBody(data, endpoint);
    const body = (typeof FormData !== 'undefined' && safe instanceof FormData) || typeof safe === 'string'
      ? safe
      : JSON.stringify(safe);
    return this.request(endpoint, {
      method: 'POST',
      body,
    });
  }

  async put(endpoint, data = {}) {
    const safe = this.sanitizeBody(data, endpoint);
    const body = (typeof FormData !== 'undefined' && safe instanceof FormData) || typeof safe === 'string'
      ? safe
      : JSON.stringify(safe);
    return this.request(endpoint, {
      method: 'PUT',
      body,
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE',
    });
  }

  async patch(endpoint, data = {}) {
    const safe = this.sanitizeBody(data, endpoint);
    const body = (typeof FormData !== 'undefined' && safe instanceof FormData) || typeof safe === 'string'
      ? safe
      : JSON.stringify(safe);
    return this.request(endpoint, {
      method: 'PATCH',
      body,
    });
  }

  // Super Orders API methods
  async placeSuperOrder(orderData) {
    return this.post('/orders/super', orderData);
  }

  async getSuperOrders() {
    return this.get('/orders/super');
  }

  async modifySuperOrder(orderId, modifications) {
    return this.put(`/orders/super/${orderId}`, modifications);
  }

  async cancelSuperOrder(orderId) {
    return this.delete(`/orders/super/${orderId}`);
  }

  // File upload
  async upload(endpoint, file, additionalData = {}) {
    const formData = new FormData();
    formData.append('file', file);

    Object.keys(additionalData).forEach(key => {
      formData.append(key, additionalData[key]);
    });

    return this.request(endpoint, {
      method: 'POST',
      body: formData,
      headers: {
        ...this.getAuthHeaders(),
        // Don't set Content-Type for FormData - browser sets it with boundary
      },
    });
  }

  // Clear cache
  clearCache() {
    this.cache.clear();
  }

  // Clear specific cache entry
  clearCacheEntry(endpoint, params = {}) {
    const cacheKey = `${endpoint}?${JSON.stringify(params)}`;
    this.cache.delete(cacheKey);
  }
}

export const apiService = new ApiService();
export default apiService;
