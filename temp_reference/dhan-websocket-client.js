// Dhan WebSocket Integration for Real-time Market Data
// Based on your project requirements

const WebSocket = require('ws');
const EventEmitter = require('events');
const axios = require('axios');

// Helper function to create Dhan API client
function createDhanApiClient() {
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

class DhanWebSocketClient extends EventEmitter {
  constructor(credentials) {
    super();
    this.credentials = credentials;
    this.ws = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 3; // Reduced to avoid rate limiting
    this.reconnectInterval = 30000; // Increased to 30 seconds to avoid rate limiting
    this.isConnecting = false;
    this.isConnected = false;
    this.subscriptions = new Set();

    // Price stores as per your requirements
    this.optionPriceStore = new Map();
    this.instrumentTokenMap = new Map();
    this.orderBookCache = new Map();

    // Margin cache (REST-based)
    this.marginCache = new Map();
  }

  async connect() {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      return;
    }

    this.isConnecting = true;
    console.log('🔌 Connecting to Dhan WebSocket...');

    try {
      // Dhan WebSocket v2 endpoint
      // authType=2 for Daily Token, authType=1 for Static IP
      const authType = this.credentials.authMode === 'STATIC_IP' ? 1 : 2;
      const wsUrl = `wss://api-feed.dhan.co?version=2&token=${this.credentials.accessToken}&clientId=${this.credentials.clientId}&authType=${authType}`;

      this.ws = new WebSocket(wsUrl);

      this.ws.on('open', () => {
        console.log('✅ Connected to Dhan WebSocket');
        this.isConnecting = false;
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.emit('connected');

        // Subscribe to a default instrument to keep connection alive
        // Dhan requires at least one subscription to maintain connection
        this.subscribeToDefaultInstrument();

        // Resubscribe to previous subscriptions
        if (this.subscriptions.size > 0) {
          this.resubscribeAll();
        }
      });

      this.ws.on('message', (data) => {
        this.handleMessage(data);
      });

      // Handle ping/pong for connection keep-alive
      this.ws.on('ping', () => {
        console.log('📡 WebSocket ping received, sending pong...');
        this.ws.pong();
      });

      this.ws.on('pong', () => {
        console.log('📡 WebSocket pong received');
      });

      this.ws.on('error', (error) => {
        console.error('❌ WebSocket error:', error);
        this.isConnecting = false;

        // Handle rate limiting specifically
        if (error.message.includes('429')) {
          console.log('⚠️ Rate limited by Dhan servers, waiting longer before reconnect...');
          this.reconnectInterval = 60000; // Wait 1 minute for rate limit
          this.maxReconnectAttempts = 2; // Fewer attempts when rate limited
        }

        this.emit('error', error);
      });

      this.ws.on('close', (code, reason) => {
        console.log(`🔌 WebSocket closed: ${code} - ${reason}`);
        this.isConnecting = false;
        this.isConnected = false;
        this.emit('disconnected');

        // Auto-reconnect logic
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`🔄 Reconnecting attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}...`);
          setTimeout(() => this.connect(), this.reconnectInterval);
        }
      });

    } catch (error) {
      console.error('❌ Failed to connect to WebSocket:', error);
      this.isConnecting = false;
      this.emit('error', error);
    }
  }

  handleMessage(data) {
    try {
      // Check if data is a Buffer (Binary)
      if (Buffer.isBuffer(data)) {
        this.handleBinaryMessage(data);
      } else if (typeof data === 'string') {
        try {
          const message = JSON.parse(data);
          // Handle potential JSON messages (like auth confirmation or error)
          console.log('📊 WebSocket JSON message:', message);
          if (message.type === 'error') {
            this.emit('feed_error', message.data);
          }
        } catch (e) {
          // If not JSON, it might be stringified binary (unlikely but safe to check)
          console.warn('⚠️ Received non-JSON string message:', data);
        }
      }
    } catch (error) {
      console.error('❌ Failed to process WebSocket message:', error);
    }
  }

  handleBinaryMessage(buffer) {
    let offset = 0;
    while (offset < buffer.length) {
      if (offset + 8 > buffer.length) break;

      // Parse Header (8 bytes)
      const feedResponseCode = buffer.readUInt8(offset);
      const messageLength = buffer.readUInt16LE(offset + 1);
      const exchangeSegmentId = buffer.readUInt8(offset + 3);
      const securityId = buffer.readUInt32LE(offset + 4);

      if (offset + messageLength > buffer.length) {
        console.warn('⚠️ Incomplete binary message received');
        break;
      }

      const payload = buffer.slice(offset + 8, offset + messageLength);
      const instrumentToken = securityId.toString();

      // Exchange mapping for internal reference
      const segments = { 1: 'NSE_EQ', 2: 'BSE_EQ', 3: 'MCX_COM', 4: 'NSE_FO', 5: 'BFO' };
      const segmentName = segments[exchangeSegmentId] || 'UNKNOWN';

      switch (feedResponseCode) {
        case 2: // Ticker / LTP
          if (payload.length >= 8) {
            const ltp = payload.readFloatLE(0);
            const timestamp = payload.readUInt32LE(4);
            this.updateMarketData(instrumentToken, { ltp, timestamp });
          }
          break;
        case 4: // Quote
          if (payload.length >= 40) {
            const ltp = payload.readFloatLE(0);
            const ltq = payload.readUInt32LE(4);
            const bestBid = payload.readFloatLE(8);
            const bestAsk = payload.readFloatLE(12);
            const bidQty = payload.readUInt32LE(16);
            const askQty = payload.readUInt32LE(20);

            this.updateMarketData(instrumentToken, {
              ltp,
              best_bid: bestBid,
              best_ask: bestAsk,
              bid_qty: bidQty,
              ask_qty: askQty,
              ltq,
              timestamp: new Date()
            });
          }
          break;
        case 50: // Disconnect
          console.warn(`🔌 Received disconnect notification for ${instrumentToken}`);
          break;
        default:
          // Ignore other codes for now (Greeks, Full depth etc)
          break;
      }

      offset += messageLength;
    }
  }

  updateMarketData(instrumentToken, data) {
    // Update OptionPriceStore
    const existing = this.optionPriceStore.get(instrumentToken) || {};
    const updated = { ...existing, ...data };
    this.optionPriceStore.set(instrumentToken, updated);

    // Update orderbook cache
    if (data.best_bid !== undefined) {
      this.orderBookCache.set(instrumentToken, {
        best_bid: data.best_bid,
        best_ask: data.best_ask,
        bid_qty: data.bid_qty,
        ask_qty: data.ask_qty,
        last_update: new Date()
      });
    }

    // Emit real-time price updates
    this.emit('price_update', {
      instrument_token: instrumentToken,
      ...updated
    });

    // Emit option chain update if this is an option
    if (this.instrumentTokenMap.has(instrumentToken)) {
      const instrument = this.instrumentTokenMap.get(instrumentToken);
      if (instrument.segment === 'NSE_FO' || instrument.segment === 'BSE_FO') {
        this.emit('option_chain_update', {
          ...instrument,
          ...updated
        });
      }
    }
  }

  async subscribeToInstruments(instruments) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected');
    }

    // Use Dhan's correct subscription format
    const subscriptionData = {
      "RequestCode": 15,
      "InstrumentCount": instruments.length,
      "InstrumentList": instruments.map(inst => ({
        "ExchangeSegment": inst.exchange_segment || 'NSE_EQ',
        "SecurityId": inst.security_id || inst.instrument_token
      }))
    };

    this.ws.send(JSON.stringify(subscriptionData));

    // Store subscriptions
    instruments.forEach(inst => {
      const token = inst.security_id || inst.instrument_token;
      this.subscriptions.add(token);
      this.instrumentTokenMap.set(token, inst);
    });

    console.log(`📊 Subscribed to ${instruments.length} instruments using Dhan format`);
  }

  // Subscribe to a default instrument to keep connection alive
  async subscribeToDefaultInstrument() {
    try {
      // Subscribe to NIFTY 50 as a default instrument
      await this.subscribeToInstruments([{
        exchange_segment: 'NSE_EQ',
        security_id: '13626', // NIFTY 50 index
        instrument_token: '13626'
      }]);
      console.log('📊 Subscribed to default instrument (NIFTY 50) to keep connection alive');
    } catch (error) {
      console.error('❌ Failed to subscribe to default instrument:', error);
    }
  }

  async subscribeToOptionChain(underlying, expiry, strikes) {
    // Build option chain skeleton first (REST call)
    const optionChainSkeleton = await this.buildOptionChainSkeleton(underlying, expiry, strikes);

    // Subscribe to all option instruments
    const optionInstruments = optionChainSkeleton.map(option => ({
      instrument_token: option.instrument_token,
      exchange_segment: option.exchange_segment
    }));

    await this.subscribeToInstruments(optionInstruments);

    return optionChainSkeleton;
  }

  async buildOptionChainSkeleton(underlying, expiry, strikes) {
    // Call Dhan REST API for complete option chain data including Greeks
    try {
      const dhanClient = createDhanApiClient();
      const response = await dhanClient.post('/optionchain', {
        UnderlyingScrip: underlying,
        UnderlyingSeg: underlying === 13 ? "IDX_I" : "NSE_FNO", // Index or Stock F&O
        Expiry: expiry
      });

      // Process the complete option chain data
      const optionChain = response.data.data || response.data;
      const skeleton = [];

      for (const option of optionChain) {
        // Store complete option data including Greeks
        const optionData = {
          underlying,
          expiry,
          strike: option.strike_price,
          option_type: option.option_type, // CE/PE
          instrument_token: option.security_id,
          exchange_segment: option.exchange_segment,

          // Greeks data (provided by Dhan API)
          greeks: {
            delta: option.delta,
            gamma: option.gamma,
            theta: option.theta,
            vega: option.vega
          },

          // Market data
          open_interest: option.open_interest,
          volume: option.volume,
          ltp: option.last_traded_price,
          best_bid: option.best_bid,
          best_ask: option.best_ask,
          implied_volatility: option.iv,

          // Additional fields
          change: option.change,
          change_percent: option.change_percent
        };

        skeleton.push(optionData);

        // Map instrument token for WebSocket updates
        this.instrumentTokenMap.set(option.security_id, optionData);
      }

      console.log(`✅ Loaded option chain with ${skeleton.length} strikes including Greeks`);
      return skeleton;

    } catch (error) {
      console.error('❌ Error fetching option chain from Dhan:', error);

      // Fallback to mock structure
      const skeleton = [];
      for (const strike of strikes) {
        skeleton.push({
          underlying,
          expiry,
          strike,
          option_type: 'CE',
          instrument_token: `${underlying}_${expiry}_${strike}_CE`,
          exchange_segment: 'NSE_FO',
          greeks: { delta: 0, gamma: 0, theta: 0, vega: 0 },
          open_interest: 0,
          volume: 0
        });

        skeleton.push({
          underlying,
          expiry,
          strike,
          option_type: 'PE',
          instrument_token: `${underlying}_${expiry}_${strike}_PE`,
          exchange_segment: 'NSE_FO',
          greeks: { delta: 0, gamma: 0, theta: 0, vega: 0 },
          open_interest: 0,
          volume: 0
        });
      }

      return skeleton;
    }
  }

  getOptionChain(underlying, expiry) {
    // Assemble option chain ON DEMAND as per your requirements
    const optionChain = [];

    for (const [token, instrument] of this.instrumentTokenMap) {
      if (instrument.underlying === underlying &&
        instrument.expiry === expiry &&
        (instrument.segment === 'NSE_FO' || instrument.segment === 'BSE_FO')) {

        const priceData = this.optionPriceStore.get(token);

        optionChain.push({
          ...instrument,
          ltp: priceData?.ltp || 0,
          best_bid: priceData?.best_bid || 0,
          best_ask: priceData?.best_ask || 0,
          bid_qty: priceData?.bid_qty || 0,
          ask_qty: priceData?.ask_qty || 0,
          timestamp: priceData?.timestamp || null
        });
      }
    }

    // Sort by strike price
    return optionChain.sort((a, b) => a.strike - b.strike);
  }

  resubscribeAll() {
    if (this.subscriptions.size > 0) {
      const instruments = Array.from(this.subscriptions).map(token => {
        const instrument = this.instrumentTokenMap.get(token);
        return {
          exchange_segment: instrument?.exchange_segment || 'NSE_EQ',
          security_id: token,
          instrument_token: token
        };
      });

      this.subscribeToInstruments(instruments);
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.subscriptions.clear();
    console.log('🔌 Disconnected from Dhan WebSocket');
  }

  // Price store access methods
  getLatestPrice(instrument_token) {
    return this.optionPriceStore.get(instrument_token);
  }

  getBestBidAsk(instrument_token) {
    const price = this.optionPriceStore.get(instrument_token);
    return price ? {
      bid: price.best_bid,
      ask: price.best_ask,
      bid_qty: price.bid_qty,
      ask_qty: price.ask_qty
    } : null;
  }

  // Margin cache methods (REST-based)
  getCachedMargin(userId, strategyHash) {
    const cacheKey = `${userId}_${strategyHash}`;
    return this.marginCache.get(cacheKey);
  }

  setCachedMargin(userId, strategyHash, marginData) {
    const cacheKey = `${userId}_${strategyHash}`;
    this.marginCache.set(cacheKey, {
      ...marginData,
      timestamp: new Date()
    });
  }
}

module.exports = DhanWebSocketClient;
