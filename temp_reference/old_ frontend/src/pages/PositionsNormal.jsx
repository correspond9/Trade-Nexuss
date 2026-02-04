import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { TrendingUp, TrendingDown, RefreshCw, Filter, Calendar } from 'lucide-react';

const PositionsNormal = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [positions, setPositions] = useState([]);
  const [sortBy, setSortBy] = useState('UserId(asc)');
  const [filterUser, setFilterUser] = useState('');
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

  useEffect(() => {
    loadPositions();
    // Set up auto-refresh for live data
    const interval = setInterval(() => {
      loadPositions();
    }, 10000); // Refresh every 10 seconds for carry forward positions

    return () => clearInterval(interval);
  }, [selectedDate]);

  const loadPositions = async () => {
    setLoading(true);
    try {
      // Mock Normal (carry forward) positions data
      const mockData = [
        {
          id: 1,
          userId: '7527',
          userName: 'Carry Forward Trader 1',
          symbol: 'RELIANCE-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 200,
          avgPrice: 2450.00,
          ltp: 2520.75,
          pnl: 14150.00,
          pnlPercentage: 2.89,
          tradeDate: '2024-01-15',
          carryForwardDays: 14,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 70.75,
          dayChangePercentage: 2.89,
          holdingPeriod: '14 days'
        },
        {
          id: 2,
          userId: '7528',
          userName: 'Long Term Investor',
          symbol: 'TCS-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 100,
          avgPrice: 2950.00,
          ltp: 3520.75,
          pnl: 57075.00,
          pnlPercentage: 19.35,
          tradeDate: '2023-12-01',
          carryForwardDays: 59,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 20.75,
          dayChangePercentage: 0.59,
          holdingPeriod: '59 days'
        },
        {
          id: 3,
          userId: '7529',
          userName: 'Position Holder',
          symbol: 'INFY-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 150,
          avgPrice: 1350.25,
          ltp: 1530.50,
          pnl: 27037.50,
          pnlPercentage: 13.33,
          tradeDate: '2024-01-10',
          carryForwardDays: 19,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: -19.50,
          dayChangePercentage: -1.26,
          holdingPeriod: '19 days'
        },
        {
          id: 4,
          userId: '7530',
          userName: 'Swing Trader',
          symbol: 'HDFC-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 300,
          avgPrice: 1380.00,
          ltp: 1505.50,
          pnl: 37650.00,
          pnlPercentage: 9.09,
          tradeDate: '2024-01-05',
          carryForwardDays: 24,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 15.50,
          dayChangePercentage: 1.03,
          holdingPeriod: '24 days'
        },
        {
          id: 5,
          userId: '7531',
          userName: 'Portfolio Manager',
          symbol: 'SBIN-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 500,
          avgPrice: 520.00,
          ltp: 558.75,
          pnl: 19375.00,
          pnlPercentage: 7.45,
          tradeDate: '2023-11-20',
          carryForwardDays: 70,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 8.75,
          dayChangePercentage: 1.57,
          holdingPeriod: '70 days'
        },
        {
          id: 6,
          userId: '7532',
          userName: 'Value Investor',
          symbol: 'WIPRO-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 250,
          avgPrice: 380.00,
          ltp: 425.75,
          pnl: 11437.50,
          pnlPercentage: 12.05,
          tradeDate: '2023-10-15',
          carryForwardDays: 106,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 5.25,
          dayChangePercentage: 1.25,
          holdingPeriod: '106 days'
        },
        {
          id: 7,
          userId: '7527',
          userName: 'Carry Forward Trader 1',
          symbol: 'MARUTI-EQ',
          exchange: 'NSE',
          product: 'NORMAL',
          quantity: 100,
          avgPrice: 9800.00,
          ltp: 10250.00,
          pnl: 45000.00,
          pnlPercentage: 4.59,
          tradeDate: '2024-01-12',
          carryForwardDays: 17,
          brokerage: 0.00,
          status: 'OPEN',
          dayChange: 150.00,
          dayChangePercentage: 1.49,
          holdingPeriod: '17 days'
        }
      ];
      
      setPositions(mockData);
      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error loading Normal positions:', error);
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
              <h1 className="text-xl font-semibold text-gray-900">All Positions Normal</h1>
              <span className="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                NORMAL
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
                <Calendar className="w-4 h-4 text-gray-500" />
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="border border-gray-300 rounded-md px-3 py-1 text-sm"
                />
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
                <option>Holding Period(asc)</option>
                <option>Holding Period(desc)</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Carry Forward indicator */}
      <div className="bg-green-50 border-b border-green-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm text-green-800 font-medium">Carry Forward (Normal) Positions</span>
            <span className="text-sm text-green-600">
              ({filteredPositions.length} active positions)
            </span>
            <span className="text-sm text-gray-600">
              • Zero brokerage • Long-term holdings
            </span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 p-6 border-b border-gray-200">
            <div className="bg-green-50 rounded-lg p-4">
              <div className="text-sm text-green-600 font-medium">Total Positions</div>
              <div className="text-2xl font-bold text-green-900">{filteredPositions.length}</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-4">
              <div className="text-sm text-blue-600 font-medium">Total P&L</div>
              <div className={`text-2xl font-bold ${
                filteredPositions.reduce((sum, p) => sum + p.pnl, 0) >= 0 ? 'text-blue-900' : 'text-red-900'
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
                    Holding Period
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Trade Date
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
                      <div className="flex items-center space-x-1">
                        <span className="font-medium">{position.holdingPeriod}</span>
                        <span className="text-xs text-gray-500">({position.carryForwardDays} days)</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {position.tradeDate}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <span className={`px-2 py-1 text-xs rounded-full ${
                          position.status === 'OPEN' 
                            ? 'bg-green-100 text-green-800' 
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {position.status}
                        </span>
                        <span className="text-xs text-gray-500">0% brokerage</span>
                      </div>
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

export default PositionsNormal;