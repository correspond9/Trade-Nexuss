import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { ChevronDown, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react';

const PositionsUserwise = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [userPositions, setUserPositions] = useState([]);
  const [expandedUsers, setExpandedUsers] = useState(new Set());
  const [sortBy, setSortBy] = useState('UserId(asc)');

  useEffect(() => {
    loadUserPositions();
  }, []);

  const loadUserPositions = async () => {
    setLoading(true);
    try {
      // Mock data matching straddly.com structure
      const mockData = [
        {
          userId: '7522',
          userName: 'C.K. Nanaiah',
          profit: 5075.00,
          stopLoss: 2500.00,
          trialBy: 100000.00,
          trialAfter: 105075.00,
          fund: 50000.00,
          pandl: 5075.00,
          pandlPercentage: 10.15,
          positions: [
            {
              id: 1,
              symbol: 'RELIANCE-EQ',
              exchange: 'NSE',
              product: 'MIS',
              quantity: 100,
              avgPrice: 2500.50,
              ltp: 2520.75,
              pnl: 2075.00,
              type: 'OPEN'
            },
            {
              id: 2,
              symbol: 'TCS-EQ', 
              exchange: 'NSE',
              product: 'NORMAL',
              quantity: 50,
              avgPrice: 3450.75,
              ltp: 3520.75,
              pnl: 3500.00,
              type: 'OPEN'
            }
          ]
        },
        {
          userId: '7523',
          userName: 'Demo User',
          profit: -1250.00,
          stopLoss: 3000.00,
          trialBy: 75000.00,
          trialAfter: 73750.00,
          fund: 25000.00,
          pandl: -1250.00,
          pandlPercentage: -5.00,
          positions: [
            {
              id: 3,
              symbol: 'INFY-EQ',
              exchange: 'NSE',
              product: 'MIS',
              quantity: 75,
              avgPrice: 1550.25,
              ltp: 1530.50,
              pnl: -1481.25,
              type: 'OPEN'
            }
          ]
        },
        {
          userId: '7524',
          userName: 'Test Trader',
          profit: 8900.00,
          stopLoss: 2000.00,
          trialBy: 120000.00,
          trialAfter: 128900.00,
          fund: 75000.00,
          pandl: 8900.00,
          pandlPercentage: 11.87,
          positions: [
            {
              id: 4,
              symbol: 'HDFC-EQ',
              exchange: 'NSE',
              product: 'NORMAL',
              quantity: 150,
              avgPrice: 1450.00,
              ltp: 1505.50,
              pnl: 8325.00,
              type: 'OPEN'
            },
            {
              id: 5,
              symbol: 'SBIN-EQ',
              exchange: 'NSE',
              product: 'MIS',
              quantity: 200,
              avgPrice: 550.25,
              ltp: 558.75,
              pnl: 1700.00,
              type: 'OPEN'
            }
          ]
        }
      ];
      
      setUserPositions(mockData);
    } catch (error) {
      console.error('Error loading user positions:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleUserExpansion = (userId) => {
    const newExpanded = new Set(expandedUsers);
    if (newExpanded.has(userId)) {
      newExpanded.delete(userId);
    } else {
      newExpanded.add(userId);
    }
    setExpandedUsers(newExpanded);
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

  if (loading) {
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
              <h1 className="text-xl font-semibold text-gray-900">All Positions Userwise</h1>
            </div>
            <div className="flex items-center space-x-4">
              <button className="p-2 text-gray-500 hover:text-gray-700">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
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

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white shadow-sm rounded-lg overflow-hidden">
          {/* Table Header */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>User Id</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>Profit</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>S L</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>Trial By</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>Trial After</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>Fund</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>PandL</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    <div className="flex items-center space-x-1">
                      <span>PandL %</span>
                      <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                      </svg>
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {userPositions.map((user) => (
                  <React.Fragment key={user.userId}>
                    <tr className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.userId}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(user.profit)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(user.stopLoss)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(user.trialBy)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(user.trialAfter)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatCurrency(user.fund)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className={`font-medium ${user.pandl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(user.pandl)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className={`font-medium ${user.pandlPercentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatPercentage(user.pandlPercentage)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <button
                          onClick={() => toggleUserExpansion(user.userId)}
                          className="text-blue-600 hover:text-blue-900 flex items-center space-x-1"
                        >
                          {expandedUsers.has(user.userId) ? (
                            <ChevronDown className="w-4 h-4" />
                          ) : (
                            <ChevronRight className="w-4 h-4" />
                          )}
                          <span>{expandedUsers.has(user.userId) ? 'Hide' : 'View'}</span>
                        </button>
                      </td>
                    </tr>
                    
                    {/* Expanded Positions */}
                    {expandedUsers.has(user.userId) && (
                      <tr>
                        <td colSpan="9" className="px-0 py-0 bg-gray-50">
                          <div className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900 mb-3">
                              Positions for {user.userName} (User ID: {user.userId})
                            </div>
                            <div className="overflow-x-auto">
                              <table className="min-w-full divide-y divide-gray-200 border border-gray-200">
                                <thead className="bg-gray-100">
                                  <tr>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Exchange</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Quantity</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Avg Price</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">LTP</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">P&L</th>
                                    <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                  </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                  {user.positions.map((position) => (
                                    <tr key={position.id} className="hover:bg-gray-50">
                                      <td className="px-4 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
                                        {position.symbol}
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {position.exchange}
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                          position.product === 'MIS' 
                                            ? 'bg-blue-100 text-blue-800' 
                                            : 'bg-green-100 text-green-800'
                                        }`}>
                                          {position.product}
                                        </span>
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {position.quantity}
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {formatCurrency(position.avgPrice)}
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        {formatCurrency(position.ltp)}
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm">
                                        <div className={`font-medium ${position.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                          {formatCurrency(position.pnl)}
                                        </div>
                                      </td>
                                      <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-900">
                                        <span className={`px-2 py-1 text-xs rounded-full ${
                                          position.type === 'OPEN' 
                                            ? 'bg-green-100 text-green-800' 
                                            : 'bg-gray-100 text-gray-800'
                                        }`}>
                                          {position.type}
                                        </span>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PositionsUserwise;