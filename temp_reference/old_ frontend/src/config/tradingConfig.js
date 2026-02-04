// Trading Terminal Configuration
// Central place for all trading-related constants and configurations

export const TRADING_CONFIG = {
  // Index configurations with actual lot sizes and strike intervals
  INDICES: {
    NIFTY: {
      symbol: 'NIFTY',
      displayName: 'NIFTY 50',
      lotSize: 65,
      strikeInterval: 50,
      segment: 'NSE_IDX',
      exchange: 'NSE',
      description: 'Nifty 50 Index'
    },
    BANKNIFTY: {
      symbol: 'BANKNIFTY', 
      displayName: 'NIFTY BANK',
      lotSize: 30,
      strikeInterval: 100,
      segment: 'NSE_IDX',
      exchange: 'NSE',
      description: 'Nifty Bank Index'
    },
    SENSEX: {
      symbol: 'SENSEX',
      displayName: 'SENSEX', 
      lotSize: 20,
      strikeInterval: 100,
      segment: 'BSE_IDX',
      exchange: 'BSE',
      description: 'BSE Sensex Index'
    }
  },

  // Expiry configurations
  EXPIRY: {
    WEEKLY_INDICES: ['NIFTY', 'SENSEX'],
    MONTHLY_INDICES: ['BANKNIFTY'],
    DEFAULT_EXPIRY_COUNT: 15,
    STRADDLE_RANGE: 10 // 10 strikes each side around ATM
  },

  // Strike generation rules
  STRIKE_GENERATION: {
    DEFAULT_STRIKE_COUNT: 21, // 10 below + 1 ATM + 10 above
    ATM_ROUNDING_RULE: 'nearest_interval',
    STRADDLE_RANGE: 10 // 10 strikes each side for straddle display
  },

  // Option types
  OPTION_TYPES: {
    CALL: 'CE',
    PUT: 'PE'
  },

  // API endpoints
  API_ENDPOINTS: {
    INSTRUMENT_DATA: '/debug/instrument',
    OPTION_CHAIN: '/option-chain',
    STRADDLE_CHAIN: '/option-chain/live-straddle',
    ATM_BY_PREMIUM: '/option-chain/atm-by-lowest-premium',
    STRADDLE_RANGE: '/option-chain/straddle-range',
    MARKET_QUOTE: '/market/quote'
  },

  // Display configurations
  DISPLAY: {
    CONFIDENCE_INDICATORS: {
      HIGH: '🟢',
      MEDIUM: '🟡', 
      LOW: '🔴'
    },
    COLORS: {
      ATM_HIGHLIGHT: 'indigo',
      BUY_BUTTON: 'blue',
      SELL_BUTTON: 'orange',
      DEMO_WARNING: 'yellow'
    }
  },

  // Mock data generation
  MOCK_DATA: {
    PREMIUM_RANGE: {
      MIN: 100,
      MAX: 500
    },
    DEFAULT_LTP: {
      NIFTY: 23000,
      BANKNIFTY: 45000,
      SENSEX: 77000
    }
  }
};

// Helper functions
export const getIndexConfig = (symbol) => {
  return TRADING_CONFIG.INDICES[symbol.toUpperCase()] || TRADING_CONFIG.INDICES.NIFTY;
};

export const getLotSize = (symbol) => {
  return getIndexConfig(symbol).lotSize;
};

export const getStrikeInterval = (symbol) => {
  return getIndexConfig(symbol).strikeInterval;
};

export const getDisplayName = (symbol) => {
  return getIndexConfig(symbol).displayName;
};

export const isWeeklyIndex = (symbol) => {
  return TRADING_CONFIG.EXPIRY.WEEKLY_INDICES.includes(symbol.toUpperCase());
};

export const generateStrikesAroundATM = (ltp, strikeInterval, range = 10) => {
  const atmStrike = Math.round(ltp / strikeInterval) * strikeInterval;
  const strikes = [];
  
  for (let i = -range; i <= range; i++) {
    strikes.push(atmStrike + (i * strikeInterval));
  }
  
  return {
    atm: atmStrike,
    strikes: strikes,
    range: range
  };
};

export const formatOptionSymbol = (symbol, strike, optionType) => {
  return `${symbol} ${strike}${optionType}`;
};

export default TRADING_CONFIG;
