import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';

const PandL = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [pandlData, setPandlData] = useState([]);
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [userIdFilter, setUserIdFilter] = useState('');

  const loadPandLData = useCallback(async () => {
    setLoading(true);
    try {
      const [positionsResponse, usersResponse] = await Promise.all([
        apiService.get('/portfolio/positions'),
        apiService.get('/admin/users')
      ]);

      const users = usersResponse?.data || [];
      const userNameMap = new Map(users.map((u) => [u.id, u.username || `User ${u.id}`]));
      const userRoleMap = new Map(users.map((u) => [u.id, String(u.role || '').toUpperCase()]));

      const normalizedUserId = String(userIdFilter || '').trim();
      const positions = (positionsResponse?.data || []).filter((pos) => {
        const role = userRoleMap.get(pos.user_id);
        if (role === 'SUPER_ADMIN') {
          return false;
        }
        if (normalizedUserId && String(pos.user_id) !== normalizedUserId) {
          return false;
        }
        return true;
      });

      const grouped = new Map();
      positions.forEach((pos) => {
        const uid = Number(pos.user_id);
        const current = grouped.get(uid) || { realized: 0, unrealized: 0 };
        current.realized += Number(pos.realizedPnl || 0);
        current.unrealized += Number(pos.mtm || 0);
        grouped.set(uid, current);
      });

      const reportDate = new Date().toLocaleDateString('en-IN');
      const rows = Array.from(grouped.entries())
        .map(([uid, totals], idx) => {
          const totalPnl = totals.realized + totals.unrealized;
          return {
            id: idx + 1,
            date: reportDate,
            userId: String(uid),
            userName: userNameMap.get(uid) || `User ${uid}`,
            realizedPnl: totals.realized,
            unrealizedPnl: totals.unrealized,
            totalPnl,
            brokerage: 0,
            netPnl: totalPnl,
          };
        })
        .sort((a, b) => Number(a.userId) - Number(b.userId));

      setPandlData(rows);
    } catch (error) {
      console.error('Error loading P&L data:', error);
    } finally {
      setLoading(false);
    }
  }, [userIdFilter]);

  useEffect(() => {
    loadPandLData();
  }, [loadPandLData]);

  const handleSearch = async () => {
    await loadPandLData();
  };

  return (
    <div className="space-y-6 min-h-screen bg-gray-100 p-6 rounded-lg">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">P &amp; L</h2>
          <p className="text-sm text-gray-600 mt-1">Fill in the details below to fetch your data.</p>
        </div>

        <div className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">From Date</label>
              <input
                type="date"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">To Date</label>
              <input
                type="date"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">User ID</label>
              <input
                type="text"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                placeholder="Enter user id"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={handleSearch}
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Fetch P&L'}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto border border-gray-200 rounded-md">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">UserId</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Realized P&amp;L</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Unrealized P&amp;L</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Total P&amp;L</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Net P&amp;L</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {pandlData.map((item) => (
                  <tr key={item.id}>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{item.date}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{item.userId}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{item.userName}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">₹{item.realizedPnl.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">₹{item.unrealizedPnl.toFixed(2)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm text-right text-gray-900">₹{item.totalPnl.toFixed(2)}</td>
                    <td className={`px-4 py-3 whitespace-nowrap text-sm text-right font-medium ${item.netPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      ₹{item.netPnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {pandlData.length === 0 && !loading && (
              <div className="text-center py-8 text-gray-500">No P&amp;L data found</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PandL;
