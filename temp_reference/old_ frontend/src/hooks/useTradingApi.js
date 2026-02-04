import { useState, useCallback } from 'react';
import { tradingApiService } from '../services/tradingApiService';

// Hook for order management operations
export const useOrderManagement = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const placeOrder = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.placeOrder(orderData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const placeSmartOrder = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.placeSmartOrder(orderData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const modifyOrder = useCallback(async (orderId, modificationData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.modifyOrder(orderId, modificationData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelOrder = useCallback(async (orderId) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.cancelOrder(orderId);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelAllOrders = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.cancelAllOrders();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const closePosition = useCallback(async (positionData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.closePosition(positionData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    placeOrder,
    placeSmartOrder,
    modifyOrder,
    cancelOrder,
    cancelAllOrders,
    closePosition,
  };
};

// Hook for market data operations
export const useMarketData = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getQuotes = useCallback(async (symbol) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getQuotes(symbol);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getMultiQuotes = useCallback(async (symbols) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getMultiQuotes(symbols);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getHistory = useCallback(async (symbol, interval, from, to) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getHistory(symbol, interval, from, to);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getDepth = useCallback(async (symbol) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getDepth(symbol);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getOptionChain = useCallback(async (symbol, expiry) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getOptionChain(symbol, expiry);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getIntervals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getIntervals();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getQuotes,
    getMultiQuotes,
    getHistory,
    getDepth,
    getOptionChain,
    getIntervals,
  };
};

// Hook for account data operations
export const useAccountData = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getFunds = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getFunds();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getOrderBook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getOrderBook();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getTradeBook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getTradeBook();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getPositionBook = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getPositionBook();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getHoldings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getHoldings();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getFunds,
    getOrderBook,
    getTradeBook,
    getPositionBook,
    getHoldings,
  };
};

// Hook for options trading operations
export const useOptionsTrading = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const placeOptionsOrder = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.placeOptionsOrder(orderData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const placeOptionsMultiOrder = useCallback(async (orders) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.placeOptionsMultiOrder(orders);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getOptionGreeks = useCallback(async (symbol) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getOptionGreeks(symbol);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getMultiOptionGreeks = useCallback(async (symbols) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getMultiOptionGreeks(symbols);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSyntheticFuture = useCallback(async (symbol, expiry) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getSyntheticFuture(symbol, expiry);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    placeOptionsOrder,
    placeOptionsMultiOrder,
    getOptionGreeks,
    getMultiOptionGreeks,
    getSyntheticFuture,
  };
};

// Hook for market information
export const useMarketInfo = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getMarketHolidays = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getMarketHolidays();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getMarketTimings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getMarketTimings();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getInstruments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getInstruments();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getMarketHolidays,
    getMarketTimings,
    getInstruments,
  };
};

// Hook for analysis and tools
export const useAnalysis = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const getAnalyzerData = useCallback(async (symbol, strategy) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getAnalyzerData(symbol, strategy);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getPnLSymbols = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.getPnLSymbols();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const ping = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.ping();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const calculateMargin = useCallback(async (orderData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await tradingApiService.calculateMargin(orderData);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    getAnalyzerData,
    getPnLSymbols,
    ping,
    calculateMargin,
  };
};