import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { TrendingUp, TrendingDown, RefreshCw, Filter } from 'lucide-react';

const PositionsMIS = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const [sortBy, setSortBy] = useState('UserId(asc)');
  const [filterUser, setFilterUser] = useState('');
  const [lastUpdate, setLastUpdate] = useState(new Date());

  useEffect(() => {
    loadPositions();
    // Set up auto-refresh for live data
    const interval = setInterval(() => {
      loadPositions();
    }, 5000); // Refresh every 5 seconds for live data

    return () => clearInterval(interval);
  }, []);

  const loadPositions = async () => {
    setLoading(true);
    try {
      const [positionsResponse, usersResponse] = await Promise.all([
        apiService.get('/portfolio/positions'),
        apiService.get('/admin/users')
      ]);

      const users = usersResponse?.data || [];
      const userMap = new Map(users.map((u) => [u.id, u.username || `User ${u.id}`]));
      const data = (positionsResponse?.data || []).filter((pos) => pos.product_type === 'MIS');
      const mapped = data.map((pos) => {
        const ltp = pos.quantity ? pos.avg_price + (pos.mtm / pos.quantity) : pos.avg_price;
        const pnl = (pos.mtm || 0) + (pos.realizedPnl || 0);
        const notional = Math.abs((pos.avg_price || 0) * (pos.quantity || 0));
        const pnlPercentage = notional ? (pnl / notional) * 100 : 0;
        const dayChange = ltp - (pos.avg_price || 0);
        const dayChangePercentage = pos.avg_price ? (dayChange / pos.avg_price) * 100 : 0;
        return {
          id: pos.id,
          userId: String(pos.user_id),
          userName: userMap.get(pos.user_id) || `User ${pos.user_id}`,
          symbol: pos.symbol,
          exchange: pos.exchange_segment,
          product: pos.product_type,
          quantity: pos.quantity,
          avgPrice: pos.avg_price,
          ltp: ltp,
          pnl: pnl,
          pnlPercentage: pnlPercentage,
          tradeTime: pos.updated_at ? new Date(pos.updated_at).toLocaleTimeString('en-IN') : '',
          orderType: pos.quantity >= 0 ? 'BUY' : 'SELL',
          status: pos.status,
          dayChange: dayChange,
          dayChangePercentage: dayChangePercentage
        };
      });

      setPositions(mapped);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error loading MIS positions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSort = (sortOption) => {
    setSortBy(sortOption);
    // Apply sorting logic here
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPercentage = (value) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
  };

  const filteredPositions = positions.filter(position => 
    filterUser === '' || 
    position.userName.toLowerCase().includes(filterUser.toLowerCase()) ||
    position.userId.includes(filterUser)
  );

  if (loading && positions.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header - Matching straddly.com */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">All Positions</h1>
              <span className="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                MIS
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <span>Last Update:</span>
                <span className="font-medium text-gray-900">
                  {lastUpdate.toLocaleTimeString()}
                </span>
                <button
                  onClick={loadPositions}
                  className="p-1 text-blue-600 hover:text-blue-800"
                  title="Refresh"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <Filter className="w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Filter by user..."
                  value={filterUser}
                  onChange={(e) => setFilterUser(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-1 text-sm"
                />
              </div>
              <select 
                value={sortBy}
                onChange={(e) => handleSort(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-1 text-sm"
              >
                <option>Sort By</option>
                <option>UserId(asc)</option>
                <option>UserId(desc)</option>
                <option>P&L(asc)</option>
                <option>P&L(desc)</option>
                <option>Quantity(asc)</option>
                <option>Quantity(desc)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Live indicator */}
      <div className="bg-green-50 border-b border-green-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-green-800 font-medium">Live MIS Trading Data</span>
            <span className="text-sm text-green-600">
              ({filteredPositions.length} active positions)
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-6 border-b border-gray-200">
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-blue-600 font-medium">Total Positions</div>
              <div className="text-2xl font-bold text-blue-900">{filteredPositions.length}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-green-600 font-medium">Total P&L</div>
              <div className={`text-2xl font-bold ${
                filteredPositions.reduce((sum, p) => sum + p.pnl, 0) >= 0 ? 'text-green-900' : 'text-red-900'
              }`}>
                {formatCurrency(filteredPositions.reduce((sum, p) => sum + p.pnl, 0))}
              </div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4">
              <div className="text-sm text-purple-600 font-medium">Active Users</div>
              <div className="text-2xl font-bold text-purple-900">
                {new Set(filteredPositions.map(p => p.userId)).size}
              </div>
            </div>
            <div className="bg-orange-50 rounded-lg p-4">
              <div className="text-sm text-orange-600 font-medium">Total Volume</div>
              <div className="text-2xl font-bold text-orange-900">
                {filteredPositions.reduce((sum, p) => sum + (p.quantity * p.ltp), 0).toLocaleString('en-IN')}
              </div>
            </div>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Symbol
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Exchange
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Quantity
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Price
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    LTP
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Day Change
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    P&L %
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Trade Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredPositions.map((position) => (
                  <tr key={position.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{position.userName}</div>
                        <div className="text-xs text-gray-500">{position.userId}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{position.symbol}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.exchange}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        position.orderType === 'BUY' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-red-100 text-red-800'
                      }`}>
                        {position.orderType}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.quantity}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(position.avgPrice)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatCurrency(position.ltp)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-1">
                        {position.dayChange >= 0 ? (
                          <TrendingUp className="w-4 h-4 text-green-500" />
                        ) : (
                          <TrendingDown className="w-4 h-4 text-red-500" />
                        )}
                        <span className={`font-medium ${
                          position.dayChange >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {formatCurrency(position.dayChange)}
                        </span>
                        <span className={`text-xs ${
                          position.dayChangePercentage >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          ({formatPercentage(position.dayChangePercentage)})
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className={`font-medium ${
                        position.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatCurrency(position.pnl)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <div className={`font-medium ${
                        position.pnlPercentage >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {formatPercentage(position.pnlPercentage)}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.tradeTime}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        position.status === 'OPEN' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {position.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PositionsMIS;