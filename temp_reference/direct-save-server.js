// Paper Trading Configuration with Data API Focus
const config = {
  // Paper Trading Mode
  PAPER_TRADING: {
    enabled: true,
    mockOrders: true, // All orders go to mock servers
    realData: true,  // Use real Data API for market data
    logLevel: 'debug'
  },

  // Data API Configuration (Paid Subscription)
  DATA_API: {
    enabled: true,
    subscription: 'paid', // ₹499/month
    endpoints: {
      // WebSocket endpoints for real-time data
      marketFeed: 'wss://api-feed.dhan.co',
      orderUpdates: 'wss://api-order-update.dhan.co', 
      marketDepth: 'wss://depth-api-feed.dhan.co/twentydepth',
      
      // REST endpoints for historical data
      historicalData: 'https://api.dhan.co/v2/historical',
      optionChain: 'https://api.dhan.co/v2/option-chain',
      marketQuotes: 'https://api.dhan.co/v2/market-quotes'
    },
    rateLimits: {
      requestsPerSec: 10,
      ordersPerSec: 25,
      maxOrdersPerDay: 5000
    }
  },

  // Trading API Configuration (Free - Mock Mode)
  TRADING_API: {
    enabled: true,
    mode: 'mock', // Mock servers only
    mockEndpoints: {
      placeOrder: 'http://localhost:5000/mock/orders/place',
      modifyOrder: 'http://localhost:5000/mock/orders/modify',
      cancelOrder: 'http://localhost:5000/mock/orders/cancel',
      getPositions: 'http://localhost:5000/mock/portfolio/positions',
      getHoldings: 'http://localhost:5000/mock/portfolio/holdings'
    }
  },

  // Authentication
  AUTH: {
    // Use same credentials for both APIs
    clientId: process.env.DHAN_CLIENT_ID,
    accessToken: process.env.DHAN_ACCESS_TOKEN || process.env.DHAN_API_KEY,
    
    // Data API may require additional headers
    dataApiHeaders: {
      'access-token': process.env.DHAN_ACCESS_TOKEN || process.env.DHAN_API_KEY,
      'client-id': process.env.DHAN_CLIENT_ID,
      'Content-Type': 'application/json',
      'X-Data-Subscription': 'active' // Indicate paid subscription
    }
  },

  // Mock Trading Simulation
  MOCK_TRADING: {
    orderExecution: {
      slippage: 0.01, // 0.01% slippage
      delay: 100,     // 100ms execution delay
      successRate: 0.98 // 98% success rate
    },
    portfolio: {
      initialBalance: 1000000, // ₹10 Lakhs virtual money
      margin: 0.2,             // 20% margin requirement
      brokerage: 20            // ₹20 per order (like real Dhan)
    }
  }
};

module.exports = config;
