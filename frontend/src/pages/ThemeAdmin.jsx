import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import ThemeCustomizer from '../components/theme/ThemeCustomizer';

const ThemeAdmin = () => {
  const { user } = useAuth();
  if (!user || (user.role !== 'ADMIN' && user.role !== 'SUPER_ADMIN')) {
    return <div className="p-8 text-center text-red-600 font-bold">Access denied: Admins only</div>;
  }
  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-6 text-gray-900">Theme Management</h1>
        <ThemeCustomizer />
      </div>
    </div>
  );
};

export default ThemeAdmin;
