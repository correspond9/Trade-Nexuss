// Custom hook for DhanHQ authentication settings
import { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';

const API_BASE = apiService.baseURL;
const ROOT_BASE = API_BASE.replace(/\/api\/v\d+\/?$/, '');
const LOCAL_CRED_CACHE_KEY = 'dhanCredViewCache';
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

  const extractCredentialData = (result) => {
    if (!result || typeof result !== 'object') return {};
    if (result.data && typeof result.data === 'object' && !Array.isArray(result.data)) {
      // Preferred backend shape: { success, message, data: {...} }
      if (
        'auth_mode' in result.data ||
        'client_id' in result.data ||
        'client_id_prefix' in result.data ||
        'has_token' in result.data
      ) {
        return result.data;
      }

      // Defensive shape: { data: { data: {...} } }
      if (
        result.data.data &&
        typeof result.data.data === 'object' &&
        (
          'auth_mode' in result.data.data ||
          'client_id' in result.data.data ||
          'client_id_prefix' in result.data.data ||
          'has_token' in result.data.data
        )
      ) {
        return result.data.data;
      }
    }
    return result;
  };

  // Load settings from backend
  const loadSavedSettings = async () => {
    // Try primary backend endpoint
    try {
      const result = await apiService.get('/credentials/active');
      const data = extractCredentialData(result);
      const hasPersistedToken = Boolean(
        data?.has_token ||
        data?.has_auth_token ||
        data?.has_daily_token ||
        data?.token_masked
      );
      
      // Check if we have valid credentials
      if (data?.client_id || data?.client_id_prefix || hasPersistedToken) {
        const next = {
          authMode: data.auth_mode || 'DAILY_TOKEN',
          clientId: data.client_id || (data.client_id_prefix ? `${data.client_id_prefix}****` : ''),
          accessToken: hasPersistedToken ? (data.token_masked || '****************') : '', // Masked token placeholder
          apiKey: '',
          clientSecret: '',
          connected: hasPersistedToken,
          lastAuthTime: data.last_updated,
          authStatus: hasPersistedToken ? 'connected' : 'disconnected',
          wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
          _cachedCredentials: {
            DAILY_TOKEN: data,
            STATIC_IP: null
          }
        };
        try {
          localStorage.setItem(
            LOCAL_CRED_CACHE_KEY,
            JSON.stringify({
              authMode: next.authMode,
              clientId: next.clientId,
              hasToken: hasPersistedToken,
              lastAuthTime: next.lastAuthTime,
            })
          );
        } catch (_e) {
          // ignore cache write errors
        }
        return next;
      }
    } catch (e) {
      console.warn('Failed to load credentials via apiService, falling back to legacy URLs', e);
    }

    // Fallback logic ...

      const isLocalHost = (() => {
        try {
          const host = window?.location?.hostname || '';
          return host === 'localhost' || host === '127.0.0.1';
        } catch (_e) {
          return false;
        }
      })();

      const fallbackBases = [
        `${ROOT_BASE}/api/v2/credentials/active`,
        ...(isLocalHost ? ['http://localhost:8000/api/v2/credentials/active', 'http://127.0.0.1:8000/api/v2/credentials/active'] : [])
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

    try {
      const raw = localStorage.getItem(LOCAL_CRED_CACHE_KEY);
      if (raw) {
        const cached = JSON.parse(raw);
        if (cached && cached.clientId) {
          return {
            authMode: cached.authMode || 'DAILY_TOKEN',
            clientId: cached.clientId || '',
            accessToken: cached.hasToken ? '****************' : '',
            apiKey: '',
            clientSecret: '',
            connected: !!cached.hasToken,
            lastAuthTime: cached.lastAuthTime || null,
            authStatus: cached.hasToken ? 'connected' : 'disconnected',
            wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
            _cachedCredentials: {
              DAILY_TOKEN: null,
              STATIC_IP: null
            }
          };
        }
      }
    } catch (_e) {
      // ignore cache read errors
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
      if (!response || response.success !== true || response.error) {
        throw new Error((response && response.error) || 'Failed to save credentials');
      }

      // Clear cached credentials to ensure we fetch latest values
      try {
        apiService.clearCacheEntry('/credentials/active', {});
      } catch (e) {
        // ignore if cache clear not available
      }

      try {
        const refreshed = await loadSavedSettings();
        if (refreshed && (refreshed.clientId || refreshed.accessToken || refreshed.connected)) {
          setLocalSettings(refreshed);
        } else {
          setLocalSettings((prev) => ({
            ...prev,
            connected: true,
            authStatus: 'connected',
            lastAuthTime: new Date().toISOString(),
          }));
        }
      } catch (_refreshError) {
        setLocalSettings((prev) => ({
          ...prev,
          connected: true,
          authStatus: 'connected',
          lastAuthTime: new Date().toISOString(),
        }));
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
