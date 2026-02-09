import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { apiService } from '../services/apiService';
import { CheckCircle, XCircle, Clock } from 'lucide-react';

const Users = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [showEntries, setShowEntries] = useState(50);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showAddFundsModal, setShowAddFundsModal] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [addFundsForm, setAddFundsForm] = useState({ amount: '', method: '', remarks: '' });
  const [addForm, setAddForm] = useState({
    firstName: '',
    lastName: '',
    email: '',
    role: 'USER',
    status: 'ACTIVE',
    walletBalance: '0',
    marginMultiplier: '5',
    allowedSegments: 'NSE,NFO,BSE,MCX',
    mobile: '',
    brokeragePlanId: '',
    initialPassword: ''
  });
  const [actionError, setActionError] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);
  const isAdmin = ['ADMIN', 'SUPER_ADMIN'].includes(user?.role);
  const showEditColumn = isAdmin;
  const showRemoveColumn = isAdmin;
  const [brokeragePlans, setBrokeragePlans] = useState([]);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    loadUsers();
    loadBrokeragePlans();
  }, [isAdmin]);

  const loadUsers = async () => {
    try {
      const response = await apiService.get('/admin/users');
      const data = response?.data || [];
      const mapped = data.map((u) => {
        const nameParts = (u.username || '').split(' ');
        const firstName = nameParts.shift() || '';
        const lastName = nameParts.join(' ');
        const walletBalanceRaw = Number(u.wallet_balance || 0);
        const marginMultiplier = Number(u.margin_multiplier ?? 5);
        return {
          id: u.id,
          username: u.username || '',
          firstName,
          lastName,
          userType: u.role || 'USER',
          role: u.role || 'USER',
          email: u.email || '-',
          createdOn: u.created_at ? new Date(u.created_at).toLocaleDateString('en-IN') : '-',
          mobile: u.mobile || '-',
          walletBalance: `₹${walletBalanceRaw.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
          walletBalanceRaw,
          marginMultiplier,
          status: u.status || 'PENDING',
          allowedSegments: u.allowed_segments || 'NSE,NFO,BSE,MCX',
          brokeragePlanId: u.brokerage_plan_id || ''
        };
      });
      setUsers(mapped);
    } catch (error) {
      console.error('Error loading users:', error);
    }
  };
  
  const loadBrokeragePlans = async () => {
    try {
      const response = await apiService.get('/admin/brokerage-plans');
      const data = response?.data || [];
      setBrokeragePlans(data);
    } catch (error) {
      console.error('Error loading brokerage plans:', error);
    }
  };

  const handleEdit = (user) => {
    if (!isAdmin) return;
    setSelectedUser(user);
    setEditForm({
      firstName: user.firstName || '',
      lastName: user.lastName || '',
      email: user.email || '',
      role: user.role || 'USER',
      status: user.status || 'PENDING',
      walletBalance: String(user.walletBalanceRaw ?? 0),
      marginMultiplier: String(user.marginMultiplier ?? 5),
      allowedSegments: user.allowedSegments || 'NSE,NFO,BSE,MCX',
      mobile: user.mobile || '',
      brokeragePlanId: user.brokeragePlanId || '',
      initialPassword: ''
    });
    setShowEditModal(true);
  };

  const handleAddFunds = (user) => {
    setSelectedUser(user);
    setAddFundsForm({ amount: '', method: '', remarks: '' });
    setShowAddFundsModal(true);
  };

  const handleEditChange = (field, value) => {
    setEditForm((prev) => ({ ...(prev || {}), [field]: value }));
  };

  const handleAddFundsChange = (field, value) => {
    setAddFundsForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveEdit = async () => {
    if (!selectedUser || !editForm) return;
    setActionError(null);
    setActionLoading(true);
    try {
      if (!editForm.mobile) {
        throw new Error('Mobile number is required');
      }
      const username = `${editForm.firstName || ''} ${editForm.lastName || ''}`.trim() || selectedUser.username;
      const payload = {
        username,
        email: editForm.email || null,
        role: editForm.role || 'USER',
        status: editForm.status || 'PENDING',
        allowed_segments: editForm.allowedSegments || 'NSE,NFO,BSE,MCX',
        wallet_balance: Number(editForm.walletBalance || 0),
        margin_multiplier: Number(editForm.marginMultiplier || 1),
        mobile: editForm.mobile || null,
        brokerage_plan_id: editForm.brokeragePlanId ? Number(editForm.brokeragePlanId) : null,
        initial_password: editForm.initialPassword || null
      };
      await apiService.put(`/admin/users/${selectedUser.id}`, payload);
      await loadUsers();
      setShowEditModal(false);
      setSelectedUser(null);
      setEditForm(null);
    } catch (error) {
      setActionError(error?.message || 'Failed to update user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddUserChange = (field, value) => {
    setAddForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleCreateUser = async () => {
    setActionError(null);
    setActionLoading(true);
    try {
      const username = `${addForm.firstName || ''} ${addForm.lastName || ''}`.trim();
      if (!username) {
        throw new Error('Username is required');
      }
      if (!addForm.mobile) {
        throw new Error('Mobile number is required');
      }
      const payload = {
        username,
        email: addForm.email || null,
        role: addForm.role || 'USER',
        status: addForm.status || 'ACTIVE',
        allowed_segments: addForm.allowedSegments || 'NSE,NFO,BSE,MCX',
        wallet_balance: Number(addForm.walletBalance || 0),
        margin_multiplier: Number(addForm.marginMultiplier || 1),
        mobile: addForm.mobile || null,
        brokerage_plan_id: addForm.brokeragePlanId ? Number(addForm.brokeragePlanId) : null,
        initial_password: addForm.initialPassword || null
      };
      await apiService.post('/admin/users', payload);
      await loadUsers();
      setShowAddUserModal(false);
      setAddForm({
        firstName: '',
        lastName: '',
        email: '',
        role: 'USER',
        status: 'ACTIVE',
        walletBalance: '0',
        marginMultiplier: '5',
        allowedSegments: 'NSE,NFO,BSE,MCX',
        mobile: '',
        brokeragePlanId: '',
        initialPassword: ''
      });
    } catch (error) {
      setActionError(error?.message || 'Failed to create user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteUser = async (targetUser) => {
    if (!targetUser) return;
    const confirmed = window.confirm(`Block user ${targetUser.username || targetUser.id}?`);
    if (!confirmed) return;
    setActionError(null);
    setActionLoading(true);
    try {
      await apiService.delete(`/admin/users/${targetUser.id}`);
      await loadUsers();
    } catch (error) {
      setActionError(error?.message || 'Failed to remove user');
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddFundsSubmit = async () => {
    if (!selectedUser) return;
    const amount = Number(addFundsForm.amount || 0);
    if (!amount || amount <= 0) {
      setActionError('Enter a valid amount');
      return;
    }
    setActionError(null);
    setActionLoading(true);
    try {
      const remarkParts = [];
      if (addFundsForm.method) {
        remarkParts.push(`Method: ${addFundsForm.method}`);
      }
      if (addFundsForm.remarks) {
        remarkParts.push(addFundsForm.remarks);
      }
      await apiService.post('/wallet/payin', {
        user_id: selectedUser.id,
        credit: amount,
        remarks: remarkParts.join(' | ') || 'Admin payin'
      });
      await loadUsers();
      setShowAddFundsModal(false);
      setSelectedUser(null);
      setAddFundsForm({ amount: '', method: '', remarks: '' });
    } catch (error) {
      setActionError(error?.message || 'Failed to add funds');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const config = {
      ACTIVE: { bg: 'bg-green-100', text: 'text-green-800', icon: CheckCircle },
      PENDING: { bg: 'bg-yellow-100', text: 'text-yellow-800', icon: Clock },
      INACTIVE: { bg: 'bg-red-100', text: 'text-red-800', icon: XCircle }
    };
    const { bg, text, icon: Icon } = config[status] || config.PENDING;
    return (
      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${bg} ${text}`}>
        <Icon className="w-3 h-3 mr-1" />
        {status}
      </span>
    );
  };

  const filteredUsers = users.filter(user => 
    user.id.toString().includes(searchTerm) ||
    user.firstName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.lastName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
    user.mobile.includes(searchTerm)
  );

  const paginatedUsers = filteredUsers.slice(0, showEntries);

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600">You do not have permission to access this page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="mx-auto w-full sm:w-11/12 px-1 sm:px-6 lg:px-8 py-6">
        <div className="bg-white shadow rounded-lg">
          {/* DataTable Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center space-x-2 mb-4 sm:mb-0">
                <label className="text-sm text-gray-700">Show</label>
                <select 
                  value={showEntries}
                  onChange={(e) => setShowEntries(parseInt(e.target.value))}
                  className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value="all">All</option>
                </select>
                <label className="text-sm text-gray-700">entries</label>
              </div>
              
              <div className="flex items-center space-x-2">
                <label className="text-sm text-gray-700">Search:</label>
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="border border-gray-300 rounded px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
            {isAdmin && (
              <div className="flex items-center justify-between mt-4">
                <div className="text-xs text-red-600">{actionError}</div>
                <button
                  onClick={() => setShowAddUserModal(true)}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded text-xs disabled:opacity-50"
                  disabled={actionLoading}
                >
                  Add User
                </button>
              </div>
            )}
          </div>

          {/* DataTable */}
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Id</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">First Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Last Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">User Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Created On</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Mobile</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Wallet Balance</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Margin Multiplier</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  {showEditColumn && (
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"></th>
                  )}
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"></th>
                  {showRemoveColumn && (
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"></th>
                  )}
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {/* Search input row */}
                <tr className="bg-gray-50">
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  <td className="px-6 py-2"><input type="text" className="w-full border border-gray-300 rounded px-2 py-1 text-xs" placeholder="Search" /></td>
                  {showEditColumn && <td className="px-6 py-2"></td>}
                  <td className="px-6 py-2"></td>
                  <td className="px-6 py-2"></td>
                  {showRemoveColumn && <td className="px-6 py-2"></td>}
                </tr>
                
                {/* Data rows */}
                {paginatedUsers.map((user) => (
                  <tr key={user.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.firstName}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.lastName}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.userType}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.email}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.createdOn}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.mobile}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{user.walletBalance}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{Number(user.marginMultiplier || 1).toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{getStatusBadge(user.status)}</td>
                    {showEditColumn && (
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button onClick={() => handleEdit(user)} className="bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-1 rounded text-xs">Edit</button>
                      </td>
                    )}
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <button onClick={() => handleAddFunds(user)} className="bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded text-xs">Add Funds</button>
                    </td>
                    {showRemoveColumn && (
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <button
                          onClick={() => handleDeleteUser(user)}
                          className="bg-red-600 hover:bg-red-700 text-white px-3 py-1 rounded text-xs disabled:opacity-50"
                          disabled={actionLoading}
                        >
                          Remove
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
                
                {paginatedUsers.length === 0 && (
                  <tr>
                    <td colSpan={showEditColumn || showRemoveColumn ? 13 : 11} className="px-6 py-4 text-center text-sm text-gray-500">No matching records found</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* DataTable Footer */}
          <div className="px-6 py-4 border-t border-gray-200">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-gray-700 mb-4 sm:mb-0">
                Showing 1 to {Math.min(showEntries, filteredUsers.length)} of {filteredUsers.length} entries
              </div>
              <div className="flex items-center space-x-2">
                <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50" disabled>First</button>
                <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50" disabled>Previous</button>
                <button className="px-3 py-1 text-sm bg-indigo-600 text-white rounded">1</button>
                <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50" disabled>Next</button>
                <button className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50" disabled>Last</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modals */}
      {showEditModal && selectedUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Edit User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">First Name</label>
                <input
                  type="text"
                  value={editForm?.firstName ?? ''}
                  onChange={(e) => handleEditChange('firstName', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Last Name</label>
                <input
                  type="text"
                  value={editForm?.lastName ?? ''}
                  onChange={(e) => handleEditChange('lastName', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={editForm?.email ?? ''}
                  onChange={(e) => handleEditChange('email', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <select
                  value={editForm?.role ?? 'USER'}
                  onChange={(e) => handleEditChange('role', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="USER">USER</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Wallet Balance</label>
                <input
                  type="number"
                  value={editForm?.walletBalance ?? '0'}
                  onChange={(e) => handleEditChange('walletBalance', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Margin Multiplier</label>
                <input
                  type="number"
                  value={editForm?.marginMultiplier ?? '1'}
                  onChange={(e) => handleEditChange('marginMultiplier', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  min="0"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <select
                  value={editForm?.status ?? 'PENDING'}
                  onChange={(e) => handleEditChange('status', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="PENDING">PENDING</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="BLOCKED">BLOCKED</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Allowed Segments</label>
                <input
                  type="text"
                  value={editForm?.allowedSegments ?? ''}
                  onChange={(e) => handleEditChange('allowedSegments', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Mobile Number (Login ID)</label>
                <input
                  type="text"
                  value={editForm?.mobile ?? ''}
                  onChange={(e) => handleEditChange('mobile', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Brokerage Plan</label>
                <select
                  value={editForm?.brokeragePlanId ?? ''}
                  onChange={(e) => handleEditChange('brokeragePlanId', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">Default</option>
                  {brokeragePlans.map((p) => (
                    <option key={p.id} value={p.id}>{p.name} (₹{p.flat_fee})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Initial Password</label>
                <input
                  type="password"
                  value={editForm?.initialPassword ?? ''}
                  onChange={(e) => handleEditChange('initialPassword', e.target.value)}
                  placeholder="Set initial password (optional)"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setSelectedUser(null);
                  setEditForm(null);
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button onClick={handleSaveEdit} className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50" disabled={actionLoading}>Save Changes</button>
            </div>
          </div>
        </div>
      )}

      {showAddUserModal && isAdmin && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add User</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">First Name</label>
                <input
                  type="text"
                  value={addForm.firstName}
                  onChange={(e) => handleAddUserChange('firstName', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Last Name</label>
                <input
                  type="text"
                  value={addForm.lastName}
                  onChange={(e) => handleAddUserChange('lastName', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={addForm.email}
                  onChange={(e) => handleAddUserChange('email', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Role</label>
                <select
                  value={addForm.role}
                  onChange={(e) => handleAddUserChange('role', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="USER">USER</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="SUPER_ADMIN">SUPER_ADMIN</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Status</label>
                <select
                  value={addForm.status}
                  onChange={(e) => handleAddUserChange('status', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="PENDING">PENDING</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="BLOCKED">BLOCKED</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Wallet Balance</label>
                <input
                  type="number"
                  value={addForm.walletBalance}
                  onChange={(e) => handleAddUserChange('walletBalance', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Margin Multiplier</label>
                <input
                  type="number"
                  value={addForm.marginMultiplier}
                  onChange={(e) => handleAddUserChange('marginMultiplier', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                  min="0"
                  step="0.1"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Allowed Segments</label>
                <input
                  type="text"
                  value={addForm.allowedSegments}
                  onChange={(e) => handleAddUserChange('allowedSegments', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Mobile Number (Login ID)</label>
                <input
                  type="text"
                  value={addForm.mobile}
                  onChange={(e) => handleAddUserChange('mobile', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Brokerage Plan</label>
                <select
                  value={addForm.brokeragePlanId}
                  onChange={(e) => handleAddUserChange('brokeragePlanId', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">Default</option>
                  {brokeragePlans.map((p) => (
                    <option key={p.id} value={p.id}>{p.name} (₹{p.flat_fee})</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Initial Password</label>
                <input
                  type="password"
                  value={addForm.initialPassword}
                  onChange={(e) => handleAddUserChange('initialPassword', e.target.value)}
                  placeholder="Set initial password (optional)"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowAddUserModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateUser}
                className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                disabled={actionLoading}
              >
                Create User
              </button>
            </div>
          </div>
        </div>
      )}

      {showAddFundsModal && selectedUser && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Add Funds</h3>
            <div className="space-y-4">
              <div><label className="block text-sm font-medium text-gray-700">User</label><input type="text" value={`${selectedUser.firstName} ${selectedUser.lastName}`} className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm" readOnly /></div>
              <div><label className="block text-sm font-medium text-gray-700">Current Balance</label><input type="text" value={selectedUser.walletBalance} className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm" readOnly /></div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Amount to Add</label>
                <input
                  type="number"
                  value={addFundsForm.amount}
                  onChange={(e) => handleAddFundsChange('amount', e.target.value)}
                  placeholder="Enter amount"
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Payment Method</label>
                <select
                  value={addFundsForm.method}
                  onChange={(e) => handleAddFundsChange('method', e.target.value)}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                >
                  <option value="">Select payment method</option>
                  <option value="bank_transfer">Bank Transfer</option>
                  <option value="upi">UPI</option>
                  <option value="cash">Cash</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Remarks</label>
                <textarea
                  rows="3"
                  value={addFundsForm.remarks}
                  onChange={(e) => handleAddFundsChange('remarks', e.target.value)}
                  placeholder="Add any remarks..."
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            <div className="flex justify-end space-x-3 mt-6">
              <button onClick={() => setShowAddFundsModal(false)} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200">Cancel</button>
              <button onClick={handleAddFundsSubmit} className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50" disabled={actionLoading}>Add Funds</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Users;
