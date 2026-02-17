import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';

const ALLOWED_ENTRY_TYPES = new Set(['PAYIN', 'PAYOUT', 'TRADE_PNL', 'ADJUST']);

const toDateInputValue = (date) => date.toISOString().split('T')[0];

const formatDate = (rawDate) => {
  try {
    return new Date(rawDate).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  } catch (_e) {
    return '-';
  }
};

const parseTxnType = (entryType, remarks = '') => {
  const text = String(remarks || '').toUpperCase();
  if (text.includes('UPI')) return 'UPI';
  if (text.includes('IMPS')) return 'IMPS';
  if (entryType === 'TRADE_PNL') return 'TRADE';
  if (entryType === 'ADJUST') return 'ADMIN/S.ADMIN';
  return entryType;
};

const parseParticular = (entryType) => {
  if (entryType === 'PAYIN') return 'payin';
  if (entryType === 'PAYOUT') return 'payout';
  if (entryType === 'TRADE_PNL') return 'trade';
  return 'adjustment';
};

const Ledger = () => {
  const { user } = useAuth();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const today = new Date();
  const defaultFrom = new Date(today.getFullYear(), 0, 1);

  const [fromDate, setFromDate] = useState(toDateInputValue(defaultFrom));
  const [toDate, setToDate] = useState(toDateInputValue(today));
  const [userIdFilter, setUserIdFilter] = useState('');

  const fetchLedger = useCallback(async () => {
    setLoading(true);
    try {
      const isAdmin = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';
      const params = {};
      const normalizedUserId = String(userIdFilter || '').trim();

      if (!isAdmin && user?.id) {
        params.user_id = user.id;
      } else if (normalizedUserId) {
        params.user_id = Number(normalizedUserId);
      }

      const response = await apiService.get('/admin/ledger', params);
      const source = response?.data || [];

      const fromBound = fromDate ? new Date(`${fromDate}T00:00:00`) : null;
      const toBound = toDate ? new Date(`${toDate}T23:59:59`) : null;

      const mapped = source
        .filter((entry) => ALLOWED_ENTRY_TYPES.has(String(entry.entry_type || '').toUpperCase()))
        .filter((entry) => {
          const createdAt = new Date(entry.created_at || new Date().toISOString());
          if (Number.isNaN(createdAt.getTime())) {
            return false;
          }
          if (fromBound && createdAt < fromBound) {
            return false;
          }
          if (toBound && createdAt > toBound) {
            return false;
          }
          return true;
        })
        .map((entry) => {
          const entryType = String(entry.entry_type || '').toUpperCase();
          const remarks = entry.remarks || '-';
          return {
            id: entry.id,
            rawDate: entry.created_at,
            date: formatDate(entry.created_at),
            userId: entry.user_id,
            particular: parseParticular(entryType),
            type: parseTxnType(entryType, remarks),
            remarks,
            credit: Number(entry.credit || 0),
            debit: Number(entry.debit || 0),
          };
        })
        .sort((a, b) => new Date(b.rawDate) - new Date(a.rawDate));

      setRows(mapped);
    } catch (error) {
      console.error('Failed to fetch ledger:', error);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, userIdFilter, user]);

  useEffect(() => {
    fetchLedger();
  }, [fetchLedger]);

  return (
    <div className="min-h-screen bg-gray-100 p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 pt-6">
          <h2 className="text-2xl font-semibold text-gray-900">Ledger Search</h2>
          <p className="text-sm text-gray-600 mt-1">Fill in the details below to fetch your ledger data.</p>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-4">
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
              onClick={fetchLedger}
              disabled={loading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Fetch Ledger'}
            </button>
          </div>
        </div>

        <div className="overflow-x-auto border-t border-gray-200">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">UserId</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Particular</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Remarks</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Credit</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Debit</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">Loading ledger...</td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-sm text-gray-500">No ledger records found</td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{row.date}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{row.userId}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{row.particular}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{row.type}</td>
                    <td className="px-6 py-4 text-sm text-gray-700">{row.remarks}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-green-700">
                      {row.credit > 0 ? `₹${row.credit.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}` : '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-700">
                      {row.debit > 0 ? `₹${row.debit.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}` : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Ledger;
