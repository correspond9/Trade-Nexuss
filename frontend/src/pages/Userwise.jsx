import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { Search, Filter, Download, TrendingUp, TrendingDown, DollarSign, BarChart3, PieChart, Activity, Calendar, User, Target, Award } from 'lucide-react';

const Userwise = () => {
  const { user } = useAuth();
  const { users } = useAppContext();
  const [selectedUser, setSelectedUser] = useState(null);
  const [userStats, setUserStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState('7d');
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (selectedUser) {
      fetchUserStats();
    }
  }, [selectedUser, dateRange]);

  const fetchUserStats = async () => {
    setLoading(true);
    try {
      const [ordersResponse, positionsResponse] = await Promise.all([
        apiService.get('/trading/orders', { user_id: selectedUser.id }),
        apiService.get('/portfolio/positions', { user_id: selectedUser.id })
      ]);

      const orders = ordersResponse?.data || [];
      const positions = positionsResponse?.data || [];

      const totalTrades = orders.length;
      const pnlByPosition = positions.map((pos) => Number(pos.mtm || 0) + Number(pos.realizedPnl || 0));
      const winningTrades = pnlByPosition.filter((p) => p > 0).length;
      const losingTrades = pnlByPosition.filter((p) => p < 0).length;
      const winRate = winningTrades + losingTrades > 0 ? (winningTrades / (winningTrades + losingTrades)) * 100 : 0;
      const totalPnL = pnlByPosition.reduce((sum, p) => sum + p, 0);
      const totalVolume = orders.reduce((sum, o) => sum + (Number(o.quantity || 0) * Number(o.price || 0)), 0);
      const averageTradeSize = totalTrades ? totalVolume / totalTrades : 0;

      const instrumentsMap = new Map();
      orders.forEach((o) => {
        const symbol = o.symbol || 'UNKNOWN';
        const entry = instrumentsMap.get(symbol) || { trades: 0, pnl: 0, volume: 0 };
        entry.trades += 1;
        entry.volume += Number(o.quantity || 0) * Number(o.price || 0);
        instrumentsMap.set(symbol, entry);
      });

      const instruments = Array.from(instrumentsMap.entries()).map(([symbol, info]) => ({
        symbol,
        trades: info.trades,
        pnl: info.pnl,
        winRate: 0,
        volume: info.volume
      }));

      const recentTrades = orders.slice(0, 10).map((o) => ({
        id: o.id,
        symbol: o.symbol || 'UNKNOWN',
        type: o.transaction_type || 'BUY',
        quantity: Number(o.quantity || 0),
        price: Number(o.price || 0),
        pnl: 0,
        time: o.created_at ? new Date(o.created_at).toLocaleTimeString('en-IN') : '',
        status: 'N/A'
      }));

      setUserStats({
        overview: {
          totalTrades,
          winningTrades,
          losingTrades,
          winRate,
          totalPnL,
          totalVolume,
          averageTradeSize,
          sharpeRatio: 0,
          maxDrawdown: 0
        },
        performance: {
          daily: [],
          weekly: [],
          monthly: []
        },
        instruments,
        recentTrades
      });
    } catch (error) {
      console.error('Failed to fetch user stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = (users || []).filter(user =>
    user.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.username?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const exportReport = () => {
    // Export functionality
    console.log('Exporting userwise report...');
  };

  const StatCard = ({ title, value, icon: Icon, trend, color = 'blue' }) => (
    <div className={`bg-white rounded-lg shadow p-6 border-l-4 border-${color}-500`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-2xl font-bold text-${color}-600`}>{value}</p>
          {trend && (
            <div className={`flex items-center mt-1 text-sm ${
              trend > 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {trend > 0 ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
              {Math.abs(trend)}%
            </div>
          )}
        </div>
        <Icon className={`w-8 h-8 text-${color}-400`} />
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Userwise Reports</h1>
            <p className="mt-2 text-gray-600">Detailed user performance and activity analytics</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={exportReport}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export Report
            </button>
          </div>
        </div>
      </div>

      {!selectedUser ? (
        /* User Selection */
        <div className="bg-white rounded-lg shadow p-6">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Select User</h2>
            <div className="flex items-center space-x-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                <input
                  type="text"
                  placeholder="Search users..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="90d">Last 90 Days</option>
                <option value="1y">Last Year</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredUsers.map((user) => (
              <div
                key={user.id}
                onClick={() => setSelectedUser(user)}
                className="border border-gray-200 rounded-lg p-4 hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer transition-colors"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
                      <User className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                      <h3 className="font-medium text-gray-900">{user.full_name || user.username}</h3>
                      <p className="text-sm text-gray-500">{user.email}</p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                    user.role === 'SUPER_ADMIN' ? 'bg-red-100 text-red-800' :
                    user.role === 'ADMIN' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {user.role?.replace('_', ' ') || 'USER'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Status:</span>
                    <span className={`ml-2 px-2 py-1 rounded-full text-xs ${
                      user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500">Member Since:</span>
                    <span className="ml-2 text-gray-900">
                      {new Date(user.created_at || '2024-01-01').toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        /* User Stats Display */
        <div className="space-y-6">
          {/* User Header */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <button
                  onClick={() => setSelectedUser(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ← Back to Users
                </button>
                <div className="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center">
                  <User className="w-6 h-6 text-indigo-600" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{selectedUser.full_name || selectedUser.username}</h2>
                  <p className="text-gray-500">{selectedUser.email} • {selectedUser.role?.replace('_', ' ')}</p>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value)}
                  className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="90d">Last 90 Days</option>
                  <option value="1y">Last Year</option>
                </select>
                <button
                  onClick={exportReport}
                  className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="w-4 h-4" />
                  Export
                </button>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="bg-white rounded-lg shadow p-12">
              <div className="flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              </div>
            </div>
          ) : userStats ? (
            <>
              {/* Tab Navigation */}
              <div className="bg-white rounded-lg shadow">
                <div className="border-b border-gray-200">
                  <nav className="flex space-x-8 px-6">
                    {['overview', 'performance', 'instruments', 'trades'].map((tab) => (
                      <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`py-4 px-1 border-b-2 font-medium text-sm capitalize ${
                          activeTab === tab
                            ? 'border-indigo-500 text-indigo-600'
                            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                        }`}
                      >
                        {tab}
                      </button>
                    ))}
                  </nav>
                </div>

                <div className="p-6">
                  {activeTab === 'overview' && (
                    <div className="space-y-6">
                      {/* Overview Stats */}
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                        <StatCard
                          title="Total P&L"
                          value={`₹${userStats.overview.totalPnL.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
                          icon={DollarSign}
                          trend={12.5}
                          color={userStats.overview.totalPnL >= 0 ? 'green' : 'red'}
                        />
                        <StatCard
                          title="Win Rate"
                          value={`${userStats.overview.winRate}%`}
                          icon={Target}
                          trend={5.2}
                          color="blue"
                        />
                        <StatCard
                          title="Total Trades"
                          value={userStats.overview.totalTrades.toLocaleString()}
                          icon={Activity}
                          trend={8.7}
                          color="purple"
                        />
                        <StatCard
                          title="Sharpe Ratio"
                          value={userStats.overview.sharpeRatio}
                          icon={BarChart3}
                          trend={2.1}
                          color="indigo"
                        />
                      </div>

                      {/* Performance Chart Placeholder */}
                      <div className="bg-gray-50 rounded-lg p-6">
                        <h3 className="text-lg font-medium text-gray-900 mb-4">Performance Chart</h3>
                        <div className="h-64 flex items-center justify-center text-gray-500">
                          <div className="text-center">
                            <BarChart3 className="w-12 h-12 mx-auto mb-2" />
                            <p>Chart visualization would go here</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {activeTab === 'performance' && (
                    <div className="space-y-6">
                      {/* Performance Table */}
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trades</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {userStats.performance.daily.map((day, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {new Date(day.date).toLocaleDateString()}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                                  day.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  ₹{day.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {day.trades}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {day.winRate}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {activeTab === 'instruments' && (
                    <div className="space-y-6">
                      {/* Instruments Table */}
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Trades</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Win Rate</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Volume</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {userStats.instruments.map((instrument, index) => (
                              <tr key={index}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                  {instrument.symbol}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {instrument.trades}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                                  instrument.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  ₹{instrument.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {instrument.winRate}%
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  ₹{instrument.volume.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {activeTab === 'trades' && (
                    <div className="space-y-6">
                      {/* Recent Trades */}
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                          <thead className="bg-gray-50">
                            <tr>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Time</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Price</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                            </tr>
                          </thead>
                          <tbody className="bg-white divide-y divide-gray-200">
                            {userStats.recentTrades.map((trade) => (
                              <tr key={trade.id}>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {trade.time}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                                  {trade.symbol}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                                    trade.type === 'BUY' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                  }`}>
                                    {trade.type}
                                  </span>
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  {trade.quantity}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                                  ₹{trade.price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                                  trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                  ₹{trade.pnl.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                                </td>
                                <td className="px-6 py-4 whitespace-nowrap">
                                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                                    trade.status === 'PROFIT' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                  }`}>
                                    {trade.status}
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="bg-white rounded-lg shadow p-12">
              <div className="text-center text-gray-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-4" />
                <p>No data available for selected user</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Userwise;