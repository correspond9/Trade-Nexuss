// src/components/DhanAuthConfig.jsx

import React, { useState, useEffect } from 'react';
import { authService } from '../services/authService';
import { apiService } from '../services/apiService';

const DhanAuthConfig = () => {
  const [currentMode, setCurrentMode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [switching, setSwitching] = useState(false);
  const [showCredentialForm, setShowCredentialForm] = useState(false);
  const [credentialType, setCredentialType] = useState('static_ip');
  const [switchReason, setSwitchReason] = useState('');
  const [showSwitchForm, setShowSwitchForm] = useState(false);
  const [formData, setFormData] = useState({
    client_id: '',
    api_key: '',
    api_secret: '',
    authorization_token: '',
    expiry_time: ''
  });

  useEffect(() => {
    if (!authService.isAdmin()) {
      window.location.href = '/user-dashboard';
      return;
    }
    fetchCurrentMode();
    fetchCredentials();
  }, []);

  const fetchCurrentMode = async () => {
    try {
      setLoading(true);
      const result = await apiService.get('/credentials/active');
      if (result.success) {
        setCurrentMode({
          auth_mode: result.data?.auth_mode || 'DAILY_TOKEN',
          has_token: result.data?.has_token || false,
          client_id: result.data?.client_id || ''
        });
      } else {
        setError(result.message || 'Failed to load auth mode');
      }
    } catch (err) {
      setError('Failed to load Dhan API configuration');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCredentials = async () => {
    try {
      // Fetch active credentials from backend (unified endpoint)
      const result = await apiService.get('/credentials/active');
      if (result && result.success && result.data) {
        const data = result.data;
          
          // Update form based on auth mode
          if (data.auth_mode === 'STATIC_IP') {
            setFormData(prev => ({
              ...prev,
              client_id: data.client_id || '',
              api_key: data.api_key || '',
              api_secret: data.secret_api || '',
            }));
            setCredentialType('static_ip');
          } else {
            setFormData(prev => ({
              ...prev,
              client_id: data.client_id || '',
              authorization_token: data.access_token || data.daily_token || '',
            }));
            setCredentialType('daily_token');
          }
          
          console.log('[CREDS] Loaded credentials from database:', data.auth_mode);
        }
      } else {
        console.warn('[CREDS] No saved credentials found');
      }
    } catch (err) {
      console.error('[CREDS] Error fetching credentials:', err);
      setError('Failed to load credentials from database');
    }
  };

  const handleSwitchMode = async (targetMode) => {
    if (!switchReason.trim()) {
      setError('Reason for switch is required');
      return;
    }

    try {
      setSwitching(true);
      
      // Note: Backend v2 doesn't have dedicated switch endpoint
      // Switching is done by saving new credentials with different auth_mode
      // Attempt switch via saving credentials endpoint (backend v2 uses save for mode changes)
      try {
        const payload = { reason: switchReason, auth_mode: targetMode };
        const result = await apiService.post('/credentials/save', payload).catch((e) => { throw e; });
        if (result && (result.success || result.status === 'success')) {
          await fetchCurrentMode();
          setShowSwitchForm(false);
          setSwitchReason('');
          alert(`Successfully switched to ${targetMode} mode`);
        } else {
          setError((result && (result.message || result.error)) || 'Switch failed');
        }
      } catch (err) {
        setError(err.message || 'Switch failed');
      }
    } catch (err) {
      setError(err.message);
      console.error('Switch error:', err);
    } finally {
      setSwitching(false);
    }
  };

  const handleUpdateCredentials = async () => {
    try {
      const auth_mode = credentialType === 'static_ip' ? 'STATIC_IP' : 'DAILY_TOKEN';
      
      const payload = {
        client_id: formData.client_id,
        access_token: credentialType === 'static_ip' ? '' : formData.authorization_token,
        api_key: credentialType === 'static_ip' ? formData.api_key : '',
        secret_api: credentialType === 'static_ip' ? formData.api_secret : '',
        daily_token: credentialType === 'static_ip' ? '' : formData.authorization_token,
        auth_mode: auth_mode
      };

      const result = await apiService.post('/credentials/save', payload);
      if (result.success) {
        await fetchCurrentMode();
        await fetchCredentials(); // Refresh credentials display
        
        resetCredentialForm();
        alert(`Credentials saved successfully! Mode: ${auth_mode}`);
      } else {
        setError(result.message || 'Failed to save credentials');
      }
    } catch (err) {
      setError(err.message);
      console.error('[CREDS] Save error:', err);
    }
  };

  const resetCredentialForm = () => {
    // Don't clear the form data - keep the loaded credentials
    // Just hide the form and clear any error
    setShowCredentialForm(false);
    setError('');
  };

  const formatTimeRemaining = (expiryTime) => {
    if (!expiryTime) return 'N/A';
    const now = new Date();
    const expiry = new Date(expiryTime);
    const diff = expiry - now;
    
    if (diff <= 0) return 'Expired';
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return `${hours}h ${minutes}m`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Dhan API Configuration</h1>
              <p className="text-gray-600 mt-1">Manage authentication modes and API credentials</p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => window.history.back()}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Back
              </button>
              <button
                onClick={() => authService.logout()}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
            <button onClick={() => setError('')} className="ml-4 text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* Current Mode Status */}
        {currentMode && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Current Authentication Status</h2>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Current Mode</label>
                  <div className={`px-3 py-2 rounded-lg text-center font-semibold ${
                    currentMode.current_mode === 'STATIC_IP' 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-orange-100 text-orange-800'
                  }`}>
                    {currentMode.current_mode === 'STATIC_IP' ? '🔒 STATIC_IP' : '🔑 DAILY_TOKEN'}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Data Authority</label>
                  <div className={`px-3 py-2 rounded-lg text-center font-semibold ${
                    currentMode.data_authority === 'PRIMARY' 
                      ? 'bg-blue-100 text-blue-800' 
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {currentMode.data_authority}
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Last Switch</label>
                  <div className="px-3 py-2 bg-gray-100 rounded-lg text-center">
                    {currentMode.last_switched_at 
                      ? new Date(currentMode.last_switched_at).toLocaleString()
                      : 'Never'
                    }
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Token Expiry</label>
                  <div className="px-3 py-2 bg-gray-100 rounded-lg text-center">
                    {currentMode.auth_info?.expired ? '⚠️ Expired' : 
                     currentMode.current_mode === 'DAILY_TOKEN' && currentMode.auth_info?.expiry_time
                      ? formatTimeRemaining(currentMode.auth_info.expiry_time)
                      : 'N/A'
                    }
                  </div>
                </div>
              </div>

              {currentMode.switch_reason && (
                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Last Switch Reason:</span> {currentMode.switch_reason}
                  </p>
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">Switched by:</span> {currentMode.switched_by}
                  </p>
                </div>
              )}

              {currentMode.current_mode === 'DAILY_TOKEN' && (
                <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
                  <p className="text-sm text-orange-800 font-medium">
                    ⚠️ Emergency Data Mode (Daily Token Active)
                  </p>
                  <p className="text-sm text-orange-700 mt-1">
                    Some features may be restricted. Consider switching to Static IP mode for full functionality.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Mode Switch Controls */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Switch Authentication Mode</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <button
                onClick={() => {
                  setShowSwitchForm(true);
                  setSwitchReason('');
                }}
                disabled={currentMode?.current_mode === 'STATIC_IP'}
                className="px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                Switch to Static IP Mode
                <p className="text-xs mt-1">Production mode with API keys</p>
              </button>
              <button
                onClick={() => {
                  setShowSwitchForm(true);
                  setSwitchReason('');
                }}
                disabled={currentMode?.current_mode === 'DAILY_TOKEN'}
                className="px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                Switch to Daily Token Mode
                <p className="text-xs mt-1">Emergency/Development mode</p>
              </button>
            </div>

            {showSwitchForm && (
              <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                <h3 className="text-md font-semibold mb-2">Confirm Switch</h3>
                <p className="text-sm text-gray-600 mb-3">
                  Switching from {currentMode?.current_mode} to {
                    currentMode?.current_mode === 'STATIC_IP' ? 'DAILY_TOKEN' : 'STATIC_IP'
                  }
                </p>
                <textarea
                  value={switchReason}
                  onChange={(e) => setSwitchReason(e.target.value)}
                  placeholder="Enter reason for switching modes..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows="3"
                  required
                />
                <div className="mt-3 flex space-x-3">
                  <button
                    onClick={() => handleSwitchMode(currentMode?.current_mode === 'STATIC_IP' ? 'DAILY_TOKEN' : 'STATIC_IP')}
                    disabled={switching || !switchReason.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
                  >
                    {switching ? 'Switching...' : 'Confirm Switch'}
                  </button>
                  <button
                    onClick={() => {
                      setShowSwitchForm(false);
                      setSwitchReason('');
                    }}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Credential Management */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Credential Management</h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={() => {
                  setCredentialType('static_ip');
                  setShowCredentialForm(true);
                }}
                className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Update Static IP Credentials
                <p className="text-xs text-gray-600 mt-1">Client ID, API Key, Secret</p>
              </button>
              <button
                onClick={() => {
                  setCredentialType('daily_token');
                  setShowCredentialForm(true);
                }}
                className="px-4 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Update Daily Token Credentials
                <p className="text-xs text-gray-600 mt-1">Authorization Token, Expiry</p>
              </button>
            </div>

            {showCredentialForm && (
              <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                <h3 className="text-md font-semibold mb-4">
                  {credentialType === 'static_ip' ? 'Static IP Credentials' : 'Daily Token Credentials'}
                </h3>
                
                {credentialType === 'static_ip' ? (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Client ID</label>
                      <input
                        type="text"
                        value={formData.client_id}
                        onChange={(e) => setFormData({...formData, client_id: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter client ID"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
                      <input
                        type="password"
                        value={formData.api_key}
                        onChange={(e) => setFormData({...formData, api_key: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter API key"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">API Secret</label>
                      <input
                        type="password"
                        value={formData.api_secret}
                        onChange={(e) => setFormData({...formData, api_secret: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter API secret"
                      />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Authorization Token</label>
                      <input
                        type="password"
                        value={formData.authorization_token}
                        onChange={(e) => setFormData({...formData, authorization_token: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Enter authorization token"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Expiry Time</label>
                      <input
                        type="datetime-local"
                        value={formData.expiry_time}
                        onChange={(e) => setFormData({...formData, expiry_time: e.target.value})}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                )}

                <div className="mt-4 flex space-x-3">
                  <button
                    onClick={handleUpdateCredentials}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Update Credentials
                  </button>
                  <button
                    onClick={resetCredentialForm}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DhanAuthConfig;
