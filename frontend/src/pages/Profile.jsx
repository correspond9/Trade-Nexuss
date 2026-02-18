import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';

const ChangePasswordForm = ({ userId }) => {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [formSuccess, setFormSuccess] = useState('');

  const isStrongPassword = (value) => {
    if (!value || value.length < 8) {
      return false;
    }
    const hasUpper = /[A-Z]/.test(value);
    const hasLower = /[a-z]/.test(value);
    const hasDigit = /\d/.test(value);
    const hasSpecial = /[!@#$%^&*()\-[\]{};:'",.<>/?\\|`~_=+]/.test(value);
    return hasUpper && hasLower && hasDigit && hasSpecial;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFormError('');
    setFormSuccess('');
    if (!userId) {
      setFormError('User not available');
      return;
    }
    if (!currentPassword || !newPassword || !confirmPassword) {
      setFormError('All password fields are required');
      return;
    }
    if (newPassword !== confirmPassword) {
      setFormError('New passwords do not match');
      return;
    }
    if (!isStrongPassword(newPassword)) {
      setFormError('Password does not meet the required complexity');
      return;
    }
    setSubmitting(true);
    try {
      await apiService.post('/auth/change-password', {
        user_id: userId,
        current_password: currentPassword,
        new_password: newPassword
      });
      setFormSuccess('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error) {
      setFormError(error?.message || 'Failed to update password');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-600">Current Password</label>
        <input
          type="password"
          value={currentPassword}
          onChange={(event) => setCurrentPassword(event.target.value)}
          className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring focus:ring-indigo-200"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-600">New Password</label>
        <input
          type="password"
          value={newPassword}
          onChange={(event) => setNewPassword(event.target.value)}
          className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring focus:ring-indigo-200"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-600">Confirm New Password</label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(event) => setConfirmPassword(event.target.value)}
          className="mt-1 w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring focus:ring-indigo-200"
        />
      </div>
      {formError && <div className="text-sm text-red-600">{formError}</div>}
      {formSuccess && <div className="text-sm text-green-600">{formSuccess}</div>}
      <button
        type="submit"
        disabled={submitting}
        className="bg-indigo-500 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
      >
        {submitting ? 'Updating...' : 'Update Password'}
      </button>
    </form>
  );
};

const Profile = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [profitTarget, setProfitTarget] = useState('');
  const [stopLossTarget, setStopLossTarget] = useState('');

  const [ledgerLoading, setLedgerLoading] = useState(false);
  const [ledgerRows, setLedgerRows] = useState([]);
  const [tradeLoading, setTradeLoading] = useState(false);
  const [tradeRows, setTradeRows] = useState([]);
  const [pnlLoading, setPnlLoading] = useState(false);
  const [pnlRows, setPnlRows] = useState([]);
  const [pnlHistory, setPnlHistory] = useState([]);
  const [marginLoading, setMarginLoading] = useState(false);
  const [marginData, setMarginData] = useState(null);
  const [marginError, setMarginError] = useState('');

  useEffect(() => {
    const nextProfit = user?.profit_target ?? '';
    const nextSl = user?.stop_loss_target ?? '';
    setProfitTarget(nextProfit === null ? '' : String(nextProfit));
    setStopLossTarget(nextSl === null ? '' : String(nextSl));
  }, [user]);

  useEffect(() => {
    const loadLedger = async () => {
      if (!user?.id) return;
      setLedgerLoading(true);
      try {
        const response = await apiService.get('/admin/ledger', { user_id: user.id });
        const data = response?.data || [];
        const openingBalance = Number(user?.wallet_balance || 0);

        const normalized = data.map((entry) => {
          const createdAt = entry.created_at || new Date().toISOString();
          const dateObj = new Date(createdAt);
          const credit = Number(entry.credit || 0);
          const debit = Number(entry.debit || 0);
          return {
            id: entry.id,
            createdAt,
            dateObj,
            credit,
            debit,
            entry,
          };
        });

        const ascending = [...normalized].sort((a, b) => {
          const tA = new Date(a.createdAt).getTime() || 0;
          const tB = new Date(b.createdAt).getTime() || 0;
          if (tA !== tB) return tA - tB;
          return Number(a.id || 0) - Number(b.id || 0);
        });

        let runningBalance = openingBalance;
        const runningById = new Map();
        ascending.forEach((row) => {
          runningBalance += row.credit - row.debit;
          runningById.set(row.id, runningBalance);
        });

        const mapped = [...normalized]
          .sort((a, b) => {
            const tA = new Date(a.createdAt).getTime() || 0;
            const tB = new Date(b.createdAt).getTime() || 0;
            if (tA !== tB) return tB - tA;
            return Number(b.id || 0) - Number(a.id || 0);
          })
          .map((row) => {
            const { entry, dateObj, credit } = row;
          const debit = Number(entry.debit || 0);
          return {
            id: entry.id,
            date: dateObj.toLocaleDateString('en-IN'),
            type: credit > 0 ? 'CREDIT' : 'DEBIT',
            category: entry.entry_type || 'UNKNOWN',
            description: entry.remarks || '-',
            amount: credit > 0 ? credit : -debit,
            balance: Number(runningById.get(entry.id) || openingBalance),
          };
        });
        setLedgerRows(mapped);
      } finally {
        setLedgerLoading(false);
      }
    };
    if (activeTab === 'ledger') {
      loadLedger();
    }
  }, [activeTab, user]);

  useEffect(() => {
    const loadTrades = async () => {
      if (!user?.id) return;
      setTradeLoading(true);
      try {
        const response = await apiService.get('/trading/orders', { user_id: user.id });
        const data = response?.data || [];
        const mapped = data
          .filter((order) => {
            const status = String(order.status || '').toUpperCase();
            return status === 'EXECUTED' || status === 'PARTIAL';
          })
          .map((order) => {
          const createdAt = order.created_at || order.updated_at || new Date().toISOString();
          return {
            id: order.id,
            createdAt,
            date: new Date(createdAt).toLocaleString('en-IN'),
            symbol: order.symbol || '-',
            side: String(order.transaction_type || 'BUY').toUpperCase(),
            qty: Number(order.quantity || 0),
            price: Number(order.price || 0),
            status: String(order.status || 'PENDING').toUpperCase(),
          };
        })
          .sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
        setTradeRows(mapped);
      } finally {
        setTradeLoading(false);
      }
    };
    if (activeTab === 'trade-history') {
      loadTrades();
    }
  }, [activeTab, user]);

  useEffect(() => {
    const loadPnl = async () => {
      if (!user?.id) return;
      setPnlLoading(true);
      try {
        const [positionsResponse, snapshotsResponse] = await Promise.all([
          apiService.get('/portfolio/positions', { user_id: user.id }),
          apiService.get('/admin/pnl/snapshots', { user_id: user.id })
        ]);
        const data = positionsResponse?.data || [];
        const mapped = data.map((pos) => {
          const mtm = Number(pos.mtm || 0);
          const realized = Number(pos.realizedPnl || 0);
          return {
            id: pos.id,
            symbol: pos.symbol,
            product: pos.product_type,
            quantity: Number(pos.quantity || 0),
            avgPrice: Number(pos.avg_price || 0),
            mtm,
            realized,
            total: mtm + realized
          };
        });
        setPnlRows(mapped);
        const history = snapshotsResponse?.data || [];
        setPnlHistory(history.map((row) => ({
          id: row.id,
          date: new Date(row.created_at || new Date().toISOString()).toLocaleString('en-IN'),
          realized: Number(row.realized_pnl || 0),
          mtm: Number(row.mtm || 0),
          total: Number(row.total_pnl || 0)
        })));
      } finally {
        setPnlLoading(false);
      }
    };
    if (activeTab === 'pnl') {
      loadPnl();
    }
  }, [activeTab, user]);

  useEffect(() => {
    const loadMargin = async () => {
      if (!user?.id) return;
      setMarginLoading(true);
      setMarginError('');
      try {
        const response = await apiService.get('/margin/account', { user_id: user.id });
        setMarginData(response?.data || null);
      } catch (error) {
        setMarginError('Failed to load margin');
        setMarginData(null);
      } finally {
        setMarginLoading(false);
      }
    };
    if (activeTab === 'margin') {
      loadMargin();
    }
  }, [activeTab, user]);

  const pnlSummary = useMemo(() => {
    const realized = pnlRows.reduce((sum, row) => sum + row.realized, 0);
    const mtm = pnlRows.reduce((sum, row) => sum + row.mtm, 0);
    return {
      realized,
      mtm,
      total: realized + mtm
    };
  }, [pnlRows]);

  const statusValue = String(user?.status || '').toUpperCase();
  const statusLabel = statusValue === 'ACTIVE'
    ? 'APPROVED'
    : statusValue === 'BLOCKED'
      ? 'BLOCKED'
      : statusValue === 'INACTIVE'
        ? 'INACTIVE'
        : 'PENDING';
  const statusClasses = statusValue === 'ACTIVE'
    ? 'border-green-500 bg-green-100 text-green-500'
    : statusValue === 'BLOCKED'
      ? 'border-red-500 bg-red-100 text-red-500'
      : 'border-gray-400 bg-gray-100 text-gray-500';
  const fullName = user?.username || user?.name || '-';
  const userId = user?.user_id || user?.id || '-';
  const mfaEnabled = Boolean(user?.mfa_enabled || user?.mfaEnabled);
  const displayValue = (value) => value ? value : '-';
  const marginAvailable = Number(marginData?.available_margin ?? 0);
  const marginUsed = Number(marginData?.used_margin ?? 0);
  const marginAllocated = marginAvailable + marginUsed;
  const formatAmount = (value) => Number(value || 0).toFixed(2);

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h1 className="text-2xl font-bold text-gray-900">Profile</h1>
        <p className="mt-2 text-gray-600">Manage your account and reports</p>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 px-6 py-3">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'profile', label: 'Profile' },
              { id: 'ledger', label: 'Ledger' },
              { id: 'pnl', label: 'P&L' },
              { id: 'trade-history', label: 'Trade History' },
              { id: 'margin', label: 'Margin' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{ boxShadow: 'none' }}
                className={`inline-flex items-center justify-center whitespace-nowrap min-h-[40px] px-4 py-2 text-sm font-medium rounded-md border transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                    : 'border-gray-200 bg-white text-gray-600 hover:text-gray-800 hover:bg-gray-50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {activeTab === 'profile' && (
          <div className="px-4 sm:px-6 md:px-0">
            <div className="py-0">
              <div className="mt-10 divide-y divide-gray-200 p-5 rounded-md bg-white">
                <div className="space-y-1 relative">
                  <h3 className="text-lg leading-6 font-medium text-gray-900">Profile</h3>
                  <p className="max-w-2xl text-sm text-gray-500">Please fill in your information below.</p>
                  <div className={`border-dashed absolute right-0 -top-4 font-bold rounded-md text-lg px-4 py-2 w-fit border-4 uppercase ${statusClasses}`}>
                    {statusLabel}
                  </div>
                </div>
                <div className="mt-6">
                  <dl className="divide-y divide-gray-200">
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">MFA</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className={mfaEnabled ? 'text-green-500' : 'text-gray-400'}>
                          {mfaEnabled ? 'Enabled' : 'Not Configured'}
                        </span>
                        <button className="text-indigo-500 ml-auto w-lg hover:underline p-2">
                          Configure MFA
                        </button>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">UserId</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(userId)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">Name</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(fullName)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">Mobile</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.mobile)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">Email</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.email)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">Aadhar Number</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.aadhar)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">PAN Number</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.pan)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">UPI</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.upi)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-3 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500">Address</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:col-span-2">
                        <span className="flex-grow">{displayValue(user?.address)}</span>
                      </dd>
                    </div>
                    <div className="py-4 sm:py-5 sm:grid sm:grid-cols-9 sm:gap-4">
                      <dt className="text-sm font-medium text-gray-500 col-span-3">Target</dt>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0 sm:text-right text-left">
                        <span className="flex-grow py-3">Profit</span>
                      </dd>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0">
                        <input
                          type="number"
                          max="100"
                          min="0"
                          name="profit"
                          placeholder="Profit"
                          value={profitTarget}
                          onChange={(event) => setProfitTarget(event.target.value)}
                          className="border-0 px-3 py-3 placeholder-gray-300 text-gray-600 bg-white rounded text-sm shadow focus:outline-none focus:ring w-full ease-linear transition-all duration-150"
                        />
                      </dd>
                      <dd className="mt-1 flex text-sm sm:text-right text-left text-gray-900 sm:mt-0">
                        <span className="flex-grow py-3">S L</span>
                      </dd>
                      <dd className="mt-1 flex text-sm text-gray-900 sm:mt-0">
                        <input
                          type="number"
                          min="-20"
                          max="0"
                          name="sl"
                          placeholder="S L"
                          value={stopLossTarget}
                          onChange={(event) => setStopLossTarget(event.target.value)}
                          className="border-0 px-3 py-3 placeholder-gray-300 text-gray-600 bg-white rounded text-sm shadow focus:outline-none focus:ring w-full ease-linear transition-all duration-150"
                        />
                      </dd>
                      <dd className="col-span-2 mt-4 sm:mt-0">
                        <button className="bg-indigo-500 w-full text-white border rounded p-2">Update Target</button>
                      </dd>
                    </div>
                  </dl>
                </div>
              </div>
              <div className="mt-6 p-5 rounded-md bg-white">
                <h3 className="text-lg leading-6 font-medium text-gray-900">Change Password</h3>
                <p className="text-sm text-gray-500 mt-1">Password must be at least 8 characters and include 1 uppercase, 1 lowercase, 1 number, and 1 special character.</p>
                <ChangePasswordForm userId={user?.id} />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'ledger' && (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Ledger</h2>
            <div className="mb-3 text-sm text-gray-700">
              Opening Balance: <span className="font-semibold">{Number(user?.wallet_balance || 0).toFixed(2)}</span>
            </div>
            {ledgerLoading ? (
              <div className="text-sm text-gray-500">Loading ledger...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Balance</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {ledgerRows.map((row) => (
                      <tr key={row.id}>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.date}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.type}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.category}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.description}</td>
                        <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.amount.toFixed(2)}</td>
                        <td className="px-4 py-2 text-sm text-gray-700 text-right">{Number(row.balance || 0).toFixed(2)}</td>
                      </tr>
                    ))}
                    {ledgerRows.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-4 text-center text-sm text-gray-500">No ledger entries found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'pnl' && (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">P&L</h2>
            {pnlLoading ? (
              <div className="text-sm text-gray-500">Loading P&L...</div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">Realized</div>
                    <div className="text-lg font-semibold text-gray-900">{pnlSummary.realized.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">MTM</div>
                    <div className="text-lg font-semibold text-gray-900">{pnlSummary.mtm.toFixed(2)}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">Total</div>
                    <div className="text-lg font-semibold text-gray-900">{pnlSummary.total.toFixed(2)}</div>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Product</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Avg</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">MTM</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Realized</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {pnlRows.map((row) => (
                        <tr key={row.id}>
                          <td className="px-4 py-2 text-sm text-gray-700">{row.symbol}</td>
                          <td className="px-4 py-2 text-sm text-gray-700">{row.product}</td>
                          <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.quantity}</td>
                          <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.avgPrice.toFixed(2)}</td>
                          <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.mtm.toFixed(2)}</td>
                          <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.realized.toFixed(2)}</td>
                          <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.total.toFixed(2)}</td>
                        </tr>
                      ))}
                      {pnlRows.length === 0 && (
                        <tr>
                          <td colSpan={7} className="px-4 py-4 text-center text-sm text-gray-500">No P&L records found</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div className="mt-8">
                  <h3 className="text-md font-semibold text-gray-900 mb-3">Historical Snapshots</h3>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Realized</th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">MTM</th>
                          <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {pnlHistory.map((row) => (
                          <tr key={row.id}>
                            <td className="px-4 py-2 text-sm text-gray-700">{row.date}</td>
                            <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.realized.toFixed(2)}</td>
                            <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.mtm.toFixed(2)}</td>
                            <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.total.toFixed(2)}</td>
                          </tr>
                        ))}
                        {pnlHistory.length === 0 && (
                          <tr>
                            <td colSpan={4} className="px-4 py-4 text-center text-sm text-gray-500">No snapshots recorded yet</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {activeTab === 'trade-history' && (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Trade History</h2>
            {tradeLoading ? (
              <div className="text-sm text-gray-500">Loading trades...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Symbol</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Side</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Qty</th>
                      <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Price</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {tradeRows.map((row) => (
                      <tr key={row.id}>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.date}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.symbol}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.side}</td>
                        <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.qty}</td>
                        <td className="px-4 py-2 text-sm text-gray-700 text-right">{row.price.toFixed(2)}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{row.status}</td>
                      </tr>
                    ))}
                    {tradeRows.length === 0 && (
                      <tr>
                        <td colSpan={6} className="px-4 py-4 text-center text-sm text-gray-500">No trades found</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'margin' && (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Margin</h2>
            {marginLoading ? (
              <div className="text-sm text-gray-500">Loading margin...</div>
            ) : marginError ? (
              <div className="text-sm text-red-600">{marginError}</div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">Allotted Margin</div>
                    <div className="text-lg font-semibold text-gray-900">₹{formatAmount(marginAllocated)}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">Used Margin</div>
                    <div className="text-lg font-semibold text-gray-900">₹{formatAmount(marginUsed)}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-xs text-gray-500">Available Margin</div>
                    <div className="text-lg font-semibold text-gray-900">₹{formatAmount(marginAvailable)}</div>
                  </div>
                </div>
                <div className="text-sm text-gray-500">
                  Available Margin = Allotted Margin - Used Margin
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;
