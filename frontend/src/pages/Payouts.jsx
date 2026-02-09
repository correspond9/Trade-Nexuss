import React, { useCallback, useEffect, useState } from 'react';
import { apiService } from '../services/apiService';
import { Search, Download, DollarSign, Clock, CheckCircle, XCircle, TrendingUp, TrendingDown, RefreshCw, Eye, CheckSquare, XSquare } from 'lucide-react';

const Payouts = () => {
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [dateRange, setDateRange] = useState('30d');
  const [selectedPayout, setSelectedPayout] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showProcessModal, setShowProcessModal] = useState(false);
  const [summary, setSummary] = useState(null);

  const fetchPayouts = useCallback(async () => {
    setLoading(true);
    try {
      const [payoutsResponse, usersResponse] = await Promise.all([
        apiService.get('/admin/payouts'),
        apiService.get('/admin/users')
      ]);

      const users = usersResponse?.data || [];
      const userMap = new Map(users.map((u) => [u.id, u]));
      const data = payoutsResponse?.data || [];
      let mapped = data.map((entry) => {
        const createdAt = entry.created_at || new Date().toISOString();
        const dateObj = new Date(createdAt);
        const user = userMap.get(entry.user_id) || {};
        const amount = Number(entry.debit || 0);
        return {
          id: entry.id,
          userId: entry.user_id,
          userName: user.username || `User ${entry.user_id}`,
          userEmail: user.email || '-',
          type: 'PAYOUT',
          amount: amount,
          status: 'COMPLETED',
          requestDate: dateObj.toISOString().split('T')[0],
          requestTime: dateObj.toLocaleTimeString('en-IN'),
          processedDate: dateObj.toISOString().split('T')[0],
          processedTime: dateObj.toLocaleTimeString('en-IN'),
          method: 'BANK_TRANSFER',
          bankDetails: {
            accountName: user.username || '-',
            accountNumber: 'N/A',
            bankName: 'N/A',
            ifsc: 'N/A'
          },
          reference: String(entry.id),
          reason: entry.remarks || 'Payout',
          notes: entry.remarks || '',
          approvedBy: 'system',
          processedBy: 'system',
          fees: 0.00,
          netAmount: amount
        };
      });

      if (dateRange !== 'all') {
        const days = parseInt(dateRange.replace('d', ''), 10);
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - days);
        mapped = mapped.filter(p => new Date(p.requestDate) >= cutoffDate);
      }

      if (filterStatus !== 'all') {
        mapped = mapped.filter(p => p.status === filterStatus);
      }

      setPayouts(mapped);
    } catch (error) {
      console.error('Failed to fetch payouts:', error);
    } finally {
      setLoading(false);
    }
  }, [dateRange, filterStatus]);

  const fetchSummary = useCallback(async () => {
    try {
      const totalPayouts = payouts.reduce((sum, p) => sum + (p.amount || 0), 0);
      setSummary({
        totalPayouts: totalPayouts,
        pendingAmount: 0,
        processingAmount: 0,
        completedAmount: totalPayouts,
        rejectedAmount: 0,
        totalRequests: payouts.length,
        pendingRequests: 0,
        processingRequests: 0,
        completedRequests: payouts.length,
        rejectedRequests: 0,
        totalFees: 0,
        lastUpdated: new Date().toLocaleString('en-IN')
      });
    } catch (error) {
      console.error('Failed to fetch summary:', error);
    }
  }, [payouts]);

  useEffect(() => {
    fetchPayouts();
  }, [fetchPayouts]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const filteredPayouts = payouts.filter(payout =>
    payout.userName?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    payout.userEmail?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    payout.reference?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    payout.reason?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const exportPayouts = () => {
    // Export functionality
    console.log('Exporting payouts data...');
  };

  const refreshData = () => {
    fetchPayouts();
    fetchSummary();
  };

  const processPayout = async (payoutId, action) => {
    try {
      // In real implementation, this would call the API
      // await apiService.post(`/admin/payouts/${payoutId}/process`, { action, notes });
      
      console.log(`Processing payout ${payoutId} with action: ${action}`);
      setShowProcessModal(false);
      setSelectedPayout(null);
      fetchPayouts();
      fetchSummary();
    } catch (error) {
      console.error('Failed to process payout:', error);
    }
  };

  const getStatusBadge = (status) => {
    const styles = {
      PENDING: 'bg-blue-100 text-blue-800',
      PROCESSING: 'bg-yellow-100 text-yellow-800',
      COMPLETED: 'bg-green-100 text-green-800',
      REJECTED: 'bg-red-100 text-red-800'
    };
    const icons = {
      PENDING: <Clock className="w-3 h-3" />,
      PROCESSING: <RefreshCw className="w-3 h-3" />,
      COMPLETED: <CheckCircle className="w-3 h-3" />,
      REJECTED: <XCircle className="w-3 h-3" />
    };
    
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-bold flex items-center gap-1 ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {icons[status]}
        {status}
      </span>
    );
  };

  const getTypeBadge = (type) => {
    const styles = {
      WITHDRAWAL: 'bg-orange-100 text-orange-800',
      PAYOUT: 'bg-green-100 text-green-800'
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-bold ${styles[type] || 'bg-gray-100 text-gray-800'}`}>
        {type}
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
            <h1 className="text-2xl font-bold text-gray-900">Payout Management</h1>
            <p className="mt-2 text-gray-600">Process and track user payouts and withdrawals</p>
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
              onClick={exportPayouts}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <SummaryCard
            title="Total Payouts"
            value={summary.totalPayouts}
            icon={DollarSign}
            color="green"
          />
          <SummaryCard
            title="Pending Amount"
            value={summary.pendingAmount}
            icon={Clock}
            color="blue"
          />
          <SummaryCard
            title="Processing Amount"
            value={summary.processingAmount}
            icon={RefreshCw}
            color="yellow"
          />
          <SummaryCard
            title="Completed Amount"
            value={summary.completedAmount}
            icon={CheckCircle}
            color="green"
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
              placeholder="Search payouts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="all">All Status</option>
            <option value="PENDING">Pending</option>
            <option value="PROCESSING">Processing</option>
            <option value="COMPLETED">Completed</option>
            <option value="REJECTED">Rejected</option>
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

      {/* Payouts Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Request Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  User
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Method
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Reason
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
              ) : filteredPayouts.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                    No payouts found
                  </td>
                </tr>
              ) : (
                filteredPayouts.map((payout) => (
                  <tr key={payout.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{new Date(payout.requestDate).toLocaleDateString()}</div>
                        <div className="text-gray-500">{payout.requestTime}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{payout.userName}</div>
                        <div className="text-gray-500">{payout.userEmail}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getTypeBadge(payout.type)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">₹{payout.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                        {payout.fees > 0 && (
                          <div className="text-gray-500">Fees: ₹{payout.fees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getStatusBadge(payout.status)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      <div>
                        <div className="font-medium">{payout.method.replace('_', ' ')}</div>
                        <div className="text-gray-500">{payout.bankDetails.bankName}</div>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div className="max-w-xs truncate" title={payout.reason}>
                        {payout.reason}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => {
                            setSelectedPayout(payout);
                            setShowDetails(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900 flex items-center gap-1"
                        >
                          <Eye className="w-4 h-4" />
                          View
                        </button>
                        
                        {(payout.status === 'PENDING' || payout.status === 'PROCESSING') && (
                          <>
                            <button
                              onClick={() => {
                                setSelectedPayout(payout);
                                setShowProcessModal(true);
                              }}
                              className="text-green-600 hover:text-green-900 flex items-center gap-1"
                            >
                              <CheckSquare className="w-4 h-4" />
                              Process
                            </button>
                            <button
                              onClick={() => processPayout(payout.id, 'reject')}
                              className="text-red-600 hover:text-red-900 flex items-center gap-1"
                            >
                              <XSquare className="w-4 h-4" />
                              Reject
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Payout Details Modal */}
      {showDetails && selectedPayout && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-hidden">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Payout Details</h2>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-80px)]">
              <div className="space-y-6">
                {/* Payout Header */}
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">{selectedPayout.reason}</h3>
                    <p className="text-gray-500">Reference: {selectedPayout.reference}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-gray-900">
                      ₹{selectedPayout.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    {getStatusBadge(selectedPayout.status)}
                  </div>
                </div>

                {/* User Information */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">User Information</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Name</p>
                      <p className="text-gray-900">{selectedPayout.userName}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Email</p>
                      <p className="text-gray-900">{selectedPayout.userEmail}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">User ID</p>
                      <p className="text-gray-900">{selectedPayout.userId}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Type</p>
                      <div className="mt-1">
                        {getTypeBadge(selectedPayout.type)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bank Details */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">Bank Details</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-500">Account Name</p>
                      <p className="text-gray-900">{selectedPayout.bankDetails.accountName}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Account Number</p>
                      <p className="text-gray-900">{selectedPayout.bankDetails.accountNumber}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">Bank Name</p>
                      <p className="text-gray-900">{selectedPayout.bankDetails.bankName}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-gray-500">IFSC Code</p>
                      <p className="text-gray-900">{selectedPayout.bankDetails.ifsc}</p>
                    </div>
                  </div>
                </div>

                {/* Transaction Details */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-gray-500">Request Date</p>
                    <p className="text-gray-900">{new Date(selectedPayout.requestDate).toLocaleDateString()} {selectedPayout.requestTime}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Method</p>
                    <p className="text-gray-900">{selectedPayout.method.replace('_', ' ')}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Gross Amount</p>
                    <p className="text-gray-900">₹{selectedPayout.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Fees</p>
                    <p className="text-gray-900">₹{selectedPayout.fees.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-500">Net Amount</p>
                    <p className="text-gray-900 font-bold">₹{selectedPayout.netAmount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                  </div>
                  {selectedPayout.processedDate && (
                    <div>
                      <p className="text-sm font-medium text-gray-500">Processed Date</p>
                      <p className="text-gray-900">{new Date(selectedPayout.processedDate).toLocaleDateString()} {selectedPayout.processedTime}</p>
                    </div>
                  )}
                </div>

                {/* Notes */}
                <div>
                  <p className="text-sm font-medium text-gray-500 mb-2">Notes</p>
                  <p className="text-gray-900 bg-gray-50 rounded-lg p-3">{selectedPayout.notes}</p>
                </div>

                {/* Processing Information */}
                {(selectedPayout.approvedBy || selectedPayout.processedBy) && (
                  <div className="bg-blue-50 rounded-lg p-4">
                    <h4 className="font-medium text-gray-900 mb-2">Processing Information</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      {selectedPayout.approvedBy && (
                        <div>
                          <span className="text-gray-500">Approved By:</span>
                          <span className="ml-2 text-gray-900">{selectedPayout.approvedBy}</span>
                        </div>
                      )}
                      {selectedPayout.processedBy && (
                        <div>
                          <span className="text-gray-500">Processed By:</span>
                          <span className="ml-2 text-gray-900">{selectedPayout.processedBy}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Process Payout Modal */}
      {showProcessModal && selectedPayout && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between p-4 border-b">
              <h2 className="text-xl font-semibold">Process Payout</h2>
              <button
                onClick={() => setShowProcessModal(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <div className="p-6">
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-500">User</p>
                  <p className="text-gray-900">{selectedPayout.userName}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Amount</p>
                  <p className="text-gray-900 font-bold">₹{selectedPayout.amount.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-500">Reason</p>
                  <p className="text-gray-900">{selectedPayout.reason}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Processing Notes (Optional)
                  </label>
                  <textarea
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    rows="3"
                    placeholder="Add any notes about this processing..."
                  />
                </div>
              </div>
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={() => setShowProcessModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => processPayout(selectedPayout.id, 'approve')}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Approve & Process
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Payouts;
