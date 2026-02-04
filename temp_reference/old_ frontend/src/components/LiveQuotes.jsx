// Live Quotes Component - Data Flow Indicators
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

const LiveQuotes = () => {
  const [quotes, setQuotes] = useState({
    nifty: { symbol: 'NIFTY', price: null, change: null, status: 'loading' },
    sensex: { symbol: 'SENSEX', price: null, change: null, status: 'loading' },
    crude: { symbol: 'CRUDEOIL', price: null, change: null, status: 'loading' }
  });
  const [lastUpdate, setLastUpdate] = useState(null);

  // Check if market is open
  const isMarketOpen = (exchange) => {
    const now = new Date();
    const day = now.getDay();
    const hours = now.getHours();
    const minutes = now.getMinutes();
    const currentTime = hours * 60 + minutes;

    // Weekend check
    if (day === 0 || day === 6) return false;

    // Market hours (simplified)
    switch (exchange) {
      case 'NSE': // NIFTY
      case 'BSE': // SENSEX
        // 9:15 AM to 3:30 PM (555 to 930 minutes)
        return currentTime >= 555 && currentTime <= 930;
      case 'MCX': // CRUDE OIL
        // 9:00 AM to 11:30 PM (540 to 1410 minutes) 
        return currentTime >= 540 && currentTime <= 1410;
      default:
        return false;
    }
  };

  useEffect(() => {
    const fetchQuotes = async () => {
      try {
        // Fetch NIFTY - use real Dhan API
        let niftyData = { status: 'error', message: 'Not available' };
        try {
          const niftyResponse = await fetch('http://127.0.0.1:5000/api/v1/dhan/quote/NIFTY');
          niftyData = await niftyResponse.json();
        } catch (e) {
          console.log('NIFTY API call failed');
        }

        // Fetch SENSEX - use real Dhan API
        let sensexData = { status: 'error', message: 'Not available' };
        try {
          const sensexResponse = await fetch('http://127.0.0.1:5000/api/v1/dhan/quote/SENSEX');
          sensexData = await sensexResponse.json();
        } catch (e) {
          console.log('SENSEX API call failed');
        }

        // Fetch CRUDEOIL - use mock data with market hours consideration
        let crudeData = { status: 'error', message: 'Not available' };
        try {
          const crudeResponse = await fetch('http://127.0.0.1:5000/api/v1/market/quote/CRUDEOIL');
          if (crudeResponse.ok) {
            const mockData = await crudeResponse.json();
            const isMCXOpen = isMarketOpen('MCX');
            
            crudeData = {
              data: {
                last_price: isMCXOpen ? mockData.data.last_price : mockData.data.close_price,
                change: isMCXOpen ? mockData.data.change : 0
              },
              status: 'success'
            };
          }
        } catch (e) {
          console.log('CRUDEOIL not available');
        }

        // Process quotes
        setQuotes(prev => ({
          ...prev,
          nifty: {
            ...prev.nifty,
            symbol: 'NIFTY',
            price: niftyData.status === 'success' ? niftyData.data.last_price : null,
            change: null, // Dhan LTP API doesn't provide change
            status: niftyData.status === 'success' ? 'success' : 'error',
            source: niftyData.status === 'success' ? 'Dhan API' : 'Error'
          },
          sensex: {
            ...prev.sensex,
            symbol: 'SENSEX', 
            price: sensexData.status === 'success' ? sensexData.data.last_price : null,
            change: null, // Dhan LTP API doesn't provide change
            status: sensexData.status === 'success' ? 'success' : 'error',
            source: sensexData.status === 'success' ? 'Dhan API' : 'Error'
          },
          crude: {
            ...prev.crude,
            symbol: 'CRUDEOIL',
            price: crudeData.status === 'success' ? crudeData.data.last_price : null,
            change: crudeData.status === 'success' ? crudeData.data.change || 0 : null,
            status: isMarketOpen('MCX') ? 'success' : 'market_closed',
            source: 'Mock Data'
          }
        }));
        
        setLastUpdate(new Date());
      } catch (error) {
        console.error('Error fetching live quotes:', error);
        setQuotes(prev => ({
          ...prev,
          nifty: { ...prev.nifty, status: 'error', source: 'Error' },
          sensex: { ...prev.sensex, status: 'error', source: 'Error' },
          crude: { ...prev.crude, status: 'error', source: 'Error' }
        }));
      }
    };

    fetchQuotes();
    const interval = setInterval(fetchQuotes, 5000); // Update every 5 seconds
    
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status, marketClosed = false) => {
    if (marketClosed) return 'text-orange-600';
    switch (status) {
      case 'success': return 'text-green-600';
      case 'error': return 'text-red-600';
      case 'loading': return 'text-gray-400';
      default: return 'text-gray-600';
    }
  };

  const getChangeColor = (change) => {
    if (!change) return 'text-gray-500';
    return change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500';
  };

  const getChangeIcon = (change) => {
    if (!change) return <Activity className="w-3 h-3" />;
    return change > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />;
  };

  const formatPrice = (price) => {
    if (price === null || price === undefined) return '--';
    return typeof price === 'number' ? price.toFixed(2) : price;
  };

  const formatChange = (change) => {
    if (change === null || change === undefined) return '';
    const sign = change > 0 ? '+' : '';
    return `${sign}${change.toFixed(2)}`;
  };

  const getStatusText = (quote) => {
    if (quote.marketClosed) return 'Market Closed';
    if (quote.priceType === 'MOCK_CLOSE') return 'Closed Price';
    if (quote.priceType === 'MOCK_LIVE') return 'Mock Data';
    return quote.status;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <Activity className="w-4 h-4 text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-700">Live Data Flow Indicators</h3>
        </div>
        <div className="text-xs text-gray-500">
          {lastUpdate ? `Updated: ${lastUpdate.toLocaleTimeString()}` : 'Loading...'}
        </div>
      </div>
      
      <div className="grid grid-cols-3 gap-4">
        {/* NIFTY */}
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-600 mb-1">NIFTY INDEX</div>
          <div className={`text-lg font-bold ${getStatusColor(quotes.nifty.status)}`}>
            {formatPrice(quotes.nifty.price)}
          </div>
          <div className={`flex items-center justify-center space-x-1 text-xs ${getChangeColor(quotes.nifty.change)}`}>
            {getChangeIcon(quotes.nifty.change)}
            <span>{formatChange(quotes.nifty.change)}</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">NSE</div>
        </div>

        {/* SENSEX */}
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-600 mb-1">SENSEX INDEX</div>
          <div className={`text-lg font-bold ${getStatusColor(quotes.sensex.status)}`}>
            {formatPrice(quotes.sensex.price)}
          </div>
          <div className={`flex items-center justify-center space-x-1 text-xs ${getChangeColor(quotes.sensex.change)}`}>
            {getChangeIcon(quotes.sensex.change)}
            <span>{formatChange(quotes.sensex.change)}</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">BSE</div>
        </div>

        {/* CRUDEOIL */}
        <div className="text-center p-3 bg-gray-50 rounded-lg">
          <div className="text-xs font-medium text-gray-600 mb-1">CRUDE OIL FUT</div>
          <div className={`text-lg font-bold ${getStatusColor(quotes.crude.status, quotes.crude.marketClosed)}`}>
            {formatPrice(quotes.crude.price)}
          </div>
          <div className={`flex items-center justify-center space-x-1 text-xs ${getChangeColor(quotes.crude.change)}`}>
            {getChangeIcon(quotes.crude.change)}
            <span>{formatChange(quotes.crude.change)}</span>
          </div>
          <div className="text-xs text-gray-500 mt-1">MCX</div>
        </div>
      </div>

      {/* Data Flow Status */}
      <div className="mt-3 pt-3 border-t border-gray-200">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${quotes.nifty.status === 'success' ? 'bg-green-500' : quotes.nifty.status === 'error' ? 'bg-red-500' : 'bg-gray-400'}`}></div>
              <span className="text-gray-600">NIFTY: {getStatusText(quotes.nifty)}</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${quotes.sensex.status === 'success' ? 'bg-green-500' : quotes.sensex.status === 'error' ? 'bg-red-500' : 'bg-gray-400'}`}></div>
              <span className="text-gray-600">SENSEX: {getStatusText(quotes.sensex)}</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${quotes.crude.status === 'success' ? 'bg-green-500' : quotes.crude.status === 'error' ? 'bg-red-500' : quotes.crude.marketClosed ? 'bg-orange-500' : 'bg-gray-400'}`}></div>
              <span className="text-gray-600">CRUDE: {getStatusText(quotes.crude)}</span>
            </div>
          </div>
          <div className="text-gray-500">
            WebSocket: {quotes.nifty.status === 'success' || quotes.sensex.status === 'success' ? '🟢 Active' : '🔴 Inactive'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveQuotes;
