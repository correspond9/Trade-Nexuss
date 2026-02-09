import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import ThemeSelector from './ThemeSelector';

const Header = () => {
  const { user, logout, hasRole } = useAuth();
  const location = useLocation();

  const navigationItems = [
    { name: 'Trade', path: '/trade', icon: '💹' },
    { name: 'Commodities', path: '/commodities', icon: '🛢️' },
    { name: 'P. MIS', path: '/trade/all-positions', icon: '📊', adminOnly: true },
    { name: 'P. Normal', path: '/trade/all-positions-normal', icon: '📈', adminOnly: true },
    { name: 'P.Userwise', path: '/trade/all-positions-userwise', icon: '👥', adminOnly: true },
    { name: 'Users', path: '/users', icon: '👤', adminOnly: true },
    { name: 'Payouts', path: '/payouts', icon: '💰', adminOnly: true },
    { name: 'Ledger', path: '/ledger', icon: '📋', adminOnly: true },
    { name: 'P&L', path: '/trade/pandl', icon: '📊', adminOnly: true },
    { name: 'Dashboard', path: '/dashboard', icon: '⚙️', superAdminOnly: true },
  ];

  const filteredItems = navigationItems.filter(item => {
    console.log('🔍 Checking item:', item.name, 'superAdminOnly:', item.superAdminOnly, 'adminOnly:', item.adminOnly);
    console.log('🔍 User hasRole SUPER_ADMIN:', hasRole('SUPER_ADMIN'));
    console.log('🔍 User hasRole ADMIN:', hasRole('ADMIN'));
    console.log('🔍 Current user:', user);
    
    if (item.superAdminOnly && !hasRole('SUPER_ADMIN')) {
      console.log('❌ Filtered out (superAdminOnly):', item.name);
      return false;
    }
    if (item.adminOnly && !hasRole('ADMIN') && !hasRole('SUPER_ADMIN')) {
      console.log('❌ Filtered out (adminOnly):', item.name);
      return false;
    }
    console.log('✅ Allowed:', item.name);
    return true;
  });
  
  console.log('🔍 Final filtered items:', filteredItems.map(item => item.name));

  return (
    <header className="bg-white shadow-md sticky top-0 z-50 border-b border-gray-200">
      <div className="max-w-[1920px] mx-auto px-4">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center">
            <Link to={(hasRole('ADMIN') || hasRole('SUPER_ADMIN')) ? '/dashboard' : '/options'} className="flex items-center">
              <img 
                src="/logo.png" 
                alt="straddly.com" 
                className="h-8 w-auto"
              />
            </Link>
          </div>

          {/* Navigation - Horizontal Bar */}
          <nav className="hidden md:flex space-x-6 flex-1 justify-center">
            {filteredItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-3 py-2 text-sm font-medium transition-colors hover:text-blue-600 ${
                  location.pathname === item.path
                    ? 'text-blue-600 border-b-2 border-blue-600'
                    : 'text-gray-700'
                }`}
              >
                {item.name}
              </Link>
            ))}
          </nav>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            <div className="text-right hidden sm:block">
              <div className="text-sm text-gray-900 font-medium">
                {user?.firstName} {user?.lastName}
              </div>
              <div className="text-xs text-gray-500">
                Mobile: {user?.mobile || '-'}
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Link
                to="/profile"
                className="text-gray-500 hover:text-gray-700 p-2 rounded-lg hover:bg-gray-100 transition-colors"
                title="Profile"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </Link>
              
              <button
                onClick={logout}
                className="px-3 py-1 bg-red-500 hover:bg-red-600 text-white text-xs font-medium rounded transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
