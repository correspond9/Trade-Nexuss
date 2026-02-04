// Simple Authentication Service
class AuthService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';
    this.cache = new Map();
  }

  async login(email, password) {
    try {
      const response = await fetch(`${this.baseURL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password
        })
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      
      // Store token in localStorage
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));
      
      return {
        success: true,
        user: data.user,
        token: data.access_token
      };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async logout() {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        await fetch(`${this.baseURL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
          }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage
      localStorage.removeItem('token');
      localStorage.removeItem('user');
    }
  }

  getCurrentUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  getToken() {
    return localStorage.getItem('token');
  }

  isAuthenticated() {
    return !!this.getToken();
  }

  // For backwards compatibility with existing code
  getMockUsers() {
    return [
      {
        id: 'admin-1',
        email: 'admin@example.com',
        password: 'admin123',
        name: 'Super Admin',
        role: 'SUPER_ADMIN',
        clientID: 'U0000',
        permissions: {
          access_nse_equity: true,
          access_bse_equity: true,
          access_nse_derivatives: true,
          access_bse_derivatives: true,
          access_mcx_commodities: true
        }
      },
      {
        id: 'user-1',
        email: 'ck.nanaiah@example.com',
        password: 'password123',
        name: 'C.K. Nanaiah',
        role: 'ADMIN',
        clientID: 'U1001',
        permissions: {
          access_nse_equity: true,
          access_bse_equity: true,
          access_nse_derivatives: true,
          access_bse_derivatives: true,
          access_mcx_commodities: true
        }
      },
      {
        id: 'user-2',
        email: 'dhruv@example.com',
        password: 'password123',
        name: 'Dhruv Gohil',
        role: 'USER_EQUITY',
        clientID: 'U1002',
        permissions: {
          access_nse_equity: true,
          access_bse_equity: true,
          access_nse_derivatives: false,
          access_bse_derivatives: false,
          access_mcx_commodities: false
        }
      },
      {
        id: 'user-3',
        email: 'equity_derivatives@example.com',
        password: 'password123',
        name: 'Rajesh Kumar',
        role: 'USER_EQUITY_DERIVATIVES',
        clientID: 'U1003',
        permissions: {
          access_nse_equity: true,
          access_bse_equity: true,
          access_nse_derivatives: true,
          access_bse_derivatives: true,
          access_mcx_commodities: false
        }
      },
      {
        id: 'user-4',
        email: 'commodity@example.com',
        password: 'password123',
        name: 'Amit Patel',
        role: 'USER_COMMODITY',
        clientID: 'U1004',
        permissions: {
          access_nse_equity: false,
          access_bse_equity: false,
          access_nse_derivatives: false,
          access_bse_derivatives: false,
          access_mcx_commodities: true
        }
      }
    ];
  }

  // Mock authentication for testing
  async mockLogin(email, password) {
    const users = this.getMockUsers();
    const user = users.find(u => u.email === email && u.password === password);
    
    if (user) {
      const mockToken = `mock-token-${Date.now()}`;
      localStorage.setItem('token', mockToken);
      localStorage.setItem('user', JSON.stringify(user));
      return {
        success: true,
        user: user,
        token: mockToken
      };
    }
    
    return {
      success: false,
      error: 'Invalid credentials'
    };
  }
}

// Export singleton instance
const authService = new AuthService();
export { authService };
