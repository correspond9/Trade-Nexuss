const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 5001; // Different port for mock trading

// Middleware
app.use(cors({
  origin: ['http://localhost:5173', 'http://localhost:3000'],
  credentials: true
}));
app.use(express.json());

// Mock portfolio state
let mockPortfolio = {
  balance: 1000000, // ₹10 Lakhs
  positions: [],
  orders: [],
  holdings: [],
  trades: []
};

// Mock order ID counter
let orderIdCounter = 1000;

// Mock endpoints for paper trading
app.post('/mock/orders/place', (req, res) => {
  const { security_id, exchange_segment, transaction_type, quantity, order_type, product_type, price } = req.body;
  
  const orderId = `MOCK_${orderIdCounter++}`;
  const timestamp = new Date().toISOString();
  
  const order = {
    orderId,
    security_id,
    exchange_segment,
    transaction_type,
    quantity,
    order_type,
    product_type,
    price,
    status: 'EXECUTED', // Auto-execute for paper trading
    timestamp,
    execution_price: order_type === 'MARKET' ? getMockPrice(security_id) : price,
    execution_quantity: quantity,
    brokerage: 20 // ₹20 per order
  };
  
  mockPortfolio.orders.push(order);
  mockPortfolio.trades.push(order);
  
  // Update balance
  const tradeValue = order.execution_price * quantity + order.brokerage;
  if (transaction_type === 'BUY') {
    mockPortfolio.balance -= tradeValue;
  } else {
    mockPortfolio.balance += tradeValue;
  }
  
  console.log('📊 Mock Order Placed:', orderId);
  
  res.json({
    success: true,
    orderId,
    status: 'EXECUTED',
    message: 'Paper trading order executed successfully',
    data: order
  });
});

app.put('/mock/orders/modify', (req, res) => {
  const { orderId, new_price, new_quantity } = req.body;
  
  const order = mockPortfolio.orders.find(o => o.orderId === orderId);
  if (order) {
    order.price = new_price;
    order.quantity = new_quantity;
    order.status = 'MODIFIED';
    
    console.log('📊 Mock Order Modified:', orderId);
    
    res.json({
      success: true,
      orderId,
      status: 'MODIFIED',
      message: 'Paper trading order modified successfully',
      data: order
    });
  } else {
    res.status(404).json({
      success: false,
      message: 'Order not found'
    });
  }
});

app.delete('/mock/orders/cancel', (req, res) => {
  const { orderId } = req.body;
  
  const orderIndex = mockPortfolio.orders.findIndex(o => o.orderId === orderId);
  if (orderIndex !== -1) {
    const order = mockPortfolio.orders[orderIndex];
    order.status = 'CANCELLED';
    
    console.log('📊 Mock Order Cancelled:', orderId);
    
    res.json({
      success: true,
      orderId,
      status: 'CANCELLED',
      message: 'Paper trading order cancelled successfully',
      data: order
    });
  } else {
    res.status(404).json({
      success: false,
      message: 'Order not found'
    });
  }
});

app.get('/mock/portfolio/positions', (req, res) => {
  // Generate mock positions based on executed orders
  const positions = mockPortfolio.orders
    .filter(order => order.status === 'EXECUTED')
    .map(order => ({
      security_id: order.security_id,
      exchange_segment: order.exchange_segment,
      product_type: order.product_type,
      quantity: order.transaction_type === 'BUY' ? order.execution_quantity : -order.execution_quantity,
      average_price: order.execution_price,
      last_price: getMockPrice(order.security_id),
      pnl: calculatePnL(order),
      status: 'OPEN'
    }));
  
  res.json({
    success: true,
    data: positions
  });
});

app.get('/mock/portfolio/holdings', (req, res) => {
  // Generate mock holdings
  const holdings = mockPortfolio.orders
    .filter(order => order.status === 'EXECUTED' && order.product_type === 'CNC')
    .map(order => ({
      security_id: order.security_id,
      exchange_segment: order.exchange_segment,
      quantity: order.execution_quantity,
      average_price: order.execution_price,
      last_price: getMockPrice(order.security_id),
      pnl: calculatePnL(order)
    }));
  
  res.json({
    success: true,
    data: holdings
  });
});

app.get('/mock/portfolio/balance', (req, res) => {
  res.json({
    success: true,
    data: {
      balance: mockPortfolio.balance,
      used_margin: mockPortfolio.balance * 0.2,
      available_margin: mockPortfolio.balance * 0.8
    }
  });
});

app.get('/mock/orders/list', (req, res) => {
  res.json({
    success: true,
    data: mockPortfolio.orders
  });
});

// Helper functions
function getMockPrice(securityId) {
  // Generate realistic mock prices based on security_id
  const basePrice = parseInt(securityId || '1000') % 1000 + 100;
  const variation = (Math.random() - 0.5) * 10;
  return Math.round((basePrice + variation) * 100) / 100;
}

function calculatePnL(order) {
  const currentPrice = getMockPrice(order.security_id);
  const pnlPerUnit = currentPrice - order.execution_price;
  const totalPnL = pnlPerUnit * order.execution_quantity;
  
  if (order.transaction_type === 'SELL') {
    return -totalPnL; // Reverse for sell orders
  }
  return totalPnL;
}

// Reset mock portfolio
app.post('/mock/portfolio/reset', (req, res) => {
  mockPortfolio = {
    balance: 1000000,
    positions: [],
    orders: [],
    holdings: [],
    trades: []
  };
  orderIdCounter = 1000;
  
  console.log('📊 Mock Portfolio Reset');
  
  res.json({
    success: true,
    message: 'Mock portfolio reset successfully'
  });
});

app.listen(PORT, () => {
  console.log(`🎯 Mock Trading Server running on http://localhost:${PORT}`);
  console.log('📊 Paper Trading Mode: ENABLED');
  console.log('💰 Virtual Balance: ₹10,00,000');
  console.log('🔄 Orders: Mock execution only');
  console.log('📈 Data: Real Data API (when configured)');
});

module.exports = app;
