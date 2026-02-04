// Live Quotes Component - Data Flow Indicators with Real-time Price Display
import React, { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, RefreshCw } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v2';
const ROOT_BASE = API_BASE.replace(/\/api\/v\d+\/?$/, '');

const CORE_INSTRUMENTS = [
  { key: 'NIFTY', label: 'NIFTY 50', exchange: 'NSE', badge: 'bg-blue-100 text-blue-700' },
  { key: 'BANKNIFTY', label: 'BANKNIFTY', exchange: 'NSE', badge: 'bg-indigo-100 text-indigo-700' },
  { key: 'SENSEX', label: 'SENSEX', exchange: 'BSE', badge: 'bg-amber-100 text-amber-700' },
  { key: 'CRUDEOIL', label: 'CRUDEOIL FUT', exchange: 'MCX', badge: 'bg-purple-100 text-purple-700' },
  { key: 'RELIANCE', label: 'RELIANCE', exchange: 'NSE', badge: 'bg-emerald-100 text-emerald-700' },
];

const LiveQuotes = () => {
  const [quotes, setQuotes] = useState(() =>
    CORE_INSTRUMENTS.reduce((acc, instrument) => {
      acc[instrument.key] = {
        symbol: instrument.key,
        price: null,
        status: 'loading',
        exchange: instrument.exchange,
      };
      return acc;
    }, {})
  );
  const [lastUpdate, setLastUpdate] = useState(null);
  const [dataFlowStatus, setDataFlowStatus] = useState('checking');

  useEffect(() => {
    let ws = null;
    let reconnectTimeout = null;

    const connectWebSocket = () => {
      try {
        // Connect to backend on port 8000, not the dev server
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const backendHost = window.location.hostname;
        const wsUrl = `${protocol}//${backendHost}:8000/ws/prices`;
        console.log('[LiveQuotes] WebSocket connecting to backend:', wsUrl);
        
        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('[LiveQuotes] WebSocket connected to:', wsUrl);
          setDataFlowStatus('checking');
        };

        ws.onmessage = (event) => {
          try {
            const priceData = JSON.parse(event.data);
            console.log('[LiveQuotes] Received prices:', priceData);

            // Update quotes with new prices
            setQuotes(prev => {
              const updated = { ...prev };
              CORE_INSTRUMENTS.forEach(({ key }) => {
                if (priceData[key]) {
                  updated[key] = {
                    ...updated[key],
                    price: priceData[key],
                    status: 'success'
                  };
                } else {
                  updated[key] = {
                    ...updated[key],
                    status: 'no_data'
                  };
                }
              });
              return updated;
            });

            // Check overall data flow status
            const activePrices = Object.values(priceData).filter(p => p && typeof p === 'number' && p > 0);
            setDataFlowStatus(activePrices.length > 0 ? 'active' : 'waiting');
            setLastUpdate(new Date());
          } catch (error) {
            console.error('Error parsing WebSocket message:', error, 'Raw data:', event.data);
          }
        };

        ws.onerror = (error) => {
          console.error('[LiveQuotes] WebSocket error:', error);
          setDataFlowStatus('error');
        };

        ws.onclose = () => {
          console.log('[LiveQuotes] WebSocket disconnected, reconnecting in 2s...');
          // Reconnect after 2 seconds
          reconnectTimeout = setTimeout(connectWebSocket, 2000);
        };
      } catch (error) {
        console.error('[LiveQuotes] Error connecting WebSocket:', error);
        setDataFlowStatus('error');
        reconnectTimeout = setTimeout(connectWebSocket, 2000);
      }
    };

    connectWebSocket();

    return () => {
      if (ws) {
        ws.close();
      }
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
    };
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800';
      case 'no_data': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'loading': return 'bg-gray-100 text-gray-600';
      default: return 'bg-gray-100 text-gray-600';
    }
  };

  const getDataFlowIndicator = () => {
    switch (dataFlowStatus) {
      case 'active':
        return { color: 'bg-green-500', text: 'Data Flowing', pulse: true };
      case 'waiting':
        return { color: 'bg-yellow-500', text: 'Waiting for Data', pulse: false };
      case 'error':
        return { color: 'bg-red-500', text: 'Connection Error', pulse: false };
      default:
        return { color: 'bg-gray-400', text: 'Checking...', pulse: false };
    }
  };

  const formatPrice = (price) => {
    if (price === null || price === undefined || price === 0) return '--';
    return typeof price === 'number' ? price.toFixed(2) : price;
  };

  const dataFlowIndicator = getDataFlowIndicator();

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg shadow-sm border border-blue-200 p-4 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Activity className="w-5 h-5 text-blue-600" />
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Market Data Stream</h3>
            <p className="text-xs text-gray-600">Real-time instrument prices</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <div className="text-right">
            <div className="text-xs text-gray-600">Last Update</div>
            <div className="text-sm font-mono text-gray-900">
              {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Waiting...'}
            </div>
          </div>
          <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${getStatusColor('success')}`}>
            <div className={`w-2 h-2 rounded-full ${dataFlowIndicator.color} ${dataFlowIndicator.pulse ? 'animate-pulse' : ''}`}></div>
            <span className="text-xs font-medium">{dataFlowIndicator.text}</span>
          </div>
        </div>
      </div>

      {/* Price Grid - dedicated to five core instruments */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 mb-4">
        {CORE_INSTRUMENTS.map(({ key, label, exchange, badge }) => (
          <div key={key} className="bg-white rounded-lg p-2 border border-gray-200 hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-1">
              <div className="text-xs font-semibold text-gray-700">{label}</div>
              <div className={`text-[10px] px-1.5 py-0.5 rounded-full ${badge}`}>{exchange}</div>
            </div>
            <div className={`text-lg font-bold ${quotes[key].status === 'success' ? 'text-green-600' : 'text-gray-400'}`}>
              {formatPrice(quotes[key].price)}
            </div>
            <div className="text-[11px] text-gray-500 mt-0.5">
              {quotes[key].status === 'success'
                ? '✓ Live'
                : quotes[key].status === 'no_data'
                  ? 'No Data'
                  : quotes[key].status}
            </div>
          </div>
        ))}
      </div>

      {/* Data Summary Footer */}
      <div className="bg-white rounded-lg p-3 border border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="text-sm">
              <span className="text-gray-600">Active Instruments: </span>
              <span className="font-semibold text-green-600">
                {Object.values(quotes).filter(q => q.status === 'success').length} / {CORE_INSTRUMENTS.length}
              </span>
            </div>
            <div className="text-sm">
              <span className="text-gray-600">Update Frequency: </span>
              <span className="font-semibold text-blue-600">Real-time (WebSocket)</span>
            </div>
          </div>
          <div className="text-xs text-gray-500">
            Endpoint: /ws/prices | Status: {dataFlowStatus}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LiveQuotes;
