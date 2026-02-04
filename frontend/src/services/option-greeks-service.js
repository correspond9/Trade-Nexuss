const axios = require('axios');

// Helper function to create Dhan API client
function createDhanApiClient() {
  const fs = require('fs');
  const path = require('path');
  
  try {
    // Get client ID from .env
    const envPath = path.join(__dirname, '..', '.env');
    const envContent = fs.readFileSync(envPath, 'utf8');
    
    let clientId = '';
    const lines = envContent.split('\n');
    for (const line of lines) {
      if (line.includes('DHAN_CLIENT_ID=')) {
        clientId = line.split('=')[1].replace(/"/g, '').trim();
      }
    }
    
    // Get access token from JSON file
    const tokenPath = path.join(__dirname, '..', 'backend', 'dhan_sandbox_token.json');
    let accessToken = '';
    
    if (fs.existsSync(tokenPath)) {
      const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
      accessToken = tokenData.access_token;
    }
    
    return axios.create({
      baseURL: 'https://api.dhan.co/v2',
      timeout: 10000,
      headers: {
        'access-token': accessToken,
        'client-id': clientId,
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('❌ Error creating Dhan API client:', error.message);
    return null;
  }
}

// Option Greeks Service - Based on OpenAlgo Implementation
class OptionGreeksService {
  constructor() {
    this.pyVollibAvailable = false;
    this.initializePyVollib();
  }

  async initializePyVollib() {
    try {
      // Check if py_vollib is available (would require Python integration)
      // For now, we'll implement a simplified Black-Scholes calculator
      this.pyVollibAvailable = true;
      console.log('✅ Option Greeks service initialized');
    } catch (error) {
      console.warn('⚠️ py_vollib not available, using simplified calculations');
      this.pyVollibAvailable = false;
    }
  }

  // Black-76 Model Implementation (simplified)
  black76(flag, S, K, t, r, sigma) {
    const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * t) / (sigma * Math.sqrt(t));
    const d2 = d1 - sigma * Math.sqrt(t);
    
    const phi = (x) => {
      const t = 1.0 / (1.0 + 0.2316419 * Math.abs(x));
      const d = 0.3989423 * Math.exp(-x * x / 2.0);
      const prob = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
      return x > 0 ? 1.0 - prob : prob;
    };

    const phiPrime = (x) => {
      return Math.exp(-x * x / 2) / Math.sqrt(2 * Math.PI);
    };

    let delta, gamma, vega, theta, rho;
    const sqrtT = Math.sqrt(t);
    const expMinusRT = Math.exp(-r * t);

    if (flag === 'call') {
      delta = expMinusRT * phi(d1);
      theta = -(S * phiPrime(d1) * sigma * expMinusRT) / (2 * sqrtT) 
               + r * K * expMinusRT * expMinusRT * phi(d2) 
               - r * S * expMinusRT * phi(d1);
      rho = t * K * expMinusRT * expMinusRT * phi(d2);
    } else { // put
      delta = -expMinusRT * phi(-d1);
      theta = -(S * phiPrime(d1) * sigma * expMinusRT) / (2 * sqrtT) 
               + r * K * expMinusRT * expMinusRT * phi(-d2) 
               + r * S * expMinusRT * phi(-d1);
      rho = -t * K * expMinusRT * expMinusRT * phi(-d2);
    }

    gamma = phiPrime(d1) * expMinusRT / (S * sigma * sqrtT);
    vega = S * expMinusRT * phiPrime(d1) * sqrtT / 100; // per 1% change

    // Convert theta to daily decay
    theta = theta / 365;

    return {
      delta: delta,
      gamma: gamma,
      theta: theta,
      vega: vega,
      rho: rho
    };
  }

  // Calculate implied volatility (Newton-Raphson method)
  calculateImpliedVolatility(flag, S, K, t, r, marketPrice, initialGuess = 0.3) {
    let sigma = initialGuess;
    const tolerance = 1e-6;
    const maxIterations = 100;

    for (let i = 0; i < maxIterations; i++) {
      const greeks = this.black76(flag, S, K, t, r, sigma);
      const price = this.black76Price(flag, S, K, t, r, sigma);
      const vega = greeks.vega * 100; // Convert back from per 1% to decimal

      const diff = price - marketPrice;
      
      if (Math.abs(diff) < tolerance) {
        return sigma;
      }

      if (Math.abs(vega) < tolerance) {
        break; // Avoid division by very small numbers
      }

      sigma = sigma - diff / vega;
      
      if (sigma <= 0) {
        sigma = initialGuess; // Reset if negative
      }
    }

    return sigma;
  }

  black76Price(flag, S, K, t, r, sigma) {
    const d1 = (Math.log(S / K) + (r + 0.5 * sigma * sigma) * t) / (sigma * Math.sqrt(t));
    const d2 = d1 - sigma * Math.sqrt(t);
    
    const phi = (x) => {
      const t = 1.0 / (1.0 + 0.2316419 * Math.abs(x));
      const d = 0.3989423 * Math.exp(-x * x / 2.0);
      const prob = d * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))));
      return x > 0 ? 1.0 - prob : prob;
    };

    const expMinusRT = Math.exp(-r * t);

    if (flag === 'call') {
      return expMinusRT * (S * phi(d1) - K * phi(d2));
    } else {
      return expMinusRT * (K * phi(-d2) - S * phi(-d1));
    }
  }

  parseOptionSymbol(symbol, exchange) {
    // Parse option symbol: SYMBOL[DD][MMM][YY][STRIKE][CE/PE]
    const match = symbol.match(/^([A-Z]+)(\d{2})([A-Z]{3})(\d{2})([\d.]+)(CE|PE)$/);
    
    if (!match) {
      throw new Error(`Invalid option symbol format: ${symbol}`);
    }

    const [, underlying, day, month, year, strikeStr, optionType] = match;
    
    // Convert month abbreviation to number
    const monthMap = {
      'JAN': 0, 'FEB': 1, 'MAR': 2, 'APR': 3, 'MAY': 4, 'JUN': 5,
      'JUL': 6, 'AUG': 7, 'SEP': 8, 'OCT': 9, 'NOV': 10, 'DEC': 11
    };
    
    const monthNum = monthMap[month];
    if (monthNum === undefined) {
      throw new Error(`Invalid month: ${month}`);
    }

    const currentYear = new Date().getFullYear();
    const fullYear = parseInt(year) + (parseInt(year) > 50 ? 1900 : 2000);
    const expiryDate = new Date(fullYear, monthNum, parseInt(day));
    
    // Set expiry time based on exchange
    switch (exchange) {
      case 'NFO':
      case 'BFO':
        expiryDate.setHours(15, 30, 0, 0); // 3:30 PM
        break;
      case 'CDS':
        expiryDate.setHours(12, 30, 0, 0); // 12:30 PM
        break;
      case 'MCX':
        expiryDate.setHours(23, 30, 0, 0); // 11:30 PM
        break;
    }

    return {
      underlying,
      expiryDate,
      strike: parseFloat(strikeStr),
      optionType
    };
  }

  async calculateGreeks(params) {
    try {
      const { symbol, exchange, interest_rate = 0, forward_price, underlying_symbol, underlying_exchange } = params;
      
      // Parse option symbol
      const optionData = this.parseOptionSymbol(symbol, exchange);
      
      // Get underlying price
      let underlyingPrice;
      if (forward_price) {
        underlyingPrice = forward_price;
      } else if (underlying_symbol) {
        underlyingPrice = await this.getUnderlyingPrice(underlying_symbol, underlying_exchange || exchange);
      } else {
        underlyingPrice = await this.getUnderlyingPrice(optionData.underlying, this.getUnderlyingExchange(optionData.underlying));
      }

      // Calculate time to expiry in years
      const now = new Date();
      const timeToExpiry = (optionData.expiryDate - now) / (1000 * 60 * 60 * 24 * 365);
      
      if (timeToExpiry <= 0) {
        throw new Error(`Option has expired on ${optionData.expiryDate.toDateString()}`);
      }

      // Get option price
      const optionPrice = await this.getOptionPrice(symbol, exchange);
      
      // Calculate implied volatility
      const impliedVolatility = this.calculateImpliedVolatility(
        optionData.optionType.toLowerCase(),
        underlyingPrice,
        optionData.strike,
        timeToExpiry,
        interest_rate / 100,
        optionPrice
      );

      // Calculate Greeks
      const greeks = this.black76(
        optionData.optionType.toLowerCase(),
        underlyingPrice,
        optionData.strike,
        timeToExpiry,
        interest_rate / 100,
        impliedVolatility
      );

      return {
        status: 'success',
        symbol,
        exchange,
        underlying: optionData.underlying,
        strike: optionData.strike,
        option_type: optionData.optionType,
        expiry_date: optionData.expiryDate.toLocaleDateString('en-US', { 
          day: '2-digit', 
          month: 'short', 
          year: '2-digit' 
        }),
        days_to_expiry: timeToExpiry * 365,
        spot_price: underlyingPrice,
        option_price: optionPrice,
        interest_rate,
        implied_volatility: impliedVolatility * 100, // Convert to percentage
        greeks: {
          delta: greeks.delta,
          gamma: greeks.gamma,
          theta: greeks.theta,
          vega: greeks.vega,
          rho: greeks.rho
        }
      };

    } catch (error) {
      console.error('Error calculating Greeks:', error);
      return {
        status: 'error',
        message: error.message
      };
    }
  }

  async getUnderlyingPrice(symbol, exchange) {
    try {
      const dhanClient = createDhanApiClient();
      const response = await dhanClient.get(`/market-data/quotes/${symbol}`);
      return response.data.ltp || response.data.last_price;
    } catch (error) {
      console.error('Error fetching underlying price:', error);
      throw new Error(`Failed to fetch underlying price: ${symbol}`);
    }
  }

  async getOptionPrice(symbol, exchange) {
    try {
      const dhanClient = createDhanApiClient();
      const response = await dhanClient.get(`/market-data/quotes/${symbol}`);
      return response.data.ltp || response.data.last_price;
    } catch (error) {
      console.error('Error fetching option price:', error);
      throw new Error(`Option LTP not available: ${symbol}`);
    }
  }

  getUnderlyingExchange(underlying) {
    // Map underlying to exchange
    const indexSymbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'];
    const currencySymbols = ['USDINR', 'EURINR', 'GBPINR', 'JPYINR'];
    const commoditySymbols = ['GOLD', 'SILVER', 'CRUDEOIL', 'NATURALGAS', 'COPPER', 'ZINC', 'LEAD', 'ALUMINIUM'];
    
    if (indexSymbols.includes(underlying)) {
      return 'NSE_INDEX';
    } else if (currencySymbols.includes(underlying)) {
      return 'CDS';
    } else if (commoditySymbols.includes(underlying)) {
      return 'MCX';
    } else {
      return 'NSE'; // Default to NSE for equities
    }
  }
}

module.exports = OptionGreeksService;
