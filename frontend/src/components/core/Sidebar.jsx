import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();

  const sidebarItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Trade', path: '/trade', icon: '💹' },
    { name: 'Commodities', path: '/commodities', icon: '🛢️' },
    { name: 'Users', path: '/users', icon: '👥' },
    { name: 'Userwise', path: '/userwise', icon: '📈' },
    { name: 'Payouts', path: '/payouts', icon: '💰' },
    { name: 'Ledger', path: '/ledger', icon: '📋' },
  ];

  return (
    <aside className="w-64 bg-gray-800 shadow-lg hidden md:block">
      <div className="p-4">
        <nav className="space-y-2">
          {sidebarItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                location.pathname === item.path
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
            >
              <span className="text-xl">{item.icon}</span>
              <span className="font-medium">{item.name}</span>
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
};

export default Sidebar;