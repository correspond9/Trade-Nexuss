import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { apiService } from '../services/apiService';
import { authService } from '../services/authService';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const initialized = useRef(false);

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        console.log('🔐 AuthContext initialization started');
        
        const storedToken = localStorage.getItem('authToken');
        const storedUser = localStorage.getItem('authUser');
        
        console.log('🔐 Found in localStorage:', {
          token: storedToken ? storedToken.substring(0, 20) + '...' : null,
          user: storedUser
        });
        
        if (storedToken && storedUser) {
          // Use stored user data instead of re-validating with backend
          apiService.setAuthToken(storedToken);
          const userData = JSON.parse(storedUser);
          
          if (userData) {
            setUser(userData);
            setToken(storedToken);
            console.log('🔐 AuthContext initialized with stored data');
          } else {
            // Data invalid, clear it
            console.log('🔐 Stored data invalid, clearing');
            clearAuth();
          }
        } else {
          console.log('🔐 No stored auth data found');
        }
      } catch (err) {
        console.error('Auth initialization failed:', err);
        clearAuth();
      } finally {
        setLoading(false);
        console.log('🔐 AuthContext initialization completed');
      }
    };

    initAuth();
  }, []);

  // Clear auth data
  const clearAuth = useCallback(() => {
    setUser(null);
    setToken(null);
    setError(null);
    initialized.current = false;  // Reset initialization flag
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    apiService.setAuthToken(null);
  }, []);

  // Login function with JWT
  const login = useCallback(async (username, password) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('🔐 Attempting login with:', { username, password: '***' });
      
      const response = await authService.login(username, password);
      
      console.log('🔐 Login response:', response);

      if (response && response.success && (response.access_token || response.token)) {
        // Handle both response formats
        const access_token = response.access_token || response.token;
        
        // Extract user data correctly - response.user contains the actual user object
        let userData = response.user;
        
        console.log('🔐 Extracted token:', access_token.substring(0, 20) + '...');
        console.log('🔐 Extracted user:', userData);
        console.log('🔐 User role:', userData?.role);
        
        // Store token and user
        setToken(access_token);
        setUser(userData);
        
        // Update apiService with the new token
        apiService.setAuthToken(access_token);
        
        // Store in localStorage for persistence
        console.log('🔐 Before localStorage set:', {
          token: localStorage.getItem('authToken'),
          user: localStorage.getItem('authUser')
        });
        
        localStorage.setItem('authToken', access_token);
        localStorage.setItem('authUser', JSON.stringify(userData));
        
        console.log('🔐 After localStorage set:', {
          token: localStorage.getItem('authToken'),
          user: localStorage.getItem('authUser')
        });
        
        console.log('🔐 Stored in localStorage');
        console.log('🔐 Login successful, returning success');
        
        return { success: true, user: userData };
      } else {
        console.error('🔐 Invalid login response:', response);
        throw new Error('Invalid login response');
      }
    } catch (err) {
      const errorMessage = err.message || 'Login failed';
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  }, []);

  // Logout function
  const logout = useCallback(async () => {
    try {
      // Call logout endpoint if available
      if (token) {
        await apiService.post('/auth/logout');
      }
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clear local state regardless of API call success
      clearAuth();
    }
  }, [token, clearAuth]);

  // Check if user is authenticated - simplified to prevent infinite loops
  const isAuthenticated = !!(user && token);

  // Check user role
  const hasRole = useCallback((role) => {
    return user?.role === role;
  }, [user]);

  // Check user permission
  const hasPermission = useCallback((permission) => {
    return user?.permissions?.[permission] === true;
  }, [user]);

  const value = {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    clearAuth,
    hasRole,
    hasPermission,
    setError
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
