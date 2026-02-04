// Unified SuperAdmin Component - Settings + Monitoring in One View
import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Settings, Eye, AlertCircle, TrendingUp } from 'lucide-react';
import { useAuthSettings } from '../hooks/useAuthSettings';
import SystemMonitoring from '../components/SystemMonitoring';

const SuperAdmin = () => {
  const { user } = useAuth();
  
  // Use custom hook for authentication settings
  const {
    localSettings,
    setLocalSettings,
    saved,
    setSaved,
    loading,
    setLoading,
    saveSettings,
    switchMode,
  } = useAuthSettings();

  // Error state for save operations
  const [saveError, setSaveError] = useState(null);

  // Handle save with error handling
  const handleSave = async () => {
    setSaveError(null);
    try {
      await saveSettings();
    } catch (error) {
      setSaveError(error.message);
      // Clear error after 5 seconds
      setTimeout(() => setSaveError(null), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Super Admin Dashboard</h1>
          <p className="text-gray-600 mt-1">DhanHQ WebSocket Configuration & System Monitoring</p>
          <div className="flex items-center space-x-2 mt-2">
            <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-sm text-gray-600">System Active</span>
          </div>
        </div>

        {/* Main Content - Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Left Column - Authentication Settings */}
          <div className="space-y-6">
            {/* Authentication Card */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <div className="flex items-center mb-6">
                  <Settings className="w-5 h-5 text-blue-600 mr-2" />
                  <h2 className="text-lg font-semibold text-gray-900">DhanHQ Authentication</h2>
                </div>

                {/* Save Status */}
                {saved && (
                  <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded-md flex items-center">
                    <div className="flex-1">
                      <span className="text-sm font-medium">
                        ✅ {localSettings.authMode === 'DAILY_TOKEN' ? 'Daily Token' : 'Static IP'} credentials saved successfully!
                      </span>
                      <div className="text-xs text-green-600 mt-1">
                        🎯 {localSettings.authMode === 'DAILY_TOKEN' ? 'Mode A (Daily Token)' : 'Mode B (Static IP)'} is now active
                      </div>
                    </div>
                  </div>
                )}

                {/* Error Status */}
                {saveError && (
                  <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-md flex items-center">
                    <div className="flex-1">
                      <span className="text-sm font-medium">
                        ❌ Failed to save credentials
                      </span>
                      <div className="text-xs text-red-600 mt-1">
                        {saveError}
                      </div>
                    </div>
                  </div>
                )}

                {/* Authentication Mode */}
                <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <div className="space-y-4">
                    <div>
                      <h3 className="text-sm font-semibold text-blue-900 mb-2">Authentication Mode</h3>
                      <p className="text-xs text-blue-600 mb-3">
                        Choose between Daily Token (24-hour validity) or Static IP authentication for DhanHQ WebSocket
                      </p>
                      
                      {/* Mode Selection */}
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                          <input
                            type="radio"
                            id="daily-token"
                            name="auth-mode"
                            value="DAILY_TOKEN"
                            checked={localSettings.authMode === 'DAILY_TOKEN'}
                            onChange={(e) => {
                              const newMode = e.target.value;
                              setLocalSettings((s) => ({ ...s, authMode: newMode }));
                              switchMode(newMode);
                            }}
                            className="mr-2"
                          />
                          <label htmlFor="daily-token" className="text-sm font-medium text-gray-700 cursor-pointer">
                            Daily Token (Mode A)
                          </label>
                        </div>
                        <div className="flex items-center">
                          <input
                            type="radio"
                            id="static-ip"
                            name="auth-mode"
                            value="STATIC_IP"
                            checked={localSettings.authMode === 'STATIC_IP'}
                            onChange={(e) => {
                              const newMode = e.target.value;
                              setLocalSettings((s) => ({ ...s, authMode: newMode }));
                              switchMode(newMode);
                            }}
                            className="mr-2"
                          />
                          <label htmlFor="static-ip" className="text-sm font-medium text-gray-700 cursor-pointer">
                            Static IP (Mode B)
                          </label>
                        </div>
                      </div>
                      
                      {/* Mode Indicator */}
                      <div className="text-xs text-gray-600">
                        Active: <span className="font-semibold text-green-600">
                          {localSettings.authMode === 'DAILY_TOKEN' ? 'Mode A (Daily Token)' : 'Mode B (Static IP)'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Daily Token Authentication */}
                {localSettings.authMode === 'DAILY_TOKEN' && (
                  <div className="border rounded-lg border-green-500 bg-green-50">
                    <div className="p-4">
                      <div className="flex items-center mb-4">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center mr-3 bg-green-100">
                          <span className="font-semibold text-sm text-green-600">A</span>
                        </div>
                        <div>
                          <h3 className="text-md font-semibold text-gray-800">Daily Token Authentication</h3>
                          <p className="text-sm text-gray-600">24-hour validity access token for DhanHQ WebSocket</p>
                        </div>
                      </div>
                      
                      <div className="space-y-3 text-sm">
                        <div>
                          <label className="block text-xs text-gray-600 font-semibold mb-1">
                            Client ID
                          </label>
                          <input
                            type="text"
                            value={localSettings.clientId || ''}
                            onChange={(e) =>
                              setLocalSettings((s) => ({
                                ...s,
                                clientId: e.target.value,
                              }))
                            }
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter DhanHQ Client ID"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Your DhanHQ account client ID (required for WebSocket connection)
                          </p>
                        </div>
                        
                        <div>
                          <label className="block text-xs text-gray-600 font-semibold mb-1">
                            Daily Access Token
                          </label>
                          <input
                            type="password"
                            value={localSettings.accessToken}
                            onChange={(e) =>
                              setLocalSettings((s) => ({
                                ...s,
                                accessToken: e.target.value,
                              }))
                            }
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter DhanHQ 24-hour access token"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Token will be sent as: {`{"type": "auth", "access-token": "<TOKEN>"}`}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Static IP Authentication */}
                {localSettings.authMode === 'STATIC_IP' && (
                  <div className="border rounded-lg border-blue-500 bg-blue-50">
                    <div className="p-4">
                      <div className="flex items-center mb-4">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center mr-3 bg-blue-100">
                          <span className="font-semibold text-sm text-blue-600">B</span>
                        </div>
                        <div>
                          <h3 className="text-md font-semibold text-gray-800">Static IP Authentication</h3>
                          <p className="text-sm text-gray-600">API Key and Secret for Static IP-based authentication</p>
                        </div>
                      </div>
                      
                      <div className="space-y-3 text-sm">
                        <div>
                          <label className="block text-xs text-gray-600 font-semibold mb-1">
                            API Key
                          </label>
                          <input
                            type="text"
                            value={localSettings.apiKey || ''}
                            onChange={(e) =>
                              setLocalSettings((s) => ({
                                ...s,
                                apiKey: e.target.value,
                              }))
                            }
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter DhanHQ API Key"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Your DhanHQ API key for Static IP authentication
                          </p>
                        </div>
                        
                        <div>
                          <label className="block text-xs text-gray-600 font-semibold mb-1">
                            Client Secret
                          </label>
                          <input
                            type="password"
                            value={localSettings.clientSecret || ''}
                            onChange={(e) =>
                              setLocalSettings((s) => ({
                                ...s,
                                clientSecret: e.target.value,
                              }))
                            }
                            className="w-full border rounded px-3 py-2"
                            placeholder="Enter DhanHQ Client Secret"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Your DhanHQ client secret for Static IP authentication
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Save Button */}
                <div className="flex justify-end">
                  <button
                    onClick={handleSave}
                    disabled={loading}
                    className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Saving...' : `Save ${localSettings.authMode === 'DAILY_TOKEN' ? 'Token' : 'Credentials'}`}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - System Monitoring */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <div className="flex items-center mb-6">
                  <Eye className="w-5 h-5 text-green-600 mr-2" />
                  <h2 className="text-lg font-semibold text-gray-900">System Monitoring</h2>
                </div>
                
                {/* System Monitoring Component */}
                <SystemMonitoring />
              </div>
            </div>
          </div>
        </div>

        {/* Security Note */}
        <div className="mt-8 bg-yellow-50 border border-yellow-200 text-xs text-yellow-800 rounded-xl p-4">
          <strong>Security note:</strong> Authentication credentials are handled securely through the backend API.
          All sensitive data is encrypted and stored using proper security practices.
        </div>
      </div>
    </div>
  );
};

export default SuperAdmin;
