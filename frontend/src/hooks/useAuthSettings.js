// Custom hook for DhanHQ authentication settings
import { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';

const API_BASE = apiService.baseURL;
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
    // Try primary backend endpoint
    try {
      const result = await apiService.get('/credentials/active');
      const data = result?.data || {};
      
      // Check if we have valid credentials
      if (data?.client_id_prefix || data?.has_token) {
        return {
          authMode: data.auth_mode || 'DAILY_TOKEN',
          clientId: data.client_id || (data.client_id_prefix ? `${data.client_id_prefix}****` : ''),
          accessToken: data.has_token ? '****************' : '', // Masked token placeholder
          apiKey: '',
          clientSecret: '',
          connected: data.has_token,
          lastAuthTime: data.last_updated,
          authStatus: data.has_token ? 'connected' : 'disconnected',
          wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
          _cachedCredentials: {
            DAILY_TOKEN: data,
            STATIC_IP: null
          }
        };
      }
    } catch (e) {
      console.warn('Failed to load credentials via apiService, falling back to legacy URLs', e);
    }

    // Fallback logic ...

      const fallbackBases = [
        `${ROOT_BASE}/api/v2/credentials/active`,
        'http://localhost:8000/api/v2/credentials/active',
        'http://127.0.0.1:8000/api/v2/credentials/active'
      ];

      for (const url of fallbackBases) {
        try {
          const result = await apiService.request(url, { method: 'GET', headers: { 'Content-Type': 'application/json' } }).catch(() => null);
          if (!result) continue;
          const data = result?.data || {};
          if (data?.client_id || data?.access_token || data?.daily_token) {
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
          console.error('Error loading settings from fallback url:', url, error);
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

      const response = await apiService.post('/credentials/save', payload);
      if (!response || (response && response.error)) {
        throw new Error((response && response.error) || 'Failed to save credentials');
      }

      // Clear cached credentials to ensure we fetch latest values
      try {
        apiService.clearCacheEntry('/credentials/active', {});
      } catch (e) {
        // ignore if cache clear not available
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
      const res = await apiService.post('/credentials/switch-mode', { auth_mode: newMode });
      if (res && !res.error) {
        // Clear cached credentials so loadSavedSettings fetches fresh data
        try {
          apiService.clearCacheEntry('/credentials/active', {});
        } catch (e) {
          // ignore
        }
        const refreshed = await loadSavedSettings();
        if (refreshed) setLocalSettings(refreshed);
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
