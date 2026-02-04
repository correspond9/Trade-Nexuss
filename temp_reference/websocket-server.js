// Real-time WebSocket Integration for Paper Trading
const WebSocket = require('ws');
const EventEmitter = require('events');

class RealTimeDataManager extends EventEmitter {
  constructor() {
    super();
    this.connections = new Map();
    this.subscriptions = new Map();
    this.marketData = new Map();
    this.portfolioData = new Map();
    
    // Initialize with mock data
    this.initializeMockData();
  }
  
  initializeMockData() {
    // Mock market data for popular MCX instruments
    const mockInstruments = [
      { security_id: '226712', symbol: 'CRUDEOIL', exchange: 'MCX_COM', price: 815.50, change: 2.5, volume: 150000 },
      { security_id: '260105', symbol: 'GOLD', exchange: 'MCX_COM', price: 52000.00, change: -0.5, volume: 25000 },
      { security_id: '260106', symbol: 'SILVER', exchange: 'MCX_COM', price: 62000.00, change: 1.2, volume: 18000 },
      { security_id: '226713', symbol: 'NATURALGAS', exchange: 'MCX_COM', price: 225.50, change: -1.8, volume: 45000 },
      { security_id: '226714', symbol: 'COPPER', exchange: 'MCX_COM', price: 725.00, change: 0.8, volume: 32000 }
    ];
    
    mockInstruments.forEach(instrument => {
      this.marketData.set(instrument.security_id, instrument);
    });
    
    console.log('📊 Initialized mock market data for', mockInstruments.length, 'instruments');
  }
  
  // WebSocket server for real-time data
  startWebSocketServer(port = 5003) => {
    const wss = new WebSocket.Server({ port });
    
    wss.on('connection', (ws) => {
      const clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      console.log('🔗 WebSocket client connected:', clientId);
      this.connections.set(clientId, ws);
      
      // Send initial data
      this.sendInitialData(ws);
      
      // Handle client messages
      ws.on('message', (message) => {
        this.handleClientMessage(clientId, JSON.parse(message.toString()));
      });
      
      ws.on('close', () => {
        console.log('🔚 WebSocket client disconnected:', clientId);
        this.connections.delete(clientId);
      });
      
      ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error.message);
      });
    });
    
    console.log(`🌐 Real-time WebSocket server running on port ${port}`);
    return wss;
  }
  
  sendInitialData(ws) {
    // Send current market data
    const marketData = Array.from(this.marketData.values());
    
    ws.send(JSON.stringify({
      type: 'market_data',
      data: marketData,
      timestamp: new Date().toISOString()
    }));
    
    // Send portfolio data
    const portfolioData = {
      balance: 1000000,
      positions: Array.from(this.portfolioData.values()),
      timestamp: new Date().toISOString()
    };
    
    ws.send(JSON.stringify({
      type: 'portfolio_data',
      data: portfolioData,
      timestamp: new Date().toISOString()
    }));
  }
  
  handleClientMessage(clientId, message) {
    const { type, data } = message;
    
    switch (type) {
      case 'subscribe_market_data':
        this.handleMarketDataSubscription(clientId, data);
        break;
        
      case 'subscribe_portfolio':
        this.handlePortfolioSubscription(clientId, data);
        break;
        
      case 'place_order':
        this.handleOrderPlacement(clientId, data);
        break;
        
      case 'get_market_data':
        this.sendMarketData(clientId);
        break;
        
      case 'get_portfolio':
        this.sendPortfolioData(clientId);
        break;
        
      default:
        console.log('🔍 Unknown message type:', type);
    }
  }
  
  handleMarketDataSubscription(clientId, data) {
    const { instruments, exchanges } = data;
    
    // Filter instruments based on subscription
    const subscribedData = Array.from(this.marketData.values()).filter(instrument => {
      return (!instruments || instruments.includes(instrument.security_id)) &&
             (!exchanges || exchanges.includes(instrument.exchange));
    });
    
    this.subscriptions.set(clientId, { instruments, exchanges });
    
    this.sendToClient(clientId, {
      type: 'market_data_subscription',
      data: subscribedData,
      timestamp: new Date().toISOString()
    });
    
    console.log('📊 Client subscribed to market data:', clientId, instruments?.length || 'all');
  }
  
  handlePortfolioSubscription(clientId, data) {
    this.subscriptions.set(clientId, { ...this.subscriptions.get(clientId), portfolio: true });
    
    this.sendPortfolioData(clientId);
    console.log('📊 Client subscribed to portfolio updates:', clientId);
  }
  
  handleOrderPlacement(clientId, data) {
    // Simulate order placement
    const orderId = `WS_ORDER_${Date.now()}`;
    const order = {
      ...data,
      orderId,
      status: 'EXECUTED',
      timestamp: new Date().toISOString(),
      execution_price: this.marketData.get(data.security_id)?.price || 800,
      execution_quantity: data.quantity
    };
    
    // Update portfolio
    this.portfolioData.set(orderId, order);
    
    this.sendToClient(clientId, {
      type: 'order_execution',
      data: order,
      timestamp: new Date().toISOString()
    });
    
    console.log('📋 WebSocket order placed:', orderId);
  }
  
  sendMarketData(clientId) {
    const subscription = this.subscriptions.get(clientId);
    let marketData = Array.from(this.marketData.values());
    
    if (subscription && subscription.instruments) {
      marketData = marketData.filter(instrument => 
        subscription.instruments.includes(instrument.security_id)
      );
    }
    
    if (subscription && subscription.exchanges) {
      marketData = marketData.filter(instrument => 
        subscription.exchanges.includes(instrument.exchange)
      );
    }
    
    this.sendToClient(clientId, {
      type: 'market_data',
      data: marketData,
      timestamp: new Date().toISOString()
    });
  }
  
  sendPortfolioData(clientId) {
    const portfolioData = {
      balance: 1000000,
      positions: Array.from(this.portfolioData.values()),
      timestamp: new Date().toISOString()
    };
    
    this.sendToClient(clientId, {
      type: 'portfolio_data',
      data: portfolioData,
      timestamp: new Date().toISOString()
    });
  }
  
  sendToClient(clientId, message) {
    const ws = this.connections.get(clientId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
    }
  }
  
  // Simulate real-time price updates
  startPriceSimulation() {
    setInterval(() => {
      // Update prices with realistic movements
      this.marketData.forEach((instrument, securityId) => {
        const currentPrice = instrument.price;
        const variation = (Math.random() - 0.5) * currentPrice * 0.001; // 0.1% variation
        const newPrice = Math.max(1, currentPrice + variation);
        
        instrument.price = Math.round(newPrice * 100) / 100;
        instrument.change = Math.round((newPrice - currentPrice) * 100) / 100;
        instrument.change_percent = Math.round(((newPrice - currentPrice) / currentPrice) * 10000) / 100;
        
        // Update volume randomly
        instrument.volume = Math.max(1000, instrument.volume + Math.floor((Math.random() - 0.5) * 1000));
      });
      
      // Broadcast price updates to all connected clients
      this.broadcastMarketUpdate();
      
    }, 2000); // Update every 2 seconds
  }
  
  broadcastMarketUpdate() {
    const marketData = Array.from(this.marketData.values());
    
    this.connections.forEach((ws, clientId) => {
      const subscription = this.subscriptions.get(clientId);
      
      if (subscription && (subscription.instruments || subscription.exchanges)) {
        let filteredData = marketData;
        
        if (subscription.instruments) {
          filteredData = marketData.filter(instrument => 
            subscription.instruments.includes(instrument.security_id)
          );
        }
        
        if (subscription.exchanges) {
          filteredData = filteredData.filter(instrument => 
            subscription.exchanges.includes(instrument.exchange)
          );
        }
        
        this.sendToClient(clientId, {
          type: 'market_data_update',
          data: filteredData,
          timestamp: new Date().toISOString()
        });
      }
    });
  }
}

// Frontend WebSocket Client Integration
class FrontendWebSocketClient {
  constructor(config = {}) {
    this.config = {
      wsUrl: 'ws://localhost:5003',
      reconnectAttempts: 5,
      reconnectDelay: 2000,
      ...config
    };
    
    this.ws = null;
    this.isConnected = false;
    this.subscriptions = {};
    this.eventEmitter = new EventEmitter();
  }
  
  connect() {
    try {
      this.ws = new WebSocket(this.config.wsUrl);
      
      this.ws.on('open', () => {
        console.log('🔗 Connected to real-time data server');
        this.isConnected = true;
        this.eventEmitter.emit('connected');
      });
      
      this.ws.on('message', (data) => {
        const message = JSON.parse(data.toString());
        this.handleMessage(message);
      });
      
      this.ws.on('close', () => {
        console.log('🔚 Disconnected from real-time data server');
        this.isConnected = false;
        this.eventEmitter.emit('disconnected');
        this.attemptReconnect();
      });
      
      this.ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error.message);
        this.isConnected = false;
        this.eventEmitter.emit('error', error);
        this.attemptReconnect();
      });
      
    } catch (error) {
      console.error('❌ Connection error:', error.message);
      this.eventEmitter.emit('error', error);
    }
  }
  
  attemptReconnect() {
    if (this.config.reconnectAttempts > 0) {
      setTimeout(() => {
        console.log('🔄 Attempting to reconnect...');
        this.connect();
      }, this.config.reconnectDelay);
      this.config.reconnectAttempts--;
    }
  }
  
  handleMessage(message) {
    const { type, data, timestamp } = message;
    
    switch (type) {
      case 'market_data':
        this.eventEmitter.emit('marketData', data);
        break;
        
      case 'market_data_update':
        this.eventEmitter.emit('marketDataUpdate', data);
        break;
        
      case 'portfolio_data':
        this.eventEmitter.emit('portfolioData', data);
        break;
        
      case 'order_execution':
        this.eventEmitter.emit('orderExecution', data);
        break;
        
      default:
        console.log('🔍 Unknown message type:', type);
    }
  }
  
  subscribeToMarketData(instruments = [], exchanges = []) {
    if (this.isConnected) {
      const message = {
        type: 'subscribe_market_data',
        data: { instruments, exchanges }
      };
      this.ws.send(JSON.stringify(message));
      this.subscriptions = { ...this.subscriptions, instruments, exchanges };
    }
  }
  
  subscribeToPortfolio() {
    if (this.isConnected) {
      const message = {
        type: 'subscribe_portfolio',
        data: {}
      };
      this.ws.send(JSON.stringify(message));
      this.subscriptions.portfolio = true;
    }
  }
  
  placeOrder(orderData) {
    if (this.isConnected) {
      const message = {
        type: 'place_order',
        data: orderData
      };
      this.ws.send(JSON.stringify(message));
    }
  }
  
  getMarketData() {
    if (this.isConnected) {
      const message = {
        type: 'get_market_data'
      };
      this.ws.send(JSON.stringify(message));
    }
  }
  
  getPortfolio() {
    if (this.isConnected) {
      const message = {
        type: 'get_portfolio'
      };
      this.ws.send(JSON.stringify(message));
    }
  }
  
  on(event, callback) {
    this.eventEmitter.on(event, callback);
  }
  
  off(event, callback) {
    this.eventEmitter.off(event, callback);
  }
}

// Start real-time data server
const realTimeManager = new RealTimeDataManager();
const wss = realTimeManager.startWebSocketServer(5003);

// Start price simulation
realTimeManager.startPriceSimulation();

console.log('🎯 Real-time Data Integration Ready!');
console.log('📊 WebSocket Server: ws://localhost:5003');
console.log('📈 Price Simulation: Active');
console.log('🔄 Real-time Updates: Every 2 seconds');

module.exports = {
  RealTimeDataManager,
  FrontendWebSocketClient,
  realTimeManager,
  wss
};
