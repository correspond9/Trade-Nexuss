import React, { useState } from 'react';

const AddFundsModal = ({ isOpen, onClose, user, onSave }) => {
  const [amount, setAmount] = useState('');

  if (!isOpen || !user) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(parseFloat(amount));
    setAmount('');
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex justify-center items-center z-60">
      <div className="bg-white p-6 rounded-xl shadow-2xl w-80 border-2 border-amber-800">
        <h3 className="text-lg font-bold mb-4 text-gray-800">
          Add Funds – {user.firstName}
        </h3>

        <div className="space-y-4">
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">
              Current Balance
            </label>
            <div className="text-xl font-mono">
              {user.walletBalance.toFixed(2)}
            </div>
          </div>

          <form onSubmit={handleSubmit}>
            <input
              type="number"
              className="w-full p-3 border-2 border-gray-200 rounded-lg focus:border-indigo-500 outline-none placeholder:text-sm"
              placeholder="Enter Amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
              step="0.01"
              min="0"
            />

            <div className="flex space-x-2 mt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 bg-gray-100 rounded-lg text-sm"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2 bg-indigo-600 text-white rounded-lg text-sm font-bold"
              >
                Add Funds
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AddFundsModal;