import { apiService } from './apiService';

// Trading API service for OpenAlgo backend integration
class TradingApiService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v2';
  }

  // Order Management
  async placeOrder(orderData) {
    return apiService.post('/placeorder', orderData);
  }

  async placeSmartOrder(orderData) {
    return apiService.post('/placesmartorder', orderData);
  }

  async modifyOrder(orderId, modificationData) {
    return apiService.post('/modifyorder', {
      order_id: orderId,
      ...modificationData
    });
  }

  async cancelOrder(orderId) {
    return apiService.post('/cancelorder', { order_id: orderId });
  }

  async cancelAllOrders() {
    return apiService.post('/cancelallorder', {});
  }

  async closePosition(positionData) {
    return apiService.post('/closeposition', positionData);
  }

  // Market Data
  async getQuotes(symbol) {
    return apiService.get('/quotes', { symbol });
  }

  async getMultiQuotes(symbols) {
    return apiService.get('/multiquotes', { symbols: symbols.join(',') });
  }

  async getHistory(symbol, interval, from, to) {
    return apiService.get('/history', {
      symbol,
      interval,
      from,
      to
    });
  }

  async getDepth(symbol) {
    return apiService.get('/depth', { symbol });
  }

  async getOptionChain(symbol, expiry) {
    return apiService.get('/optionchain', { symbol, expiry });
  }

  async getIntervals() {
    return apiService.get('/intervals');
  }

  // Account Data
  async getFunds() {
    return apiService.get('/funds');
  }

  async getOrderBook() {
    return apiService.get('/orderbook');
  }

  async getTradeBook() {
    return apiService.get('/tradebook');
  }

  async getPositionBook() {
    return apiService.get('/positionbook');
  }

  async getHoldings() {
    return apiService.get('/holdings');
  }

  // Advanced Features
  async getBasketOrder(basketId) {
    return apiService.get('/basketorder', { basket_id: basketId });
  }

  async splitOrder(orderData) {
    return apiService.post('/splitorder', orderData);
  }

  async getOrderStatus(orderId) {
    return apiService.get('/orderstatus', { order_id: orderId });
  }

  async getOpenPosition() {
    return apiService.get('/openposition');
  }

  async getTicker(symbol) {
    return apiService.get('/ticker', { symbol });
  }

  // Symbol and Search
  async getSymbol(symbol) {
    return apiService.get('/symbol', { symbol });
  }

  async searchSymbols(query) {
    return apiService.get('/search', { q: query });
  }

  async getExpiry(symbol) {
    return apiService.get('/expiry', { symbol });
  }

  async getOptionSymbol(symbol, expiry, strike, optionType) {
    return apiService.get('/optionsymbol', {
      symbol,
      expiry,
      strike,
      option_type: optionType
    });
  }

  // Options Trading
  async placeOptionsOrder(orderData) {
    return apiService.post('/optionsorder', orderData);
  }

  async placeOptionsMultiOrder(orders) {
    return apiService.post('/optionsmultiorder', { orders });
  }

  async getOptionGreeks(symbol) {
    return apiService.get('/optiongreeks', { symbol });
  }

  async getMultiOptionGreeks(symbols) {
    return apiService.get('/multioptiongreeks', { symbols: symbols.join(',') });
  }

  async getSyntheticFuture(symbol, expiry) {
    return apiService.get('/syntheticfuture', { symbol, expiry });
  }

  // Market Information
  async getMarketHolidays() {
    return apiService.get('/market/holidays');
  }

  async getMarketTimings() {
    return apiService.get('/market/timings');
  }

  // Analysis and Tools
  async getAnalyzerData(symbol, strategy) {
    return apiService.get('/analyzer', { symbol, strategy });
  }

  async getPnLSymbols() {
    return apiService.get('/pnl');
  }

  // System Health
  async ping() {
    return apiService.get('/ping');
  }

  // Margin Calculation
  async calculateMargin(orderData) {
    return apiService.post('/margin', orderData);
  }

  // Instruments
  async getInstruments() {
    return apiService.get('/instruments');
  }

  // Chart Data
  async getChartData(symbol, interval, from, to) {
    return apiService.get('/chart', {
      symbol,
      interval,
      from,
      to
    });
  }
}

export const tradingApiService = new TradingApiService();
export default tradingApiService;