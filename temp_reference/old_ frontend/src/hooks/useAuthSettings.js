// Custom hook for DhanHQ authentication settings
import { useState, useEffect } from 'react';
import { authService } from '../services/authService';

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
    try {
      // Get active authentication mode
      const modeResponse = await fetch('http://127.0.0.1:5000/api/v1/credentials/active', {
        headers: { 'Content-Type': 'application/json' },
      });
      
      if (modeResponse.ok) {
        const modeResult = await modeResponse.json();
        const activeMode = modeResult.active_mode || 'DAILY_TOKEN';
        
        // Get credentials for both modes
        const [dailyTokenResponse, staticIpResponse] = await Promise.all([
          fetch('http://127.0.0.1:5000/api/v1/credentials?auth_mode=DAILY_TOKEN', {
            headers: { 'Content-Type': 'application/json' },
          }),
          fetch('http://127.0.0.1:5000/api/v1/credentials?auth_mode=STATIC_IP', {
            headers: { 'Content-Type': 'application/json' },
          })
        ]);
        
        let dailyTokenCreds = null;
        let staticIpCreds = null;
        
        if (dailyTokenResponse.ok) {
          const dailyResult = await dailyTokenResponse.json();
          if (dailyResult.length > 0) {
            dailyTokenCreds = dailyResult[0];
          }
        }
        
        if (staticIpResponse.ok) {
          const staticResult = await staticIpResponse.json();
          if (staticResult.length > 0) {
            staticIpCreds = staticResult[0];
          }
        }
        
        // Return credentials for the active mode, but we have both cached
        const activeCreds = activeMode === 'DAILY_TOKEN' ? dailyTokenCreds : staticIpCreds;
        
        if (activeCreds) {
          return {
            authMode: activeMode,
            clientId: activeCreds.client_id || '',
            accessToken: activeCreds.access_token || '',
            apiKey: activeCreds.api_key || '',
            clientSecret: activeCreds.client_secret || '',
            connected: false,
            lastAuthTime: activeCreds.last_used_at || activeCreds.created_at || null,
            authStatus: 'disconnected',
            wsUrl: 'wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2',
            // Cache both modes for quick switching
            _cachedCredentials: {
              DAILY_TOKEN: dailyTokenCreds,
              STATIC_IP: staticIpCreds
            }
          };
        }
      }
    } catch (error) {
      console.error('Error loading settings:', error);
    }
    
    // Default settings
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
      let response;
      
      // Save credentials based on auth mode
      if (localSettings.authMode === 'DAILY_TOKEN') {
        console.log('🔐 Saving DAILY_TOKEN credentials...');
        
        // Validate daily token fields
        if (!localSettings.clientId || !localSettings.accessToken) {
          throw new Error('Client ID and Access Token are required for Daily Token mode');
        }
        
        const payload = {
          auth_mode: 'DAILY_TOKEN',
          client_id: localSettings.clientId,
          access_token: localSettings.accessToken,
          is_default: true
        };
        
        console.log('🔐 Payload:', payload);
        
        response = await fetch('http://127.0.0.1:5000/api/v1/credentials', {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify(payload)
        });
        
        console.log('🔐 Response status:', response.status);
        console.log('🔐 Response headers:', response.headers);
        
        if (!response.ok) {
          const error = await response.json();
          console.error('🔐 Error response:', error);
          throw new Error(error.detail || 'Failed to save credentials');
        }
        
        const result = await response.json();
        console.log('🔐 Success response:', result);
        
      } else if (localSettings.authMode === 'STATIC_IP') {
        console.log('🔐 Saving STATIC_IP credentials...');
        
        // Validate static IP fields
        if (!localSettings.apiKey || !localSettings.clientSecret) {
          throw new Error('API Key and Client Secret are required for Static IP mode');
        }
        
        const payload = {
          auth_mode: 'STATIC_IP',
          api_key: localSettings.apiKey,
          client_secret: localSettings.clientSecret,
          is_default: true
        };
        
        console.log('🔐 Payload:', payload);
        
        response = await fetch('http://127.0.0.1:5000/api/v1/credentials', {
          method: 'POST',
          headers: authHeaders,
          body: JSON.stringify(payload)
        });
        
        console.log('🔐 Response status:', response.status);
        
        if (!response.ok) {
          const error = await response.json();
          console.error('🔐 Error response:', error);
          throw new Error(error.detail || 'Failed to save credentials');
        }
        
        const result = await response.json();
        console.log('🔐 Success response:', result);
      }
      
      // Switch to the saved mode and update local state
      console.log('🔐 Switching mode to:', localSettings.authMode);
      const switchResponse = await fetch('http://127.0.0.1:5000/api/v1/credentials/switch-mode', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ auth_mode: localSettings.authMode })
      });
      
      console.log('🔐 Switch response status:', switchResponse.status);
      
      if (switchResponse.ok) {
        // Reload settings after successful save and mode switch
        console.log('🔐 Reloading settings...');
        const settings = await loadSavedSettings();
        if (settings) {
          setLocalSettings(settings);
          console.log('🔐 Settings reloaded:', settings);
        }
      }
      
      // Reset saved status after 3 seconds
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
      
      const response = await fetch('http://127.0.0.1:5000/api/v1/credentials/switch-mode', {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ auth_mode: newMode })
      });
      
      if (response.ok) {
        // Use cached credentials for instant switching
        const cachedCreds = localSettings._cachedCredentials?.[newMode];
        
        if (cachedCreds) {
          // Use cached credentials for instant UI update
          setLocalSettings(prev => ({
            ...prev,
            authMode: newMode,
            clientId: cachedCreds.client_id || '',
            accessToken: cachedCreds.access_token || '',
            apiKey: cachedCreds.api_key || '',
            clientSecret: cachedCreds.client_secret || '',
            lastAuthTime: cachedCreds.last_used_at || cachedCreds.created_at || null
          }));
        } else {
          // If no cached credentials, just update the auth mode
          setLocalSettings(prev => ({ ...prev, authMode: newMode }));
        }
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
