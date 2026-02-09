// Custom hook for DhanHQ authentication settings
import { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v2';
const ROOT_BASE = API_BASE.replace(/\/api\/v\d+\/?$/, '');
const CREDENTIALS_BASE = `${API_BASE}/credentials`;

export const useAuthSettings = () => {
  const [localSettings, setLocalSettings] = useState({
    authMode: 'DAILY_TOKEN', // DAILY_TOKEN or STATIC_IP
    clientId: '',
    accessToken: '',
    apiKey: '',
    clientSecret: '',
    connected: false,
    lastAuthTime: null,
    authStatus: 'disconnected',
    wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
  });

  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  // Load settings from backend
  const loadSavedSettings = async () => {
    const fallbackBases = [
      `${CREDENTIALS_BASE}/active`,
      `${ROOT_BASE}/api/v2/credentials/active`,
      'http://localhost:8000/api/v2/credentials/active',
      'http://127.0.0.1:8000/api/v2/credentials/active'
    ];

    for (const url of fallbackBases) {
      try {
        const response = await fetch(url, {
          headers: { 'Content-Type': 'application/json' },
        });

        if (!response.ok) {
          console.warn('🔐 Credentials fetch failed:', url, response.status);
          continue;
        }

        const result = await response.json();
        const data = result?.data || {};
        if (data?.client_id || data?.access_token || data?.daily_token) {
          console.log('🔐 Credentials loaded from:', url);
          return {
            authMode: data.auth_mode || 'DAILY_TOKEN',
            clientId: data.client_id || '',
            accessToken: data.access_token || '',
            apiKey: data.api_key || '',
            clientSecret: data.secret_api || '',
            connected: false,
            lastAuthTime: null,
            authStatus: 'disconnected',
            wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
            _cachedCredentials: {
              DAILY_TOKEN: data,
              STATIC_IP: null
            }
          };
        }
      } catch (error) {
        console.error('Error loading settings from:', url, error);
      }
    }

    return {
      authMode: 'DAILY_TOKEN',
      clientId: '',
      accessToken: '',
      apiKey: '',
      clientSecret: '',
      connected: false,
      lastAuthTime: null,
      authStatus: 'disconnected',
      wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
      _cachedCredentials: {
        DAILY_TOKEN: null,
        STATIC_IP: null
      }
    };
  };

  // Save settings
  const saveSettings = async () => {
    try {
      console.log('🔐 Starting saveSettings...');
      console.log('🔐 Current settings:', localSettings);
      
      setSaved(true);
      
      const authHeaders = { 'Content-Type': 'application/json' };

      if (!localSettings.clientId || !localSettings.accessToken) {
        throw new Error('Client ID and Access Token are required');
      }

      if (localSettings.authMode === 'STATIC_IP') {
        if (!localSettings.apiKey || !localSettings.clientSecret) {
          throw new Error('API Key and Client Secret are required for Static IP mode');
        }
      }

      const payload = {
        client_id: localSettings.clientId,
        access_token: localSettings.accessToken,
        api_key: localSettings.apiKey || '',
        secret_api: localSettings.clientSecret || '',
        daily_token: localSettings.accessToken,
        auth_mode: localSettings.authMode
      };

      const response = await fetch(`${CREDENTIALS_BASE}/save`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save credentials');
      }

      const refreshed = await loadSavedSettings();
      if (refreshed) {
        setLocalSettings(refreshed);
      }

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      
    } catch (error) {
      console.error('🔐 SaveSettings error:', error);
      setSaved(false);
      throw error;
    }
  };

  // Switch authentication mode
  const switchMode = async (newMode) => {
    try {
      const authHeaders = { 'Content-Type': 'application/json' };
      const response = await fetch(`${CREDENTIALS_BASE}/switch-mode`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ auth_mode: newMode })
      });

      if (response.ok) {
        const refreshed = await loadSavedSettings();
        if (refreshed) {
          setLocalSettings(refreshed);
        }
      } else {
        setLocalSettings(prev => ({ ...prev, authMode: newMode }));
      }
    } catch (error) {
      console.error('Error switching mode:', error);
    }
  };

  // Initialize on mount
  useEffect(() => {
    const initializeSettings = async () => {
      try {
        const settings = await loadSavedSettings();
        if (settings) {
          setLocalSettings(settings);
        }
      } catch (error) {
        console.error('Error initializing settings:', error);
      } finally {
        setLoading(false);
      }
    };
    
    initializeSettings();
  }, []);

  return {
    localSettings,
    setLocalSettings,
    saved,
    setSaved,
    loading,
    setLoading,
    saveSettings,
    switchMode,
  };
};
