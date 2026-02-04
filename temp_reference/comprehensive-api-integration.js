// Comprehensive API Integration for Paper Trading
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
const DhanWebSocketClient = require('./dhan-websocket-client');

// Import security middleware
const securityMiddleware = require('./middleware/security');
const validationSchemas = require('./middleware/validation');
const SecurityConfig = require('./utils/security-config');
const OptionGreeksService = require('./services/option-greeks-service');

const app = express();
const PORT = 5002; // API Gateway for comprehensive integration

// Security Middleware
app.use(helmet(securityMiddleware.helmetConfig));
app.use(securityMiddleware.corsConfig);

// Rate Limiting
const apiLimiter = securityMiddleware.createRateLimit(
  15 * 60 * 1000, // 15 minutes
  100, // limit each IP to 100 requests per windowMs
  'Too many requests from this IP, please try again later.'
);
const orderLimiter = securityMiddleware.createRateLimit(
  60 * 1000, // 1 minute
  10, // limit orders to 10 per minute
  'Too many order requests, please try again later.'
);

app.use(apiLimiter);
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// WebSocket Client Initialization
let dhanWS = null;

// Initialize WebSocket connection
function initializeWebSocket() {
  const credentials = getCredentials();
  if (credentials.accessToken && credentials.clientId) {
    dhanWS = new DhanWebSocketClient(credentials);
    
    dhanWS.on('connected', () => {
      console.log('✅ Dhan WebSocket connected successfully');
    });
    
    dhanWS.on('price_update', (data) => {
      // Broadcast to connected frontend clients
      broadcastPriceUpdate(data);
    });
    
    dhanWS.on('option_chain_update', (data) => {
      // Broadcast option chain updates
      broadcastOptionChainUpdate(data);
    });
    
    dhanWS.on('error', (error) => {
      console.error('❌ WebSocket error:', error);
    });
    
    dhanWS.on('disconnected', () => {
      console.log('🔌 WebSocket disconnected, attempting reconnect...');
    });
    
    // Connect to WebSocket
    dhanWS.connect();
  }
}

// WebSocket broadcast to frontend
const activeConnections = new Set();

function broadcastPriceUpdate(data) {
  const message = JSON.stringify({
    type: 'price_update',
    data
  });
  
  activeConnections.forEach(ws => {
    if (ws.readyState === 1) { // WebSocket.OPEN
      ws.send(message);
    }
  });
}

function broadcastOptionChainUpdate(data) {
  const message = JSON.stringify({
    type: 'option_chain_update',
    data
  });
  
  activeConnections.forEach(ws => {
    if (ws.readyState === 1) {
      ws.send(message);
    }
  });
}

// Configuration
const config = {
  // Mock Trading Server
  mockServer: 'http://localhost:5001',
  
  // Dhan API (Sandbox)
  dhanApi: {
    baseUrl: 'https://sandbox.dhan.co/v2',
    timeout: 10000
  },
  
  // Mock Data Generation
  mockData: {
    priceVariation: 0.02, // 2% price variation
    volumeMultiplier: 1000,
    defaultMargin: 0.2 // 20% margin
  }
};

// Get credentials from .env and JSON
function getCredentials() {
  const fs = require('fs');
  const path = require('path');
  
  try {
    // Get client ID from .env
    const envPath = path.join(__dirname, '.env');
    const envContent = fs.readFileSync(envPath, 'utf8');
    
    let clientId = '';
    const lines = envContent.split('\n');
    for (const line of lines) {
      if (line.includes('DHAN_CLIENT_ID=')) {
        clientId = line.split('=')[1].replace(/"/g, '').trim();
      }
    }
    
    // Get access token from JSON file
    const tokenPath = path.join(__dirname, 'backend', 'dhan_sandbox_token.json');
    let accessToken = '';
    
    if (fs.existsSync(tokenPath)) {
      const tokenData = JSON.parse(fs.readFileSync(tokenPath, 'utf8'));
      accessToken = tokenData.access_token;
    }
    
    return { clientId, accessToken };
  } catch (error) {
    console.error('❌ Error reading credentials:', error.message);
    return { clientId: '', accessToken: '' };
  }
}

// Dhan API client with authentication
function createDhanApiClient() {
  const credentials = getCredentials();
  
  return axios.create({
    baseURL: config.dhanApi.baseUrl,
    timeout: config.dhanApi.timeout,
    headers: {
      'access-token': credentials.accessToken,
      'client-id': credentials.clientId,
      'Content-Type': 'application/json'
    }
  });
}

// Mock data generators
function generateMockInstrumentData(securityId) {
  const basePrice = parseInt(securityId || '1000') % 1000 + 100;
  const currentPrice = basePrice + (Math.random() - 0.5) * basePrice * 0.02;
  
  return {
    security_id: securityId,
    symbol: `MOCK_${securityId}`,
    name: `Mock Instrument ${securityId}`,
    exchange: 'MCX_COM',
    segment: 'COM',
    price: Math.round(currentPrice * 100) / 100,
    change: Math.round((Math.random() - 0.5) * 10 * 100) / 100,
    change_percent: Math.round((Math.random() - 0.5) * 5 * 100) / 100,
    volume: Math.floor(Math.random() * 100000) + 10000,
    oi: Math.floor(Math.random() * 50000) + 5000,
    high: currentPrice * 1.02,
    low: currentPrice * 0.98,
    open: basePrice,
    close: currentPrice
  };
}

function generateMockMarginData(securityId, quantity, orderType) {
  const instrument = generateMockInstrumentData(securityId);
  const price = instrument.price;
  const notional = price * quantity;
  
  // Different margin requirements for different segments
  let marginRate = config.mockData.defaultMargin;
  
  if (instrument.segment === 'COM') {
    marginRate = 0.15; // 15% for commodities
  } else if (instrument.segment === 'EQ') {
    marginRate = 0.20; // 20% for equity
  }
  
  const marginRequired = notional * marginRate;
  const brokerage = 20;
  const taxes = notional * 0.001; // 0.1% taxes
  
  return {
    security_id: securityId,
    quantity: quantity,
    order_type: orderType,
    price: price,
    notional: Math.round(notional * 100) / 100,
    margin_required: Math.round(marginRequired * 100) / 100,
    margin_rate: marginRate,
    brokerage: brokerage,
    taxes: Math.round(taxes * 100) / 100,
    total_charges: Math.round((marginRequired + brokerage + taxes) * 100) / 100
  };
}

// Comprehensive API Endpoints

// 1. Market Data APIs
app.get('/api/v1/market/instruments/:exchange', async (req, res) => {
  const { exchange } = req.params;
  const { search } = req.query;
  
  try {
    // Try real Dhan API first
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.get(`/v2/instruments/${exchange}`);
    
    console.log('📊 Real instruments data from Dhan API');
    
    // Filter by search term if provided
    let instruments = response.data || [];
    if (search && search.trim()) {
      const searchTerm = search.toLowerCase().trim();
      instruments = instruments.filter(instrument => 
        (instrument.symbol && instrument.symbol.toLowerCase().includes(searchTerm)) ||
        (instrument.name && instrument.name.toLowerCase().includes(searchTerm)) ||
        (instrument.security_id && instrument.security_id.toString().includes(searchTerm))
      );
    }
    
    res.json({
      success: true,
      source: 'real',
      data: instruments
    });
  } catch (error) {
    // Fallback to mock data
    console.log('📊 Using mock instruments data');
    
    const mockInstruments = [];
    for (let i = 1; i <= 50; i++) {
      mockInstruments.push(generateMockInstrumentData(`${226700 + i}`));
    }
    
    // Filter mock data by search term if provided
    let filteredInstruments = mockInstruments;
    if (search && search.trim()) {
      const searchTerm = search.toLowerCase().trim();
      filteredInstruments = mockInstruments.filter(instrument => 
        (instrument.symbol && instrument.symbol.toLowerCase().includes(searchTerm)) ||
        (instrument.name && instrument.name.toLowerCase().includes(searchTerm)) ||
        (instrument.security_id && instrument.security_id.toString().includes(searchTerm))
      );
    }
    
    res.json({
      success: true,
      source: 'mock',
      data: filteredInstruments
    });
  }
});

app.get('/api/v1/market/quote/:securityId', async (req, res) => {
  const { securityId } = req.params;
  
  try {
    // Try real Dhan API first
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.post('/v2/marketfeed/ltp', {
      [securityId.includes('MCX') ? 'MCX_COM' : 'NSE_EQ']: [parseInt(securityId)]
    });
    
    console.log('📊 Real quote data from Dhan API');
    res.json({
      success: true,
      source: 'real',
      data: response.data
    });
  } catch (error) {
    // Fallback to mock data
    console.log('📊 Using mock quote data');
    
    const mockQuote = generateMockInstrumentData(securityId);
    res.json({
      success: true,
      source: 'mock',
      data: mockQuote
    });
  }
});

// 2. Margin Calculator APIs
app.post('/api/v1/margin/calculator', (req, res) => {
  const { orders } = req.body; // Array of orders
  
  const marginCalculations = orders.map(order => {
    return generateMockMarginData(
      order.security_id,
      order.quantity,
      order.order_type
    );
  });
  
  const totalMarginRequired = marginCalculations.reduce(
    (sum, calc) => sum + calc.total_charges, 
    0
  );
  
  console.log('💰 Margin calculation completed');
  
  res.json({
    success: true,
    data: {
      orders: marginCalculations,
      total_margin_required: Math.round(totalMarginRequired * 100) / 100,
      currency: 'INR'
    }
  });
});

// 3. Wallet/Balance APIs
app.get('/api/v1/wallet/balance', async (req, res) => {
  try {
    // Get from mock trading server
    const response = await axios.get(`${config.mockServer}/mock/portfolio/balance`);
    
    console.log('💰 Wallet balance from mock server');
    res.json({
      success: true,
      source: 'mock',
      data: response.data.data
    });
  } catch (error) {
    console.error('❌ Error getting wallet balance:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get wallet balance'
    });
  }
});

// 4. Order Management APIs (Proxy to Mock Server)
app.post('/api/v1/orders/place', async (req, res) => {
  try {
    // Check SPAN margin requirements using Dhan API
    const marginOrder = {
      security_id: req.body.security_id,
      exchange_segment: req.body.exchange_segment || 'NSE_EQ',
      transaction_type: req.body.transaction_type || 'BUY',
      quantity: req.body.quantity,
      price: req.body.price || 0,
      product_type: req.body.product_type || 'CNC',
      order_type: req.body.order_type || 'MARKET'
    };
    
    // Call Dhan SPAN margin API
    const dhanClient = createDhanApiClient();
    const marginResponse = await dhanClient.post('/v2/margins/orders', {
      orders: [marginOrder]
    });
    
    const spanMargin = marginResponse.data.total_margin || marginResponse.data.span_margin;
    
    // Get wallet balance
    const walletResponse = await axios.get(`${config.mockServer}/mock/portfolio/balance`);
    const availableBalance = walletResponse.data.data.available_margin;
    
    // Validate SPAN margin (as per your rules)
    if (spanMargin > availableBalance) {
      return res.status(400).json({
        success: false,
        error: 'Insufficient SPAN margin',
        required_span_margin: spanMargin,
        available_balance: availableBalance,
        source: 'dhan_api'
      });
    }
    
    // Place order through mock server
    const response = await axios.post(`${config.mockServer}/mock/orders/place`, req.body);
    
    res.json({
      success: true,
      data: response.data,
      margin_calculation: {
        span_margin: spanMargin,
        exposure_margin: marginResponse.data.exposure_margin,
        total_charges: marginResponse.data.total_charges,
        source: 'dhan_api'
      }
    });
  } catch (error) {
    console.error('❌ Error placing order:', error.message);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Super Orders API - Place orders with stop-loss and target
app.post('/api/v1/orders/super', async (req, res) => {
  try {
    const { 
      security_id, 
      exchange_segment, 
      transaction_type, 
      quantity, 
      order_type, 
      product_type, 
      price,
      target_price,
      stop_loss_price,
      trailing_jump = 0
    } = req.body;
    
    // Validate super order parameters
    if (!target_price || !stop_loss_price) {
      return res.status(400).json({
        success: false,
        error: 'Target price and stop loss price are required for super orders'
      });
    }
    
    // Check SPAN margin requirements for all legs using Dhan API
    const entryOrder = {
      security_id,
      exchange_segment: exchange_segment || 'NSE_EQ',
      transaction_type,
      quantity,
      order_type: order_type || 'MARKET',
      product_type: product_type || 'CNC',
      price: price || 0
    };
    
    // Call Dhan SPAN margin API for entry order
    const dhanClient = createDhanApiClient();
    const marginResponse = await dhanClient.post('/v2/margins/orders', {
      orders: [entryOrder]
    });
    
    const entrySpanMargin = marginResponse.data.total_margin || marginResponse.data.span_margin;
    const totalMarginRequired = entrySpanMargin * 1.5; // Extra margin for super orders
    
    // Get wallet balance
    const walletResponse = await axios.get(`${config.mockServer}/mock/portfolio/balance`);
    const availableBalance = walletResponse.data.data.available_margin;
    
    // Validate margin
    if (totalMarginRequired > availableBalance) {
      return res.status(400).json({
        success: false,
        error: 'Insufficient margin for super order',
        required: totalMarginRequired,
        available: availableBalance
      });
    }
    
    // Generate super order ID
    const superOrderId = `SUPER_${Date.now()}`;
    
    // Create the super order structure
    const superOrder = {
      super_order_id: superOrderId,
      security_id,
      exchange_segment,
      transaction_type,
      quantity,
      order_type,
      product_type,
      price,
      target_price,
      stop_loss_price,
      trailing_jump,
      status: 'ACTIVE',
      legs: {
        ENTRY_LEG: {
          order_id: `ENTRY_${Date.now()}`,
          status: 'EXECUTED',
          price: price,
          quantity: quantity,
          executed_at: new Date().toISOString()
        },
        TARGET_LEG: {
          order_id: `TARGET_${Date.now()}`,
          status: 'PENDING',
          price: target_price,
          quantity: quantity,
          order_type: 'LIMIT'
        },
        STOP_LOSS_LEG: {
          order_id: `SL_${Date.now()}`,
          status: 'PENDING',
          price: stop_loss_price,
          quantity: quantity,
          order_type: 'SL-M'
        }
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    // Place the entry order
    const orderToPlace = {
      security_id,
      exchange_segment,
      transaction_type,
      quantity,
      order_type,
      product_type,
      price
    };
    
    const response = await axios.post(`${config.mockServer}/mock/orders/place`, orderToPlace);
    
    console.log('🎯 Super order placed via mock server');
    res.json({
      success: true,
      data: {
        ...response.data,
        super_order: superOrder
      },
      margin_calculation: {
        span_margin: entrySpanMargin,
        exposure_margin: marginResponse.data.exposure_margin,
        total_charges: totalMarginRequired,
        source: 'dhan_api'
      }
    });
  } catch (error) {
    console.error('❌ Error placing super order:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to place super order'
    });
  }
});

// Get all super orders
app.get('/api/v1/orders/super', async (req, res) => {
  try {
    // Mock super orders data (in real implementation, this would come from database)
    const mockSuperOrders = [
      {
        super_order_id: 'SUPER_1642972800000',
        security_id: '226733',
        symbol: 'MOCK_226733',
        exchange_segment: 'MCX_COM',
        transaction_type: 'BUY',
        quantity: 10,
        order_type: 'MARKET',
        product_type: 'INTRADAY',
        price: 831.50,
        target_price: 850.00,
        stop_loss_price: 820.00,
        status: 'ACTIVE',
        legs: {
          ENTRY_LEG: {
            order_id: 'ENTRY_1642972800000',
            status: 'EXECUTED',
            price: 831.50,
            quantity: 10,
            executed_at: '2026-01-23T07:30:00Z'
          },
          TARGET_LEG: {
            order_id: 'TARGET_1642972800000',
            status: 'PENDING',
            price: 850.00,
            quantity: 10,
            order_type: 'LIMIT'
          },
          STOP_LOSS_LEG: {
            order_id: 'SL_1642972800000',
            status: 'PENDING',
            price: 820.00,
            quantity: 10,
            order_type: 'SL-M'
          }
        },
        created_at: '2026-01-23T07:30:00Z',
        updated_at: '2026-01-23T07:30:00Z',
        pnl: 0,
        current_price: 831.50
      }
    ];
    
    res.json({
      success: true,
      data: mockSuperOrders
    });
  } catch (error) {
    console.error('❌ Error fetching super orders:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch super orders'
    });
  }
});

// Modify super order
app.put('/api/v1/orders/super/:orderId', async (req, res) => {
  try {
    const { orderId } = req.params;
    const { leg_name, target_price, stop_loss_price, trailing_jump } = req.body;
    
    // Validate leg name
    if (!['TARGET_LEG', 'STOP_LOSS_LEG'].includes(leg_name)) {
      return res.status(400).json({
        success: false,
        error: 'Invalid leg name. Must be TARGET_LEG or STOP_LOSS_LEG'
      });
    }
    
    console.log(`🔄 Modified super order ${orderId}, leg: ${leg_name}`);
    res.json({
      success: true,
      data: {
        super_order_id: orderId,
        leg_name,
        updated_at: new Date().toISOString(),
        status: 'MODIFIED'
      }
    });
  } catch (error) {
    console.error('❌ Error modifying super order:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to modify super order'
    });
  }
});

// Cancel super order
app.delete('/api/v1/orders/super/:orderId', async (req, res) => {
  try {
    const { orderId } = req.params;
    
    console.log(`❌ Cancelled super order ${orderId}`);
    res.json({
      success: true,
      data: {
        super_order_id: orderId,
        status: 'CANCELLED',
        cancelled_at: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('❌ Error cancelling super order:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to cancel super order'
    });
  }
});

app.get('/api/v1/orders/list', async (req, res) => {
  try {
    const response = await axios.get(`${config.mockServer}/mock/orders/list`);
    
    console.log('📋 Order list from mock server');
    res.json({
      success: true,
      data: response.data.data
    });
  } catch (error) {
    console.error('❌ Error getting orders:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get orders'
    });
  }
});

// 5. Portfolio APIs
app.get('/api/v1/portfolio/positions', async (req, res) => {
  try {
    const response = await axios.get(`${config.mockServer}/mock/portfolio/positions`);
    
    console.log('📊 Portfolio positions from mock server');
    res.json({
      success: true,
      data: response.data.data
    });
  } catch (error) {
    console.error('❌ Error getting positions:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get positions'
    });
  }
});

app.get('/api/v1/portfolio/holdings', async (req, res) => {
  try {
    const response = await axios.get(`${config.mockServer}/mock/portfolio/holdings`);
    
    console.log('📊 Portfolio holdings from mock server');
    res.json({
      success: true,
      data: response.data.data
    });
  } catch (error) {
    console.error('❌ Error getting holdings:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to get holdings'
    });
  }
});

// 6. Basket Order APIs
app.post('/api/v1/basket/create', async (req, res) => {
  const { name, orders } = req.body;
  
  try {
    // Calculate SPAN margin for all orders using Dhan API
    const dhanClient = createDhanApiClient();
    const marginOrders = orders.map(order => ({
      security_id: order.security_id,
      exchange_segment: order.exchange_segment || 'NSE_EQ',
      transaction_type: order.transaction_type || 'BUY',
      quantity: order.quantity,
      price: order.price || 0,
      product_type: order.product_type || 'CNC',
      order_type: order.order_type || 'MARKET'
    }));
    
    // Call Dhan SPAN margin API for all basket orders
    const marginResponse = await dhanClient.post('/v2/margins/orders', {
      orders: marginOrders
    });
    
    const totalSpanMargin = marginResponse.data.total_margin || marginResponse.data.span_margin;
    const totalExposureMargin = marginResponse.data.exposure_margin || 0;
    const totalCharges = marginResponse.data.total_charges || totalSpanMargin;
    
    // Create basket with real margin calculations
    const basket = {
      id: `BASKET_${Date.now()}`,
      name: name,
      orders: orders,
      margin_calculations: {
        span_margin: totalSpanMargin,
        exposure_margin: totalExposureMargin,
        total_charges: totalCharges,
        source: 'dhan_api'
      },
      created_at: new Date().toISOString()
    };
    
    console.log('🧺 Basket created with real SPAN margin calculations');
    
    res.json({
      success: true,
      data: basket
    });
  } catch (error) {
    console.error('❌ Error creating basket:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to create basket'
    });
  }
});

// 7. Risk Management APIs
app.get('/api/v1/risk/exposure', async (req, res) => {
  try {
    const positionsResponse = await axios.get(`${config.mockServer}/mock/portfolio/positions`);
    const balanceResponse = await axios.get(`${config.mockServer}/mock/portfolio/balance`);
    
    const positions = positionsResponse.data.data;
    const balance = balanceResponse.data.data;
    
    // Calculate exposure
    const totalExposure = positions.reduce((sum, pos) => {
      return sum + (Math.abs(pos.quantity) * pos.last_price);
    }, 0);
    
    const exposurePercentage = (totalExposure / balance.balance) * 100;
    
    console.log('⚠️ Risk exposure calculated');
    
    res.json({
      success: true,
      data: {
        total_exposure: Math.round(totalExposure * 100) / 100,
        available_balance: balance.available_margin,
        exposure_percentage: Math.round(exposurePercentage * 100) / 100,
        risk_level: exposurePercentage > 80 ? 'HIGH' : exposurePercentage > 60 ? 'MEDIUM' : 'LOW'
      }
    });
  } catch (error) {
    console.error('❌ Error calculating exposure:', error.message);
    res.status(500).json({
      success: false,
      error: 'Failed to calculate exposure'
    });
  }
});

// 8. Historical Data APIs
app.get('/api/v1/historical/intraday/:securityId', async (req, res) => {
  const { securityId } = req.params;
  const { interval = '1' } = req.query;
  
  try {
    // Try real Dhan API first
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.post('/v2/historical/intraday', {
      security_id: securityId,
      interval: interval
    });
    
    console.log('📈 Real intraday data from Dhan API');
    res.json({
      success: true,
      source: 'real',
      data: response.data
    });
  } catch (error) {
    // Fallback to mock data
    console.log('📈 Using mock intraday data');
    
    const mockData = [];
    const basePrice = parseInt(securityId || '1000') % 1000 + 100;
    let currentPrice = basePrice;
    
    // Generate 390 data points (9:15 AM to 3:30 PM, 1-minute intervals)
    for (let i = 0; i < 390; i++) {
      const variation = (Math.random() - 0.5) * basePrice * 0.001;
      currentPrice += variation;
      
      mockData.push({
        timestamp: new Date(Date.now() - (390 - i) * 60000).toISOString(),
        open: currentPrice,
        high: currentPrice * 1.002,
        low: currentPrice * 0.998,
        close: currentPrice,
        volume: Math.floor(Math.random() * 1000) + 100
      });
    }
    
    res.json({
      success: true,
      source: 'mock',
      data: mockData
    });
  }
});

// WebSocket server for real-time data
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8765 });

wss.on('connection', (ws) => {
  console.log('🔌 Frontend client connected to WebSocket');
  activeConnections.add(ws);
  
  ws.on('close', () => {
    console.log('🔌 Frontend client disconnected');
    activeConnections.delete(ws);
  });
  
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      handleWebSocketMessage(ws, data);
    } catch (error) {
      console.error('❌ Invalid WebSocket message:', error);
    }
  });
});

function handleWebSocketMessage(ws, message) {
  switch (message.type) {
    case 'subscribe_option_chain':
      subscribeToOptionChain(message.data);
      break;
    case 'subscribe_instrument':
      subscribeToInstrument(message.data);
      break;
    default:
      console.log('📊 WebSocket message:', message);
  }
}

async function subscribeToOptionChain(data) {
  if (!dhanWS) {
    console.error('❌ WebSocket client not initialized');
    return;
  }
  
  try {
    const { underlying, expiry, strikes } = data;
    await dhanWS.subscribeToOptionChain(underlying, expiry, strikes);
    console.log(`📊 Subscribed to option chain: ${underlying} ${expiry}`);
  } catch (error) {
    console.error('❌ Failed to subscribe to option chain:', error);
  }
}

async function subscribeToInstrument(data) {
  if (!dhanWS) {
    console.error('❌ WebSocket client not initialized');
    return;
  }
  
  try {
    await dhanWS.subscribeToInstruments([data]);
    console.log(`📊 Subscribed to instrument: ${data.instrument_token}`);
  } catch (error) {
    console.error('❌ Failed to subscribe to instrument:', error);
  }
}

// Option Chain API endpoints
app.get('/api/v1/market/option-chain/:underlying', async (req, res) => {
  const { underlying } = req.params;
  const { expiry } = req.query;
  
  try {
    if (!dhanWS) {
      return res.status(500).json({
        success: false,
        error: 'WebSocket not connected'
      });
    }
    
    const optionChain = dhanWS.getOptionChain(underlying, expiry);
    
    res.json({
      success: true,
      data: optionChain,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('❌ Error fetching option chain:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Get expiry dates for underlying
app.get('/api/v1/market/expiries/:underlying', async (req, res) => {
  const { underlying } = req.params;
  
  try {
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.post('/optionchain/expirylist', {
      UnderlyingScrip: parseInt(underlying),
      UnderlyingSeg: underlying === '13' ? "IDX_I" : "NSE_FNO"
    });
    
    res.json({
      success: true,
      data: response.data.data || response.data,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('❌ Error fetching expiries:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Enhanced margin calculation with SPAN rules
app.post('/api/v1/margin/calculate', async (req, res) => {
  const { orders, user_id, strategy_hash } = req.body;
  
  try {
    // Check cached margin first (as per your rules)
    if (user_id && strategy_hash) {
      const cachedMargin = dhanWS?.getCachedMargin(user_id, strategy_hash);
      if (cachedMargin && (Date.now() - cachedMargin.timestamp.getTime()) < 300000) { // 5 minutes cache
        return res.json({
          success: true,
          data: cachedMargin,
          source: 'cache'
        });
      }
    }
    
    // Call Dhan margin API
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.post('/v2/margins/orders', {
      orders: orders
    });
    
    const marginData = {
      required_margin: response.data.total_margin,
      span_margin: response.data.span_margin,
      exposure_margin: response.data.exposure_margin,
      total_charges: response.data.total_charges,
      timestamp: new Date().toISOString()
    };
    
    // Cache the result
    if (user_id && strategy_hash) {
      dhanWS?.setCachedMargin(user_id, strategy_hash, marginData);
    }
    
    res.json({
      success: true,
      data: marginData,
      source: 'api'
    });
  } catch (error) {
    console.error('❌ Error calculating margin:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Enhanced order placement with WebSocket price validation
app.post('/api/v1/orders/place', async (req, res) => {
  const { order } = req.body;
  
  try {
    // Check WebSocket price feasibility first (as per your rules)
    if (dhanWS && order.instrument_token) {
      const priceData = dhanWS.getBestBidAsk(order.instrument_token);
      
      if (priceData) {
        // Validate order against current market prices
        if (order.transaction_type === 'BUY' && order.price > priceData.ask) {
          return res.status(400).json({
            success: false,
            error: 'Buy price above current ask',
            current_ask: priceData.ask
          });
        }
        
        if (order.transaction_type === 'SELL' && order.price < priceData.bid) {
          return res.status(400).json({
            success: false,
            error: 'Sell price below current bid',
            current_bid: priceData.bid
          });
        }
      }
    }
    
    // Proceed with order placement
    const dhanClient = createDhanApiClient();
    const response = await dhanClient.post('/v2/orders', order);
    
    res.json({
      success: true,
      data: response.data,
      message: 'Order placed successfully'
    });
  } catch (error) {
    console.error('❌ Error placing order:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// System Monitoring API endpoints
app.get('/api/v1/system/status', async (req, res) => {
  try {
    const systemStatus = {
      timestamp: new Date().toISOString(),
      services: {
        dhan_api: await checkDhanApiStatus(),
        database: await checkDatabaseStatus(),
        authentication: await checkAuthenticationStatus(),
        mock_server: await checkMockServerStatus(),
        websocket: await checkWebSocketStatus()
      },
      system: {
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        node_version: process.version
      }
    };
    
    res.json({
      success: true,
      data: systemStatus
    });
  } catch (error) {
    console.error('❌ Error checking system status:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to get system status'
    });
  }
});

// Individual service status checks
async function checkDhanApiStatus() {
  try {
    const response = await axios.get('https://api.dhan.co', { 
      timeout: 5000,
      validateStatus: (status) => status < 500
    });
    return {
      status: 'online',
      response_time: response.headers['x-response-time'] || 'N/A',
      last_check: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: 'offline',
      error: error.message,
      last_check: new Date().toISOString()
    };
  }
}

async function checkDatabaseStatus() {
  try {
    // Check if mock server is responding (acting as our database)
    const response = await axios.get('http://localhost:5001/mock/portfolio/balance', { timeout: 3000 });
    return {
      status: 'connected',
      response_time: 'N/A',
      last_check: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: 'disconnected',
      error: error.message,
      last_check: new Date().toISOString()
    };
  }
}

async function checkAuthenticationStatus() {
  try {
    // Check if auth endpoints are working
    const credentials = getCredentials();
    const hasCredentials = credentials.accessToken && credentials.clientId;
    
    return {
      status: hasCredentials ? 'active' : 'inactive',
      configured: hasCredentials,
      last_check: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: 'error',
      error: error.message,
      last_check: new Date().toISOString()
    };
  }
}

async function checkMockServerStatus() {
  try {
    const response = await axios.get('http://localhost:5001/mock/portfolio/balance', { timeout: 3000 });
    return {
      status: 'online',
      response_time: 'N/A',
      last_check: new Date().toISOString()
    };
  } catch (error) {
    return {
      status: 'offline',
      error: error.message,
      last_check: new Date().toISOString()
    };
  }
}

async function checkWebSocketStatus() {
  try {
    // Check WebSocket connection status
    if (dhanWS && dhanWS.isConnected) {
      return {
        status: 'connected',
        last_check: new Date().toISOString()
      };
    } else {
      return {
        status: 'disconnected',
        error: 'WebSocket not connected',
        last_check: new Date().toISOString()
      };
    }
  } catch (error) {
    return {
      status: 'error',
      error: error.message,
      last_check: new Date().toISOString()
    };
  }
}

// Recent activity endpoint
app.get('/api/v1/system/activity', async (req, res) => {
  try {
    // Mock recent activity - in production, this would come from logs/database
    const activities = [
      {
        type: 'admin_login',
        user: 'ck.nanaiah',
        timestamp: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
        description: 'Admin login'
      },
      {
        type: 'user_registration',
        user: 'dhruv',
        timestamp: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
        description: 'User registration'
      },
      {
        type: 'api_config_update',
        user: 'system',
        timestamp: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
        description: 'API configuration updated'
      },
      {
        type: 'system_backup',
        user: 'system',
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        description: 'System backup completed'
      }
    ];
    
    res.json({
      success: true,
      data: activities
    });
  } catch (error) {
    console.error('❌ Error fetching system activity:', error);
    res.status(500).json({
      success: false,
      message: 'Failed to fetch system activity'
    });
  }
});

// Health check endpoint
app.get('/api/v1/health', (req, res) => {
  res.json({
    success: true,
    message: 'Comprehensive API Integration running',
    services: {
      mock_trading_server: 'http://localhost:5001',
      dhan_api: 'https://api.dhan.co',
      mode: 'paper_trading_with_real_data'
    }
  });
});

// Option Greeks Calculation Endpoint
app.post('/api/v1/optiongreeks', 
  validationSchemas.optionGreeksValidation,
  securityMiddleware.validateRequest,
  async (req, res) => {
    try {
      const greeksService = new OptionGreeksService();
      const result = await greeksService.calculateGreeks(req.body);
      
      if (result.status === 'error') {
        return res.status(400).json(result);
      }
      
      res.json(result);
    } catch (error) {
      console.error('❌ Error calculating option Greeks:', error);
      res.status(500).json({
        status: 'error',
        message: 'Internal server error while calculating option Greeks'
      });
    }
  }
);

// Multi Option Greeks Calculation Endpoint
app.post('/api/v1/multioptiongreeks',
  validationSchemas.optionGreeksValidation,
  securityMiddleware.validateRequest,
  async (req, res) => {
    try {
      const greeksService = new OptionGreeksService();
      const { symbols, ...commonParams } = req.body;
      
      if (!Array.isArray(symbols) || symbols.length === 0) {
        return res.status(400).json({
          status: 'error',
          message: 'Symbols must be a non-empty array'
        });
      }
      
      const results = [];
      for (const symbol of symbols) {
        const result = await greeksService.calculateGreeks({ ...commonParams, symbol });
        results.push(result);
      }
      
      res.json({
        status: 'success',
        results
      });
    } catch (error) {
      console.error('❌ Error calculating multi option Greeks:', error);
      res.status(500).json({
        status: 'error',
        message: 'Internal server error while calculating multi option Greeks'
      });
    }
  }
);

app.listen(PORT, () => {
  console.log(`🎯 Comprehensive API Integration running on http://localhost:${PORT}`);
  console.log('📊 Features:');
  console.log('  ✅ Market Data (Real + Mock)');
  console.log('  ✅ Dhan WebSocket Integration');
  console.log('  ✅ Real-time Option Chain');
  console.log('  ✅ SPAN Margin Calculation');
  console.log('  ✅ Price Validation');
  console.log('  ✅ Margin Calculator');
  console.log('  ✅ Wallet Balance');
  console.log('  ✅ Order Management');
  console.log('  ✅ Portfolio Tracking');
  console.log('  ✅ Basket Orders');
  console.log('  ✅ Risk Management');
  console.log('  ✅ Historical Data');
  console.log('  ✅ Paper Trading Mode');
  console.log('🔌 WebSocket server running on ws://localhost:8765');
  
  // Initialize WebSocket connection
  initializeWebSocket();
});

module.exports = app;
