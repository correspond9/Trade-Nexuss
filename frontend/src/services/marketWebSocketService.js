import { useWebSocket } from '../hooks/useWebSocket';
import { useState, useEffect } from 'react';

export function useMarketWebSocket(wsUrl = 'ws://127.0.0.1:8000/ws/prices') {
  const { lastMessage, sendMessage, readyState } = useWebSocket(wsUrl);
  const [marketData, setMarketData] = useState({
    quotes: {},
    orderbook: {},
    positions: {},
    holdings: {}
  });

  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type) {
          switch(data.type) {
            case 'quotes':
              setMarketData(prev => ({ ...prev, quotes: data.payload }));
              break;
            case 'orderbook':
              setMarketData(prev => ({ ...prev, orderbook: data.payload }));
              break;
            case 'positions':
              setMarketData(prev => ({ ...prev, positions: data.payload }));
              break;
            case 'holdings':
              setMarketData(prev => ({ ...prev, holdings: data.payload }));
              break;
          }
        } else {
          setMarketData(prev => ({ ...prev, quotes: data }));
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error);
      }
    }
  }, [lastMessage]);

  const subscribeToSymbol = (symbol) => {
    sendMessage(JSON.stringify({
      action: 'subscribe',
      symbol: symbol,
      type: 'quote'
    }));
  };

  const unsubscribeFromSymbol = (symbol) => {
    sendMessage(JSON.stringify({
      action: 'unsubscribe',
      symbol: symbol,
      type: 'quote'
    }));
  };

  return {
    marketData,
    subscribeToSymbol,
    unsubscribeFromSymbol,
    readyState
  };
}