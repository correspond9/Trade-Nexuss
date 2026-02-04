// src/components/MarketHolidays.jsx

import React, { useState, useEffect } from 'react';
import { authService } from '../services/authService';

const MarketHolidays = () => {
  const [holidays, setHolidays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());
  const [formData, setFormData] = useState({
    date: '',
    description: '',
    holiday_type: 'TRADING_HOLIDAY',
    closed_exchanges: []
  });

  const exchanges = ['NSE', 'BSE', 'NFO', 'BFO', 'BCD', 'CDS', 'MCX'];
  const years = Array.from({ length: 5 }, (_, i) => new Date().getFullYear() + i - 2);

  useEffect(() => {
    if (!authService.isAdmin()) {
      window.location.href = '/user-dashboard';
      return;
    }
    fetchHolidays();
  }, [selectedYear]);

  const fetchHolidays = async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://127.0.0.1:5000/admin/api/holidays?year=${selectedYear}`, {
        headers: authService.getAuthHeaders(),
      });
      
      if (!response.ok) throw new Error('Failed to fetch data');
      
      const result = await response.json();
      if (result.success) {
        setHolidays(result.data);
      } else {
        setError(result.error || 'Failed to load data');
      }
    } catch (err) {
      setError('Failed to load market holidays');
      console.error('Fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch('http://127.0.0.1:5000/admin/api/holidays', {
        method: 'POST',
        headers: {
          ...authService.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Operation failed');
      }

      const result = await response.json();
      if (result.success) {
        await fetchHolidays();
        resetForm();
        alert(result.message);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err.message);
      console.error('Submit error:', err);
    }
  };

  const handleDelete = async (id, description) => {
    if (!confirm(`Are you sure you want to delete holiday: ${description}?`)) return;

    try {
      const response = await fetch(`http://127.0.0.1:5000/admin/api/holidays/${id}`, {
        method: 'DELETE',
        headers: authService.getAuthHeaders(),
      });

      if (!response.ok) throw new Error('Failed to delete');

      const result = await response.json();
      if (result.success) {
        await fetchHolidays();
        alert(result.message);
      } else {
        setError(result.error);
      }
    } catch (err) {
      setError(err.message);
      console.error('Delete error:', err);
    }
  };

  const handleExchangeToggle = (exchange) => {
    setFormData(prev => ({
      ...prev,
      closed_exchanges: prev.closed_exchanges.includes(exchange)
        ? prev.closed_exchanges.filter(e => e !== exchange)
        : [...prev.closed_exchanges, exchange]
    }));
  };

  const resetForm = () => {
    setFormData({
      date: '',
      description: '',
      holiday_type: 'TRADING_HOLIDAY',
      closed_exchanges: []
    });
    setShowAddForm(false);
    setError('');
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Market Holidays</h1>
              <p className="text-gray-600 mt-1">Manage trading holidays and exchange closures</p>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => window.history.back()}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Back
              </button>
              <button
                onClick={() => authService.logout()}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
            <button onClick={() => setError('')} className="ml-4 text-red-500 hover:text-red-700">×</button>
          </div>
        )}

        {/* Year Selector */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Select Year</h2>
              <select
                value={selectedYear}
                onChange={(e) => setSelectedYear(parseInt(e.target.value))}
                className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {years.map(year => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Add Holiday Form */}
        {showAddForm && (
          <div className="bg-white rounded-lg shadow mb-6">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900">Add New Holiday</h2>
            </div>
            <div className="p-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Date
                    </label>
                    <input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData({...formData, date: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Holiday Type
                    </label>
                    <select
                      value={formData.holiday_type}
                      onChange={(e) => setFormData({...formData, holiday_type: e.target.value})}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="TRADING_HOLIDAY">Trading Holiday</option>
                      <option value="SETTLEMENT_HOLIDAY">Settlement Holiday</option>
                      <option value="CLEARING_HOLIDAY">Clearing Holiday</option>
                    </select>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Description
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => setFormData({...formData, description: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    placeholder="Holiday description"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Closed Exchanges
                  </label>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    {exchanges.map(exchange => (
                      <label key={exchange} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={formData.closed_exchanges.includes(exchange)}
                          onChange={() => handleExchangeToggle(exchange)}
                          className="mr-2"
                        />
                        <span className="text-sm">{exchange}</span>
                      </label>
                    ))}
                  </div>
                </div>
                <div className="flex space-x-4">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                  >
                    Add Holiday
                  </button>
                  <button
                    type="button"
                    onClick={resetForm}
                    className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Add Button */}
        {!showAddForm && (
          <div className="mb-6">
            <button
              onClick={() => setShowAddForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Add New Holiday
            </button>
          </div>
        )}

        {/* Holidays Table */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">
              Holidays - {selectedYear} ({holidays.length})
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Day
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Closed Exchanges
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {holidays.map((holiday) => (
                  <tr key={holiday.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {holiday.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {holiday.day_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {holiday.description}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                        {holiday.holiday_type.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {holiday.closed_exchanges.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {holiday.closed_exchanges.map(exchange => (
                            <span key={exchange} className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                              {exchange}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-gray-400">None</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <button
                        onClick={() => handleDelete(holiday.id, holiday.description)}
                        className="text-red-600 hover:text-red-900"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {holidays.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                No holidays found for {selectedYear}. Add one to get started.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketHolidays;
