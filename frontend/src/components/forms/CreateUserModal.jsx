import React, { useState } from 'react';

const CreateUserModal = ({ isOpen, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    mobile: '',
    pan: '',
    aadhar: '',
    bank: '',
    allocatedMargin: '',
    profit: '',
    sl: '',
  });

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
    onClose();
  };

  const handleChange = (e) => {
    setFormData(prev => ({
      ...prev,
      [e.target.name]: e.target.value
    }));
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex justify-center items-center z-60 p-4 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b flex justify-between items-center bg-indigo-600 text-white rounded-t-2xl">
          <h2 className="text-xl font-bold">Create New Client Account</h2>
          <button
            onClick={onClose}
            className="hover:rotate-90 transition-transform"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="First Name"
            name="firstName"
            value={formData.firstName}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Last Name"
            name="lastName"
            value={formData.lastName}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Email Address"
            type="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Mobile Number"
            name="mobile"
            value={formData.mobile}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="PAN Number"
            name="pan"
            value={formData.pan}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Aadhar Number"
            name="aadhar"
            value={formData.aadhar}
            onChange={handleChange}
            required
          />
          <input
            className="p-2 border rounded placeholder:text-sm col-span-full"
            placeholder="Bank Account / IFSC"
            name="bank"
            value={formData.bank}
            onChange={handleChange}
            required
          />

          <div className="col-span-full border-t pt-4 mt-2">
            <h3 className="font-semibold text-gray-700 mb-2">Trading Configuration</h3>
          </div>

          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Allocated Margin"
            type="number"
            name="allocatedMargin"
            value={formData.allocatedMargin}
            onChange={handleChange}
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Target Profit"
            type="number"
            name="profit"
            value={formData.profit}
            onChange={handleChange}
          />
          <input
            className="p-2 border rounded placeholder:text-sm"
            placeholder="Stop Loss"
            type="number"
            name="sl"
            value={formData.sl}
            onChange={handleChange}
          />

          <div className="col-span-full flex justify-end space-x-3 mt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-gray-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-indigo-600 text-white rounded-lg font-bold shadow-lg"
            >
              Create Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateUserModal;