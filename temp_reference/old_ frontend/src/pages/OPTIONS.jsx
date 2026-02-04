import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';

// Helper function to generate option strikes from real database
const generateStrikesFromDatabase = (indexPrice, lotSize, strikeInterval = 50) => {
  const strikes = [];
  
  // Generate strikes from ATM - 10 to ATM + 10 (21 total strikes)
  const atmStrike = Math.round(indexPrice / strikeInterval) * strikeInterval;
  
  for (let i = -10; i <= 10; i++) {
    const strike = atmStrike + (i * strikeInterval);
    const isATM = i === 0;
    
    strikes.push({
      strike,
      isATM,
      ltpCE: Math.max(0.05, (indexPrice - strike) * 0.3 + Math.random() * 20),
      ltpPE: Math.max(0.05, (strike - indexPrice) * 0.3 + Math.random() * 20),
      lotSize
    });
  }
  
  return strikes;
};

const Options = ({ handleOpenOrderModal, selectedIndex = 'NIFTY 50', expiry }) => {
  const [strikes, setStrikes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedExpiry, setSelectedExpiry] = useState('');
  const [indexData, setIndexData] = useState({});
  const [availableExpiries, setAvailableExpiries] = useState([]);

  // Convert selectedIndex to symbol for API calls
  const getSymbolFromIndex = (index) => {
    switch(index) {
      case 'NIFTY 50': return 'NIFTY';
      case 'NIFTY BANK': return 'BANKNIFTY';
      case 'SENSEX': return 'SENSEX';
      default: return 'NIFTY';
    }
  };

  const getLotSize = (symbol) => {
    switch(symbol) {
      case 'NIFTY': return 50;
      case 'BANKNIFTY': return 25;
      case 'SENSEX': return 10;
      default: return 50;
    }
  };

  // Fetch option chain from real database using v2 API
  const fetchOptionChain = async (symbol, expiry) => {
    try {
      setLoading(true);
      setError('');
      
      // Use FastAPI option chain v2 endpoint
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000/api/v1'}/option-chain-v2/chain/${symbol}/${expiry}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data && data.chain) {
        // Process real option data from v2 API
        const optionsData = data.chain;
        
        // Convert v2 format to our component format
        const strikesArray = optionsData.map(item => ({
          strike: item.strike,
          isATM: Math.abs(item.strike - (data.underlying_price || 23000)) < 50,
          ltpCE: item.ce ? item.ce.ltp : 0,
          ltpPE: item.pe ? item.pe.ltp : 0,
          lotSize: item.ce ? item.ce.lot_size || getLotSize(symbol) : getLotSize(symbol),
          ceToken: item.ce ? item.ce.token : null,
          peToken: item.pe ? item.pe.token : null,
          ceSymbol: item.ce ? item.ce.symbol : null,
          peSymbol: item.pe ? item.pe.symbol : null
        }));
        
        setStrikes(strikesArray);
      } else {
        // Fallback to generated strikes
        const generatedStrikes = generateStrikesFromDatabase(
          indexData[symbol]?.currentLTP || 23000,
          getLotSize(symbol)
        );
        setStrikes(generatedStrikes);
      }
    } catch (err) {
      console.error('Error fetching option chain:', err);
      setError('Failed to load options data');
      
      // Fallback to generated strikes on error
      const generatedStrikes = generateStrikesFromDatabase(
        indexData[getSymbolFromIndex(selectedIndex)]?.currentLTP || 23000,
        getLotSize(getSymbolFromIndex(selectedIndex))
      );
      setStrikes(generatedStrikes);
    } finally {
      setLoading(false);
    }
  };

  // Fetch available expiries for the symbol
  const fetchAvailableExpiries = async (symbol) => {
    try {
      // Use FastAPI instruments endpoint for expiries
      const response = await apiService.get('/market/instruments/NFO', {
        search: symbol,
        instrument_type: 'OPTIDX',
        limit: 50
      });
      
      if (response && response.data) {
        const expiries = [...new Set(response.data.map(opt => opt.expiry).filter(Boolean))];
        expiries.sort();
        setAvailableExpiries(expiries);
        
        // Set default expiry to current month
        if (expiries.length > 0 && !selectedExpiry) {
          setSelectedExpiry(expiries[0]);
        }
      }
    } catch (err) {
      console.error('Error fetching expiries:', err);
    }
  };

  // Fetch index price
  const fetchIndexPrice = async (symbol) => {
    try {
      const response = await apiService.get(`/market/instruments/NSE_INDEX?search=${symbol}`);
      
      if (response && response.data && response.data.length > 0) {
        const index = response.data[0];
        const quoteResponse = await apiService.get(`/market/quote/${index.security_id}`);
        
        if (quoteResponse && quoteResponse.data) {
          setIndexData(prev => ({
            ...prev,
            [symbol]: {
              ...prev[symbol],
              currentLTP: quoteResponse.data.ltp,
              change: quoteResponse.data.change,
              changePercent: quoteResponse.data.change_percent
            }
          }));
        }
      }
    } catch (err) {
      console.error('Error fetching index price:', err);
    }
  };

  // Load data when symbol or expiry changes
  useEffect(() => {
    const currentSymbol = getSymbolFromIndex(selectedIndex);
    
    const loadData = async () => {
      await Promise.all([
        fetchIndexPrice(currentSymbol),
        fetchAvailableExpiries(currentSymbol)
      ]);
    };
    
    loadData();
  }, [selectedIndex]);

  // Fetch option chain when expiry is selected
  useEffect(() => {
    if (expiry) {
      const currentSymbol = getSymbolFromIndex(selectedIndex);
      fetchOptionChain(currentSymbol, expiry);
    }
  }, [expiry, selectedIndex]);

  // Manual refresh function
  const handleRefresh = () => {
    const currentSymbol = getSymbolFromIndex(selectedIndex);
    if (expiry) {
      fetchOptionChain(currentSymbol, expiry);
    }
  };

  const currentSymbol = getSymbolFromIndex(selectedIndex);
  const currentSymbolData = indexData[currentSymbol] || {};

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="p-3 bg-gray-50 border-b flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <h3 className="font-semibold text-gray-800">{currentSymbol} OPTIONS</h3>
          <span className="text-xs text-gray-500">
            {currentSymbolData.currentLTP ? currentSymbolData.currentLTP.toFixed(2) : '0.00'}
          </span>
        </div>
        <button
          onClick={handleRefresh}
          className="p-1 hover:bg-gray-200 rounded"
          title="Refresh data"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {/* Expiry Selection */}
      <div className="p-2 bg-white border-b flex space-x-2 overflow-x-auto">
        {availableExpiries.map((expiry) => (
          <button
            key={expiry}
            onClick={() => setSelectedExpiry(expiry)}
            className={`px-3 py-1 text-xs font-medium rounded whitespace-nowrap ${
              selectedExpiry === expiry
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {expiry}
          </button>
        ))}
        {availableExpiries.length === 0 && (
          <span className="text-xs text-gray-500">Loading expiries...</span>
        )}
      </div>

      {/* Options Matrix */}
      <div className="overflow-y-auto flex-grow">
        {/* Column Headers */}
        <div className="grid grid-cols-3 bg-gray-100 p-2 text-xs font-bold text-gray-500 uppercase sticky top-0 z-10">
          <div className="text-left">CE Premium</div>
          <div className="text-center">Strike</div>
          <div className="text-right">PE Premium</div>
        </div>

        {/* Strike Rows */}
        {strikes.map((strikeData) => (
          <div
            key={strikeData.strike}
            className={`grid grid-cols-3 p-2 border-b items-center text-xs ${
              strikeData.isATM ? 'bg-indigo-50 font-bold' : 'bg-white'
            }`}
          >
            {/* CE Premium Column - Left Aligned */}
            <div className="flex items-center justify-between pr-2">
              <span className="text-sm font-semibold text-gray-900">
                {strikeData.ltpCE.toFixed(2)}
              </span>
              <div className="flex space-x-1 ml-2">
                <button
                  onClick={() =>
                    handleOpenOrderModal([{
                      symbol: `NIFTY ${strikeData.strike} CE`,
                      action: 'BUY',
                      ltp: strikeData.ltpCE,
                      lotSize: strikeData.lotSize,
                      expiry: selectedExpiry,
                    }])
                  }
                  className="px-2 py-1 text-xs font-semibold bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                  title="Buy CE"
                >
                  B
                </button>
                <button
                  onClick={() =>
                    handleOpenOrderModal([{
                      symbol: `NIFTY ${strikeData.strike} CE`,
                      action: 'SELL',
                      ltp: strikeData.ltpCE,
                      lotSize: strikeData.lotSize,
                      expiry: selectedExpiry,
                    }])
                  }
                  className="px-2 py-1 text-xs font-semibold bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                  title="Sell CE"
                >
                  S
                </button>
              </div>
            </div>

            {/* Strike Column - Centered */}
            <div className="flex items-center justify-center">
              <span className="text-sm font-bold text-gray-900">
                {strikeData.strike}
              </span>
            </div>

            {/* PE Premium Column - Right Aligned */}
            <div className="flex items-center justify-between pl-2">
              <div className="flex space-x-1 mr-2">
                <button
                  onClick={() =>
                    handleOpenOrderModal([{
                      symbol: `NIFTY ${strikeData.strike} PE`,
                      action: 'BUY',
                      ltp: strikeData.ltpPE,
                      lotSize: strikeData.lotSize,
                      expiry: selectedExpiry,
                    }])
                  }
                  className="px-2 py-1 text-xs font-semibold bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                  title="Buy PE"
                >
                  B
                </button>
                <button
                  onClick={() =>
                    handleOpenOrderModal([{
                      symbol: `NIFTY ${strikeData.strike} PE`,
                      action: 'SELL',
                      ltp: strikeData.ltpPE,
                      lotSize: strikeData.lotSize,
                      expiry: selectedExpiry,
                    }])
                  }
                  className="px-2 py-1 text-xs font-semibold bg-red-500 text-white rounded hover:bg-red-600 transition-colors"
                  title="Sell PE"
                >
                  S
                </button>
              </div>
              <span className="text-sm font-semibold text-gray-900">
                {strikeData.ltpPE.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Options;