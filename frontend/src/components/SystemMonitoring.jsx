// System Monitoring Component - Fixed to match backend response structure
import React, { useState, useEffect } from 'react';
import { Eye, TrendingUp, AlertCircle } from 'lucide-react';
import LiveQuotes from './LiveQuotes';
import { apiService } from '../services/apiService';

const API_BASE = apiService.baseURL;
const ROOT_BASE = API_BASE.replace(/\/api\/v\d+\/?$/, '');

const SystemMonitoring = () => {
  const [systemData, setSystemData] = useState({});
  const [lastUpdate, setLastUpdate] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [actionMessage, setActionMessage] = useState(null);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const [healthData, streamData] = await Promise.all([
          apiService.request(`${ROOT_BASE}/health`, { method: 'GET' }).catch(() => ({})),
          apiService.get('/market/stream-status').catch(() => ({}))
        ]);
        const data = healthData;

        const wsStatus = streamData?.equity_ws || data?.websocket_status || {};
        const mcxWsStatus = streamData?.mcx_ws || data?.mcx_websocket_status || {};
        const wsConnected = (wsStatus.connected_connections ?? 0) > 0;
        const mcxWsConnected = (mcxWsStatus.connected_connections ?? 0) > 0;
        const liveFeed = streamData?.live_feed || {};

        const normalized = {
          services: {
            database: { status: 'unknown', response_time: 'N/A' },
            authentication: { status: data?.status || 'unknown', response_time: 'OK' },
            dhan_api: { status: 'unknown', message: 'Not checked' },
            websocket: {
              status: wsConnected ? 'healthy' : 'offline',
              message: wsConnected ? 'Connections active' : (liveFeed.cooldown_active ? 'Cooldown active' : 'No active connections'),
              connections: wsStatus.connected_connections || 0
            },
            mcx_websocket: {
              status: mcxWsConnected ? 'healthy' : 'offline',
              message: mcxWsConnected ? 'Connections active' : (mcxWsStatus.cooldown_active ? 'Cooldown active' : 'No active connections'),
              connections: mcxWsStatus.connected_connections || 0
            },
          },
          system_metrics: {}
        };

        setSystemData(normalized);
        setLastUpdate(new Date());
      } catch (error) {
        console.error('❌ Error fetching system status:', error);
      }
    };

    fetchSystemStatus();
    const interval = setInterval(fetchSystemStatus, 1000); // Poll every second for live feedback
    
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let interval = null;
    const fetchNotifications = async () => {
      try {
        try {
          const data = await apiService.get('/admin/notifications', { limit: 10 });
          setNotifications(data?.notifications || []);
        } catch (err) {
          console.error('Error fetching admin notifications via apiService:', err);
        }
      } catch (error) {
        console.error('❌ Error fetching admin notifications:', error);
      }
    };

    fetchNotifications();
    interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleReconnect = async () => {
    setActionMessage(null);
    setActionError(null);
    const confirmed = window.confirm(
      'This will explicitly clear cooldowns and trigger one reconnect attempt.\n\nAre you sure you want to proceed?\n\nSelect YES to continue or NO to cancel.'
    );
    if (!confirmed) {
      return;
    }
    try {
      const data = await apiService.post('/market/stream-reconnect');
      if (!data || !data.success) {
        throw new Error((data && data.message) || 'Failed to trigger reconnect');
      }
      setActionMessage('Reconnect triggered: cooldowns cleared and one attempt initiated');
      setTimeout(() => setActionMessage(null), 5000);
    } catch (err) {
      setActionError(err.message || 'Error triggering reconnect');
      setTimeout(() => setActionError(null), 7000);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
      case 'running':
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'error':
      case 'offline':
      case 'disconnected':
        return 'bg-red-100 text-red-800';
      case 'warning':
      case 'checking':
        return 'bg-yellow-100 text-yellow-800';
      case 'disabled':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'healthy': return 'Healthy';
      case 'running': return 'Running';
      case 'active': return 'Active';
      case 'error': return 'Error';
      case 'offline': return 'Offline';
      case 'disconnected': return 'Disconnected';
      case 'warning': return 'Warning';
      case 'checking': return 'Checking...';
      case 'disabled': return 'Disabled';
      default: return 'Unknown';
    }
  };

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'Never';
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
    
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
  };

  const services = systemData.services || {};
  const metrics = systemData.system_metrics || {};

  return (
    <div className="space-y-6">
      {/* Live Quotes - Data Flow Indicators */}
      <LiveQuotes />
      
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">System Monitoring</h2>
        <div className="flex items-center space-x-3">
          <div className="text-sm text-gray-500">
            Last updated: {lastUpdate ? formatTimeAgo(lastUpdate) : 'Never'}
          </div>
          <button
            onClick={handleReconnect}
            className="px-3 py-1.5 text-sm font-medium rounded-md bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-400"
            title="Clear cooldowns and trigger single reconnect attempt"
          >
            Clear Cooldown & Reconnect
          </button>
        </div>
      </div>

      {actionMessage && (
        <div className="p-3 bg-green-100 border border-green-300 text-green-800 rounded-md text-sm">
          {actionMessage}
        </div>
      )}
      {actionError && (
        <div className="p-3 bg-red-100 border border-red-300 text-red-800 rounded-md text-sm">
          {actionError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Database Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-900">Database</h3>
            <Eye className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(services.database?.status || 'checking')}`}>
            {getStatusText(services.database?.status || 'checking')}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.database?.response_time || 'Checking connection...'}
          </p>
        </div>

        {/* API Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-900">API Server</h3>
            <TrendingUp className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(services.authentication?.status || 'checking')}`}>
            {getStatusText(services.authentication?.status || 'checking')}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.authentication?.response_time || 'Checking endpoints...'}
          </p>
        </div>

        {/* Dhan API Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-900">Dhan API</h3>
            <AlertCircle className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(services.dhan_api?.status || 'checking')}`}>
            {getStatusText(services.dhan_api?.status || 'checking')}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.dhan_api?.error || services.dhan_api?.message || 'Checking Dhan servers...'}
          </p>
        </div>

        {/* Equity WebSocket Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-900">Equity WebSocket</h3>
            <AlertCircle className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(services.websocket?.status || 'checking')}`}>
            {getStatusText(services.websocket?.status || 'checking')}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.websocket?.message || 'Checking connection...'}
          </p>
        </div>

        {/* MCX WebSocket Status */}
        <div className="bg-white rounded-lg shadow p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-gray-900">MCX WebSocket</h3>
            <AlertCircle className="w-4 h-4 text-gray-400" />
          </div>
          <div className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(services.mcx_websocket?.status || 'checking')}`}>
            {getStatusText(services.mcx_websocket?.status || 'checking')}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {services.mcx_websocket?.message || 'Checking connection...'}
          </p>
        </div>
      </div>

      {/* System Metrics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-md font-semibold text-gray-800 mb-4">Performance Metrics</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-500">CPU Usage</p>
            <p className="text-lg font-semibold text-gray-900">
              {metrics.cpu_percent ? `${metrics.cpu_percent.toFixed(1)}%` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Memory Usage</p>
            <p className="text-lg font-semibold text-gray-900">
              {metrics.memory_percent ? `${metrics.memory_percent.toFixed(1)}%` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Disk Usage</p>
            <p className="text-lg font-semibold text-gray-900">
              {metrics.disk_percent ? `${metrics.disk_percent.toFixed(1)}%` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500">Uptime</p>
            <p className="text-lg font-semibold text-gray-900">
              {metrics.uptime || 'N/A'}
            </p>
          </div>
        </div>
        
        {/* Additional Details */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-gray-600">Memory Available</p>
            <p className="font-medium">{metrics.memory_available_gb ? `${metrics.memory_available_gb.toFixed(2)} GB` : 'N/A'}</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-gray-600">Disk Free</p>
            <p className="font-medium">{metrics.disk_free_gb ? `${metrics.disk_free_gb.toFixed(2)} GB` : 'N/A'}</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-gray-600">Equity WS Connections</p>
            <p className="font-medium">{services.websocket?.connections || 0}</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-gray-600">MCX WS Connections</p>
            <p className="font-medium">{services.mcx_websocket?.connections || 0}</p>
          </div>
          <div className="bg-gray-50 p-3 rounded">
            <p className="text-gray-600">Dhan API Status</p>
            <p className={`font-medium ${services.dhan_api?.status === 'healthy' ? 'text-green-600' : services.dhan_api?.status === 'error' ? 'text-red-600' : 'text-yellow-600'}`}>
              {services.dhan_api?.status === 'healthy' ? 'Connected' : services.dhan_api?.status === 'error' ? 'Disconnected' : 'Checking...'}
            </p>
          </div>
        </div>
      </div>

      {/* Admin Notifications */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-md font-semibold text-gray-800">Admin Alerts</h3>
          <div className="text-xs text-gray-500">
            {notifications.length} recent
          </div>
        </div>
        {notifications.length === 0 ? (
          <div className="text-sm text-gray-500">No alerts yet.</div>
        ) : (
          <div className="space-y-3">
            {notifications.map((item) => (
              <div key={item.id} className="border border-gray-200 rounded-md px-3 py-2">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-gray-800">
                    {item.message}
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                    item.level === 'ERROR'
                      ? 'bg-red-100 text-red-700'
                      : item.level === 'INFO'
                        ? 'bg-blue-100 text-blue-700'
                        : 'bg-yellow-100 text-yellow-700'
                  }`}>
                    {item.level || 'WARN'}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {item.created_at ? new Date(item.created_at).toLocaleString() : '—'}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemMonitoring;
