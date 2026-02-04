// Simplified Authentication Settings Component - Daily Token Only
import React from 'react';

const AuthSettings = ({ localSettings, setLocalSettings, saveSettings, saved }) => {
  return (
    <div className="space-y-6">
      {/* Save Status */}
      {saved && (
        <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded-md flex items-center">
          <span className="text-sm font-medium">Settings saved successfully!</span>
        </div>
      )}

      {/* Authentication Mode - Daily Token Only */}
      <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-semibold text-blue-900 mb-2">Authentication Mode</h3>
            <p className="text-xs text-blue-600 mb-3">
              Daily Token authentication for DhanHQ WebSocket connection (24-hour validity)
            </p>
            
            {/* Mode Indicator */}
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <span className="text-sm font-medium mr-3 text-green-600">Daily Token Mode</span>
                <div className="w-6 h-6 bg-green-600 rounded-full flex items-center justify-center">
                  <span className="text-white text-xs font-bold">✓</span>
                </div>
              </div>
              <div className="text-xs text-gray-600">
                Active: <span className="font-semibold text-green-600">Mode A (Daily Token)</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Daily Token Authentication */}
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

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={saveSettings}
          className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors"
        >
          Save Token
        </button>
      </div>
    </div>
  );
};

export default AuthSettings;
