import { useMemo } from 'react';
import { useWebSocket } from './useWebSocket';
import { apiService } from '../services/apiService';

const toWebSocketUrl = (apiBase, endpointPath) => {
  const safePath = endpointPath.startsWith('/') ? endpointPath : `/${endpointPath}`;
  const fallbackOrigin = typeof window !== 'undefined' ? window.location.origin : 'http://127.0.0.1:8000';

  try {
    const base = new URL(apiBase, fallbackOrigin);
    const wsProtocol = base.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${base.host}${safePath}`;
  } catch (_error) {
    const wsProtocol = fallbackOrigin.startsWith('https') ? 'wss:' : 'ws:';
    const host = fallbackOrigin.replace(/^https?:\/\//, '');
    return `${wsProtocol}//${host}${safePath}`;
  }
};

export const useMarketPulse = () => {
  const wsUrl = useMemo(
    () => toWebSocketUrl(apiService.baseURL, '/api/v2/ws/prices'),
    []
  );

  const { lastMessage, readyState } = useWebSocket(wsUrl);

  const pulse = useMemo(() => {
    if (!lastMessage?.data) {
      return {
        timestamp: null,
        status: 'idle',
        prices: {},
      };
    }

    try {
      const parsed = JSON.parse(lastMessage.data);
      const { timestamp = null, status = 'unknown', ...prices } = parsed || {};
      return { timestamp, status, prices };
    } catch (_error) {
      return {
        timestamp: null,
        status: 'parse_error',
        prices: {},
      };
    }
  }, [lastMessage]);

  return {
    pulse,
    readyState,
    marketActive: pulse.status === 'active',
  };
};
