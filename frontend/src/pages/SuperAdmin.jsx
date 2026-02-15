// Unified SuperAdmin Component - Settings + Monitoring in One View
import React, { useCallback, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { Settings, Eye } from 'lucide-react';
import { useAuthSettings } from '../hooks/useAuthSettings';
import SystemMonitoring from '../components/SystemMonitoring';

const SuperAdmin = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('settings');
  const [marketConfig, setMarketConfig] = useState(null);
  const [mcError, setMcError] = useState(null);
  const API_BASE = apiService.baseURL;
  const ROOT_BASE = API_BASE.replace(/\/api\/v\d+\/?$/, '');
  
  // Use custom hook for authentication settings
  const {
    localSettings,
    setLocalSettings,
    saved,
    loading,
    saveSettings,
    switchMode,
  } = useAuthSettings();

  // Error state for save operations
  const [saveError, setSaveError] = useState(null);
  const [masterLoading, setMasterLoading] = useState(false);
  const [masterMsg, setMasterMsg] = useState('');
  const [uploadMsg, setUploadMsg] = useState('');
  const [exposureFile, setExposureFile] = useState(null);
  const [equitySpanFile, setEquitySpanFile] = useState(null);
  const [commoditySpanFile, setCommoditySpanFile] = useState(null);
  const [authCheckIdentifier, setAuthCheckIdentifier] = useState('');
  const [authCheckPassword, setAuthCheckPassword] = useState('');
  const [authCheckLoading, setAuthCheckLoading] = useState(false);
  const [authCheckResult, setAuthCheckResult] = useState(null);
  const [authCheckError, setAuthCheckError] = useState('');

  // Handle save with error handling
  const handleSave = async () => {
    setSaveError(null);
    try {
      await saveSettings();
      // One-click daily workflow: after token save, immediately load instrument master
      if (localSettings.authMode === 'DAILY_TOKEN') {
        await handleLoadInstrumentMaster();
      }
    } catch (error) {
      setSaveError(error.message);
      // Clear error after 5 seconds
      setTimeout(() => setSaveError(null), 5000);
    }
  };

  const handleLoadInstrumentMaster = async () => {
    setMasterLoading(true);
    setMasterMsg('');
    try {
      const res = await apiService.request(`${ROOT_BASE}/admin/load-instrument-master`, {
        method: 'POST',
        headers: { 'X-USER': user?.username || '' },
        body: {}
      });
      const count = res?.records ?? 0;
      setMasterMsg(`✅ Instrument master loaded (${count.toLocaleString()} records)`);
    } catch (error) {
      const detail = error?.message || 'Failed to load instrument master';
      setMasterMsg(`❌ ${detail}`);
    } finally {
      setMasterLoading(false);
      setTimeout(() => setMasterMsg(''), 6000);
    }
  };

  const handleUserAuthCheck = async () => {
    if (!authCheckIdentifier.trim()) {
      setAuthCheckError('Please enter mobile/user identifier');
      return;
    }

    setAuthCheckLoading(true);
    setAuthCheckError('');
    setAuthCheckResult(null);

    try {
      const payload = {
        identifier: authCheckIdentifier.trim(),
      };
      if (authCheckPassword.trim()) {
        payload.password = authCheckPassword;
      }

      const res = await apiService.request(`${ROOT_BASE}/admin/user-auth-check`, {
        method: 'POST',
        headers: { 'X-USER': user?.username || '' },
        body: payload,
      });

      setAuthCheckResult(res);
    } catch (error) {
      setAuthCheckError(error?.message || 'Auth check failed');
    } finally {
      setAuthCheckLoading(false);
    }
  };

  const fetchMarketConfig = useCallback(async () => {
    try {
      const data = await apiService.get('/admin/market-config');
      setMarketConfig(data?.data || null);
    } catch (e) {
      setMcError('Failed to load market config');
      setTimeout(() => setMcError(null), 5000);
    }
  }, []);

  const saveMarketConfig = async () => {
    try {
      const payload = { config: marketConfig };
      const data = await apiService.post('/admin/market-config', payload);
      setMarketConfig(data?.data || marketConfig);
    } catch (e) {
      setMcError('Failed to save market config');
      setTimeout(() => setMcError(null), 5000);
    }
  };

  const setForce = async (exchange, state) => {
    try {
      const data = await apiService.post('/admin/market-force', { exchange, state });
      setMarketConfig(data?.data || marketConfig);
    } catch (e) {
      setMcError('Failed to set force state');
      setTimeout(() => setMcError(null), 5000);
    }
  };

  React.useEffect(() => {
    fetchMarketConfig();
  }, [fetchMarketConfig]);

  const timeInput = (value, onChange) => (
    <input
      type="time"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="border rounded px-2 py-1 text-sm"
    />
  );

  const dayCheckboxes = (days, onChange) => {
    const labels = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
    return (
      <div className="flex flex-wrap gap-2">
        {labels.map((lbl, idx) => {
          const checked = Array.isArray(days) ? days.includes(idx) : false;
          return (
            <label key={idx} className="flex items-center space-x-1 text-xs">
              <input
                type="checkbox"
                checked={checked}
                onChange={(e) => {
                  const set = new Set(days || []);
                  if (e.target.checked) set.add(idx);
                  else set.delete(idx);
                  onChange(Array.from(set).sort());
                }}
              />
              <span>{lbl}</span>
            </label>
          );
        })}
      </div>
    );
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

        <div className="mb-6 flex flex-wrap gap-2">
          <button
            onClick={() => setActiveTab('settings')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'settings'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            Settings & Monitoring
          </button>
          <button
            onClick={() => setActiveTab('user-auth-check')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === 'user-auth-check'
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50'
            }`}
          >
            User Auth Check
          </button>
        </div>

        {activeTab === 'settings' && (
          <>
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
                      
                      {/* Mode Selection - Toggle */}
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center">
                          <label htmlFor="auth-toggle" className="flex items-center cursor-pointer">
                            <div className="relative">
                              <input
                                id="auth-toggle"
                                type="checkbox"
                                className="sr-only"
                                checked={localSettings.authMode === 'DAILY_TOKEN'}
                                onChange={async (e) => {
                                  const newMode = e.target.checked ? 'DAILY_TOKEN' : 'STATIC_IP';
                                  // Optimistic UI update
                                  const prev = localSettings.authMode;
                                  setLocalSettings((s) => ({ ...s, authMode: newMode }));
                                  try {
                                    await switchMode(newMode);
                                  } catch (err) {
                                    // Revert UI on error
                                    setLocalSettings((s) => ({ ...s, authMode: prev }));
                                  }
                                }}
                              />
                              <div className="w-11 h-6 bg-gray-200 rounded-full shadow-inner"></div>
                              <div className={`dot absolute left-0 top-0 w-6 h-6 bg-white rounded-full shadow transform transition ${localSettings.authMode === 'DAILY_TOKEN' ? 'translate-x-5' : 'translate-x-0'}`} />
                            </div>
                            <span className="ml-3 text-sm font-medium text-gray-700">{localSettings.authMode === 'DAILY_TOKEN' ? 'Daily Token (Mode A)' : 'Static IP (Mode B)'}</span>
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
                            type="text"
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
                            Required for WebSocket connection and backend storage
                          </p>
                        </div>

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
                            type="text"
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
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs text-gray-600">
                    Load instrument master manually after token/credentials save.
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleLoadInstrumentMaster}
                      disabled={masterLoading}
                      className="bg-gray-800 text-white px-4 py-2 rounded-md hover:bg-gray-900 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                      {masterLoading ? 'Loading Master...' : 'Load Instrument Master'}
                    </button>
                  <button
                    onClick={handleSave}
                    disabled={loading}
                    className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Saving...' : `Save ${localSettings.authMode === 'DAILY_TOKEN' ? 'Token' : 'Credentials'}`}
                  </button>
                  </div>
                </div>
                {masterMsg && (
                  <div className="mt-3 text-sm text-gray-700">{masterMsg}</div>
                )}
              </div>
            </div>

            {/* Market Hours & Days Configuration */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6">
                <div className="flex items-center mb-6">
                  <Settings className="w-5 h-5 text-blue-600 mr-2" />
                  <h2 className="text-lg font-semibold text-gray-900">Market Hours & Days</h2>
                </div>
                {mcError && (
                  <div className="mb-3 p-2 bg-red-100 border border-red-200 text-red-700 rounded text-xs">
                    {mcError}
                  </div>
                )}
                {!marketConfig ? (
                  <div className="text-sm text-gray-600">Loading config...</div>
                ) : (
                  <div className="space-y-4">
                    {['NSE','BSE','MCX'].map((ex) => {
                      const cfg = marketConfig[ex];
                      return (
                        <div key={ex} className="border rounded p-4">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-semibold text-gray-900">{ex}</h3>
                            <div className="text-xs text-gray-600">Force: {cfg.force_state || 'none'}</div>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Open Time</div>
                              {timeInput(cfg.open_time, (val) => {
                                setMarketConfig((c) => ({...c, [ex]: {...c[ex], open_time: val}}));
                              })}
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Close Time</div>
                              {timeInput(cfg.close_time, (val) => {
                                setMarketConfig((c) => ({...c, [ex]: {...c[ex], close_time: val}}));
                              })}
                            </div>
                            <div>
                              <div className="text-xs text-gray-600 mb-1">Working Days</div>
                              {dayCheckboxes(cfg.working_days, (days) => {
                                setMarketConfig((c) => ({...c, [ex]: {...c[ex], working_days: days}}));
                              })}
                            </div>
                          </div>
                          <div className="flex items-center gap-2 mt-3">
                            <button
                              onClick={() => setForce(ex, 'open')}
                              className="px-3 py-1.5 text-xs rounded bg-green-600 text-white hover:bg-green-700"
                            >
                              Force Open
                            </button>
                            <button
                              onClick={() => setForce(ex, 'close')}
                              className="px-3 py-1.5 text-xs rounded bg-red-600 text-white hover:bg-red-700"
                            >
                              Force Close
                            </button>
                            <button
                              onClick={() => setForce(ex, 'none')}
                              className="px-3 py-1.5 text-xs rounded bg-gray-600 text-white hover:bg-gray-700"
                            >
                              Clear Override
                            </button>
                          </div>
                        </div>
                      );
                    })}
                    <div className="flex justify-end">
                      <button
                        onClick={saveMarketConfig}
                        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 text-sm"
                      >
                        Save Market Config
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* NSE File Uploads */}
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 space-y-4">
                <div className="flex items-center mb-2">
                  <Settings className="w-5 h-5 text-blue-600 mr-2" />
                  <h2 className="text-lg font-semibold text-gray-900">NSE Files Upload</h2>
                </div>
                {uploadMsg && (
                  <div className="p-2 bg-green-50 border border-green-200 text-green-700 text-xs rounded">
                    {uploadMsg}
                  </div>
                )}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded p-4 space-y-2">
                    <div className="text-sm font-semibold">Equity Exposure CSV</div>
                    <input type="file" accept=".csv,text/csv" onChange={(e) => setExposureFile(e.target.files?.[0] || null)} />
                    <button
                      className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                      onClick={async () => {
                        if (!exposureFile) return;
                        const fd = new FormData();
                        fd.append('file', exposureFile);
                        try {
                          await apiService.request(`${ROOT_BASE}/admin/upload/equity-exposure`, {
                            method: 'POST',
                            headers: { 'X-USER': user?.username || '' },
                            body: fd
                          });
                          setUploadMsg('Equity exposure uploaded');
                        } catch (err) {
                          const msg = (err && err.message) || 'Upload failed';
                          setUploadMsg(`Upload failed: ${msg}`);
                        }
                        setTimeout(() => setUploadMsg(''), 3000);
                      }}
                    >
                      Upload Exposure
                    </button>
                  </div>
                  <div className="border rounded p-4 space-y-2">
                    <div className="text-sm font-semibold">Equity SPAN Zip</div>
                    <input type="file" accept=".zip,application/zip" onChange={(e) => setEquitySpanFile(e.target.files?.[0] || null)} />
                    <button
                      className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                      onClick={async () => {
                        if (!equitySpanFile) return;
                        const fd = new FormData();
                        fd.append('file', equitySpanFile);
                        try {
                          await apiService.request(`${ROOT_BASE}/admin/upload/equity-span`, {
                            method: 'POST',
                            headers: { 'X-USER': user?.username || '' },
                            body: fd
                          });
                          setUploadMsg('Equity SPAN uploaded');
                        } catch (err) {
                          const msg = (err && err.message) || 'Upload failed';
                          setUploadMsg(`Upload failed: ${msg}`);
                        }
                        setTimeout(() => setUploadMsg(''), 3000);
                      }}
                    >
                      Upload Equity SPAN
                    </button>
                  </div>
                  <div className="border rounded p-4 space-y-2">
                    <div className="text-sm font-semibold">Commodity SPAN Zip</div>
                    <input type="file" accept=".zip,application/zip" onChange={(e) => setCommoditySpanFile(e.target.files?.[0] || null)} />
                    <button
                      className="px-3 py-2 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                      onClick={async () => {
                        if (!commoditySpanFile) return;
                        const fd = new FormData();
                        fd.append('file', commoditySpanFile);
                        try {
                          await apiService.request(`${ROOT_BASE}/admin/upload/commodity-span`, {
                            method: 'POST',
                            headers: { 'X-USER': user?.username || '' },
                            body: fd
                          });
                          setUploadMsg('Commodity SPAN uploaded');
                        } catch (err) {
                          const msg = (err && err.message) || 'Upload failed';
                          setUploadMsg(`Upload failed: ${msg}`);
                        }
                        setTimeout(() => setUploadMsg(''), 3000);
                      }}
                    >
                      Upload Commodity SPAN
                    </button>
                  </div>
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

        {/* Admin Note */}
        <div className="mt-8 bg-blue-50 border border-blue-200 text-xs text-blue-800 rounded-xl p-4">
          <strong>Admin note:</strong> Authentication credentials are now visible for easier management and validation.
          This is an admin-only panel. Ensure proper access control to this dashboard.
        </div>
          </>
        )}

        {activeTab === 'user-auth-check' && (
          <div className="max-w-4xl">
            <div className="bg-white rounded-lg shadow">
              <div className="p-6 space-y-4">
                <h2 className="text-lg font-semibold text-gray-900">User Auth Check</h2>
                <p className="text-sm text-gray-600">
                  Diagnose user login issues safely (existence, status, role, password match). No password/hash is exposed.
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-gray-600 font-semibold mb-1">Mobile / User ID / Username / Email</label>
                    <input
                      type="text"
                      value={authCheckIdentifier}
                      onChange={(e) => setAuthCheckIdentifier(e.target.value)}
                      className="w-full border rounded px-3 py-2"
                      placeholder="e.g. 9967595222"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-600 font-semibold mb-1">Password (optional verify)</label>
                    <input
                      type="password"
                      value={authCheckPassword}
                      onChange={(e) => setAuthCheckPassword(e.target.value)}
                      className="w-full border rounded px-3 py-2"
                      placeholder="Optional: verify password match"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleUserAuthCheck}
                    disabled={authCheckLoading}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    {authCheckLoading ? 'Checking...' : 'Check User Auth'}
                  </button>
                </div>

                {authCheckError && (
                  <div className="p-3 bg-red-100 border border-red-300 text-red-700 rounded text-sm">{authCheckError}</div>
                )}

                {authCheckResult && (
                  <div className="p-4 border rounded bg-gray-50 text-sm space-y-2">
                    <div><strong>Message:</strong> {authCheckResult?.message || '-'}</div>
                    <div><strong>User Exists:</strong> {String(!!authCheckResult?.exists)}</div>
                    {authCheckResult?.data && (
                      <>
                        <div><strong>Status:</strong> {authCheckResult.data.status || '-'}</div>
                        <div><strong>Role:</strong> {authCheckResult.data.role || '-'}</div>
                        <div><strong>Username:</strong> {authCheckResult.data.username || '-'}</div>
                        <div><strong>Mobile:</strong> {authCheckResult.data.mobile || '-'}</div>
                        <div><strong>Has Password:</strong> {String(!!authCheckResult.data.has_password)}</div>
                        {authCheckResult.data.password_match !== null && authCheckResult.data.password_match !== undefined && (
                          <div><strong>Password Match:</strong> {String(!!authCheckResult.data.password_match)}</div>
                        )}
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SuperAdmin;
