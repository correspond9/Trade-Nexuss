import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url) => {
  const [lastMessage, setLastMessage] = useState(null);
  const [readyState, setReadyState] = useState(WebSocket.CONNECTING);
  const [sendMessage, setSendMessage] = useState(() => () => {});
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const connectTimeout = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 3;

  const connect = useCallback(() => {
    try {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      if (connectTimeout.current) {
        clearTimeout(connectTimeout.current);
        connectTimeout.current = null;
      }

      if (!url) {
        setReadyState(WebSocket.CLOSED);
        return;
      }
      const lowerUrl = String(url || '').toLowerCase();
      if (lowerUrl.includes('dhan.co')) {
        throw new Error('Frontend direct Dhan WebSocket connections are disabled. Use backend websocket endpoints only.');
      }
      ws.current = new WebSocket(url);
      setReadyState(WebSocket.CONNECTING);

      connectTimeout.current = setTimeout(() => {
        if (ws.current && ws.current.readyState === WebSocket.CONNECTING) {
          ws.current.close(4000, 'Connection timeout');
        }
      }, 4000);
      
      ws.current.onopen = () => {
        console.log('WebSocket connected to:', url);
        setReadyState(WebSocket.OPEN);
        reconnectAttempts.current = 0;
        if (connectTimeout.current) {
          clearTimeout(connectTimeout.current);
          connectTimeout.current = null;
        }
        
        // Set up send message function
        setSendMessage(() => (message) => {
          if (ws.current && ws.current.readyState === WebSocket.OPEN) {
            ws.current.send(message);
          } else {
            console.warn('WebSocket is not connected');
          }
        });
      };

      ws.current.onmessage = (event) => {
        setLastMessage(event);
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setReadyState(WebSocket.CLOSED);
        if (connectTimeout.current) {
          clearTimeout(connectTimeout.current);
          connectTimeout.current = null;
        }
        
        // Attempt reconnection if not explicitly closed
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts &&
          navigator.onLine !== false
        ) {
          reconnectAttempts.current++;
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          
          console.log(`Attempting reconnection ${reconnectAttempts.current}/${maxReconnectAttempts} in ${delay}ms`);
          
          reconnectTimeout.current = setTimeout(() => {
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
        setReadyState(WebSocket.CLOSED);
      };

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setReadyState(WebSocket.CLOSED);
    }
  }, [url]);

  useEffect(() => {
    if (!url) {
      return undefined;
    }
    connect();
    
    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
      if (connectTimeout.current) {
        clearTimeout(connectTimeout.current);
        connectTimeout.current = null;
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounted');
      }
    };
  }, [connect, url]);

  return {
    lastMessage,
    sendMessage,
    readyState,
    reconnect: connect
  };
};
