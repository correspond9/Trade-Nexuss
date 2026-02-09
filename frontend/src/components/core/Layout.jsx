import React from 'react';
import { Outlet } from 'react-router-dom';
import Header from './Header';

const Layout = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-[1920px] mx-auto px-4 py-6">
        {children || <Outlet />}
      </main>
    </div>
  );
};

export default Layout;
