import React, { useState, useEffect } from 'react';
import { useAppContext } from '../contexts/AppContext';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { Search, Filter, Download, Calendar, TrendingUp, TrendingDown, DollarSign, ArrowUpRight, ArrowDownRight, Receipt, FileText, Eye, RefreshCw } from 'lucide-react';

const Ledger = () => {
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [dateRange, setDateRange] = useState('30d');
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    fetchTransactions();
    fetchSummary();
  }, [dateRange, filterType]);

  useEffect(() => {
    fetchSummary();
  }, [transactions]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = {};
      if (user?.id) {
        params.user_id = user.id;
      }
      const response = await apiService.get('/admin/ledger', params);
      const data = response?.data || [];
      let mapped = data.map((entry) => {
        const createdAt = entry.created_at || new Date().toISOString();
        const dateObj = new Date(createdAt);
        const credit = Number(entry.credit || 0);
        const debit = Number(entry.debit || 0);
        return {
          id: entry.id,
          date: dateObj.toISOString().split('T')[0],
          time: dateObj.toLocaleTimeString('en-IN'),
          type: credit > 0 ? 'CREDIT' : 'DEBIT',
          category: entry.entry_type || 'UNKNOWN',
          description: entry.remarks || '-',
          amount: credit > 0 ? credit : -debit,
          balance: entry.balance || 0,
          reference: String(entry.id),
          status: 'COMPLETED',
          userId: entry.user_id,
          userName: user?.username || user?.full_name || 'user'
        };
      });

      if (dateRange !== 'all') {
        const days = parseInt(dateRange.replace('d', ''), 10);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        mapped = mapped.filter(t => new Date(t.date) >= cutoffDate);
      }

      if (filterType !== 'all') {
        mapped = mapped.filter(t => t.type === filterType);
      }

      setTransactions(mapped);
    } catch (error) {
      console.error('Failed to fetch transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async () => {
    try {
      const params = {};
      if (user?.id) {
        params.user_id = user.id;
      }
      const response = await apiService.get('/admin/ledger/summary', params);
      const data = response?.data || {};
      setSummary({
        totalCredits: data.total_credit || 0,
        totalDebits: data.total_debit || 0,
        netBalance: (data.total_credit || 0) - (data.total_debit || 0),
        transactionCount: transactions.length,
        pendingTransactions: 0,
        lastUpdated: new Date().toLocaleString('en-IN')
      });
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  };

  const filteredTransactions = transactions.filter(transaction =>
    transaction.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    transaction.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    transaction.userName?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const exportLedger = () => {
    // Export functionality
    console.log('Exporting ledger data...');
  };

  const refreshData = () => {
    fetchTransactions();
    fetchSummary();
  };

  const getStatusBadge = (status) => {
    const styles = {
      COMPLETED: 'bg-green-100 text-green-800',
      PROCESSING: 'bg-yellow-100 text-yellow-800',
      PENDING: 'bg-blue-100 text-blue-800',
      FAILED: 'bg-red-100 text-red-800'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-bold ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {status}
      </span>
    );
  };

  const getCategoryBadge = (category) => {
    const styles = {
      FUND_ADD: 'bg-blue-100 text-blue-800',
      TRADE: 'bg-purple-100 text-purple-800',
      CHARGES: 'bg-orange-100 text-orange-800',
      WITHDRAWAL: 'bg-red-100 text-red-800',
      PAYOUT: 'bg-green-100 text-green-800',
      TAX: 'bg-gray-100 text-gray-800',
      REFUND: 'bg-indigo-100 text-indigo-800'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-bold ${styles[category] || 'bg-gray-100 text-gray-800'}`}>
        {category.replace('_', ' ')}
      </span>
    );
  };

  const SummaryCard = ({ title, value, icon: Icon, color = 'blue', trend }) => (
    <div className={`bg-white rounded-lg shadow p-6 border-l-4 border-${color}-500`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className={`text-2xl font-bold text-${color}-600`}>
            {typeof value === 'number' 
              ? `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : value
            }
          </p>
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
            <h1 className="text-2xl font-bold text-gray-900">Ledger</h1>
            <p className="mt-2 text-gray-600">View transaction history and financial records</p>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={refreshData}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </button>
            <button
              onClick={exportLedger}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <SummaryCard
            title="Total Credits"
            value={summary.totalCredits}
            icon={ArrowUpRight}
            color="green"
          />
          <SummaryCard
            title="Total Debits"
            value={summary.totalDebits}
            icon={ArrowDownRight}
            color="red"
          />
          <SummaryCard
            title="Net Balance"
            value={summary.netBalance}
            icon={DollarSign}
            color={summary.netBalance >= 0 ? 'green' : 'red'}
          />
          <SummaryCard
            title="Transactions"
            value={summary.transactionCount}
            icon={Receipt}
            color="blue"
          />
          <SummaryCard
            title="Pending"
            value={summary.pendingTransactions}
            icon={FileText}
            color="yellow"
          />
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
            <input
              type="text"
              placeholder="Search transactions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Types</option>
            <option value="CREDIT">Credits</option>
            <option value="DEBIT">Debits</option>
          </select>
          
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
            <option value="90d">Last 90 Days</option>
            <option value="1y">Last Year</option>
            <option value="all">All Time</option>
          </select>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date & Time
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Category
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Description
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Balance
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    </div>
                  </td>
                </tr>
              ) : filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                    No transactions found
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((transaction) => (
                  <tr key={transaction.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{new Date(transaction.date).toLocaleDateString()}</div>
                        <div className="text-gray-500">{transaction.time}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        transaction.type === 'CREDIT' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {transaction.type}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getCategoryBadge(transaction.category)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{transaction.description}</div>
                        <div className="text-gray-500">Ref: {transaction.reference}</div>
                      </div>
                    </td>
                    <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                      transaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {transaction.amount >= 0 ? '+' : ''}
                      ₹{Math.abs(transaction.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      ₹{transaction.balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(transaction.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => {
                          setSelectedTransaction(transaction);
                          setShowDetails(true);
                        }}
                        className="text-indigo-600 hover:text-indigo-900 flex items-center gap-1"
                      >
                        <Eye className="w-4 h-4" />
                        View
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction Details Modal */}
      {showDetails && selectedTransaction && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Transaction Details</h2>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              <div className="space-y-6">
                {/* Transaction Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{selectedTransaction.description}</h3>
                    <p className="text-gray-500">Reference: {selectedTransaction.reference}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-2xl font-bold ${
                      selectedTransaction.amount >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {selectedTransaction.amount >= 0 ? '+' : ''}
                      ₹{Math.abs(selectedTransaction.amount).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    {getStatusBadge(selectedTransaction.status)}
                  </div>
                </div>

                {/* Transaction Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Date</p>
                    <p className="text-gray-900">{new Date(selectedTransaction.date).toLocaleDateString()}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Time</p>
                    <p className="text-gray-900">{selectedTransaction.time}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Type</p>
                    <div className="mt-1">
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        selectedTransaction.type === 'CREDIT' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {selectedTransaction.type}
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Category</p>
                    <div className="mt-1">
                      {getCategoryBadge(selectedTransaction.category)}
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">User</p>
                    <p className="text-gray-900">{selectedTransaction.userName}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Balance After</p>
                    <p className="text-gray-900">₹{selectedTransaction.balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                </div>

                {/* Additional Information */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-2">Additional Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Transaction ID:</span>
                      <span className="text-gray-900">#{selectedTransaction.id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">User ID:</span>
                      <span className="text-gray-900">{selectedTransaction.userId}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">Last Updated:</span>
                      <span className="text-gray-900">{summary?.lastUpdated || 'N/A'}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Ledger;