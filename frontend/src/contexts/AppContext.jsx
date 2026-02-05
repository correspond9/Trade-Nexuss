import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiService } from '../services/apiService';
import { useAuth } from './AuthContext';

const AppContext = createContext();

export const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
};

export const AppProvider = ({ children }) => {
  const { isAuthenticated, user } = useAuth();
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [baskets, setBaskets] = useState([]);
  const [positions, setPositions] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Integration settings
  const [integrationSettings, setIntegrationSettings] = useState({
    provider: 'Dhan',
    authMethod: 'apikey', // 'token' or 'apikey'
    accessToken: '',
    clientId: '',
    apiKey: '',
  });

  // Load initial data only when authenticated
  useEffect(() => {
    const loadInitialData = async () => {
      // Only load data if user is authenticated
      if (!isAuthenticated) {
        console.log(' User not authenticated, skipping data load');
        return;
      }
      
      setLoading(true);
      try {
        console.log(' Production mode: Using real API data');
        
        // Simplified - only load essential data
        const usersRes = await apiService.get('/admin/users').catch(() => null);
        
        if (usersRes?.data) setUsers(usersRes.data);
        
      } catch (err) {
        console.error('Failed to load initial data:', err);
        console.log(' API data loading failed, but continuing...');
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, [isAuthenticated]);

  // User management
  const createUser = useCallback(async (userData) => {
    try {
      const response = await apiService.post('/admin/users', userData);
      const newUser = response?.data || response;
      setUsers(prev => [...prev, newUser]);
      return { success: true, data: newUser };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  const updateUser = useCallback(async (userId, userData) => {
    try {
      const response = await apiService.put(`/admin/users/${userId}`, userData);
      const updatedUser = response?.data || response;
      setUsers(prev => prev.map(user => 
        user.id === userId ? updatedUser : user
      ));
      return { success: true, data: updatedUser };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  const deleteUser = useCallback(async (userId) => {
    try {
      await apiService.delete(`/admin/users/${userId}`);
      setUsers(prev => prev.filter(user => user.id !== userId));
      return { success: true };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  // Order management
  const createOrder = useCallback(async (orderData) => {
    try {
      const response = await apiService.post('/trading/orders', orderData);
      const newOrder = response?.data || response;
      setOrders(prev => [...prev, newOrder]);
      return { success: true, data: newOrder };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  const updateOrder = useCallback(async (orderId, orderData) => {
    try {
      const updatedOrder = await apiService.put(`/orders/${orderId}`, orderData);
      setOrders(prev => prev.map(order => 
        order.id === orderId ? updatedOrder : order
      ));
      return { success: true, data: updatedOrder };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  // Position management
  const closePosition = useCallback(async (positionId) => {
    try {
      const response = await apiService.post(`/positions/${positionId}/close`);
      const closedPosition = response?.data || response;
      setPositions(prev => prev.map(position => 
        position.id === positionId ? { ...position, ...closedPosition } : position
      ));
      return { success: true, data: closedPosition };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  // Basket management
  const createBasket = useCallback(async (basketData) => {
    try {
      const response = await apiService.post('/trading/basket-orders', basketData);
      const newBasket = response?.data || response;
      setBaskets(prev => [...prev, newBasket]);
      return { success: true, data: newBasket };
    } catch (err) {
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  // Integration settings
  const updateIntegrationSettings = useCallback(async (settings) => {
    try {
      // Save to backend
      const response = await apiService.post('/credentials/save', settings);
      
      if (response.success) {
        setIntegrationSettings(settings);
        return { 
          success: true, 
          message: 'API keys saved successfully',
          connectionTest: response.connectionTest 
        };
      } else {
        throw new Error(response.message || 'Failed to save API keys');
      }
    } catch (err) {
      console.error('Error saving integration settings:', err);
      setError(err.message);
      return { success: false, message: err.message };
    }
  }, []);

  // Clear error
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = {
    // Data
    users,
    orders,
    baskets,
    positions,
    payouts,
    integrationSettings,
    
    // State
    loading,
    error,
    
    // User actions
    createUser,
    updateUser,
    deleteUser,
    
    // Order actions
    createOrder,
    updateOrder,
    
    // Position actions
    closePosition,
    
    // Basket actions
    createBasket,
    
    // Settings
    updateIntegrationSettings,
    
    // Utilities
    clearError,
  };

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  );
};

export default AppContext;