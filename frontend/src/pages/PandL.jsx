import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';

const PandL = () => {
  const [loading, setLoading] = useState(false);
  const [pandlData, setPandlData] = useState([]);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  useEffect(() => {
    loadPandLData();
  }, []);

  const loadPandLData = async () => {
    setLoading(true);
    try {
      const [positionsResponse, usersResponse] = await Promise.all([
        apiService.get('/portfolio/positions'),
        apiService.get('/admin/users')
      ]);
      const users = usersResponse?.data || [];
      const userMap = new Map(users.map((u) => [u.id, u.username || `User ${u.id}`]));
      const positions = positionsResponse?.data || [];

      const grouped = new Map();
      positions.forEach((pos) => {
        const entry = grouped.get(pos.user_id) || { realized: 0, unrealized: 0 };
        entry.realized += Number(pos.realizedPnl || 0);
        entry.unrealized += Number(pos.mtm || 0);
        grouped.set(pos.user_id, entry);
      });

      const date = new Date().toISOString().split('T')[0];
      const rows = Array.from(grouped.entries()).map(([userId, totals], idx) => {
        const totalPnl = totals.realized + totals.unrealized;
        return {
          id: idx + 1,
          date: date,
          userId: String(userId),
          userName: userMap.get(userId) || `User ${userId}`,
          realizedPnl: totals.realized,
          unrealizedPnl: totals.unrealized,
          totalPnl: totalPnl,
          brokerage: 0,
          netPnl: totalPnl
        };
      });

      setPandlData(rows);
    } catch (error) {
      console.error('Error loading P&L data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    setLoading(true);
    try {
      // API call would go here
      await loadPandLData();
    } catch (error) {
      console.error('Error searching P&L data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">P&L Report</h2>
          <p className="text-sm text-gray-600 mt-1">View profit and loss details</p>
        </div>
        
        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                From Date
              </label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                To Date
              </label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Search'}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    User Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Realized P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Unrealized P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total P&L
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Brokerage
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Net P&L
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pandlData.map((item) => (
                  <tr key={item.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.userId}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {item.userName}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{item.realizedPnl.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{item.unrealizedPnl.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{item.totalPnl.toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{item.brokerage.toFixed(2)}
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                      item.netPnl >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      ₹{item.netPnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {pandlData.length === 0 && !loading && (
              <div className="text-center py-8 text-gray-500">
                No P&L data found
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PandL;
