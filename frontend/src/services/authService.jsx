// Simple Authentication Service
class AuthService {
  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || 'http://72.62.228.112:8010';
    this.cache = new Map();
  }

  async login(mobile, password) {
    try {
      const response = await fetch(`${this.baseURL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mobile: mobile,
          password: password
        })
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();
      const token = data.access_token || data.token;
      const user = data.user || data;

      if (!token || !user) {
        throw new Error('Invalid login response');
      }

      // Store token in localStorage
      localStorage.setItem('token', token);
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('authToken', token);
      localStorage.setItem('authUser', JSON.stringify(user));

      return {
        success: true,
        user,
        token,
        access_token: token
      };
    } catch (error) {
      console.error('Login error:', error);
      return {
        success: false,
        error: error.message || 'Login failed'
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
  async mockLogin(emailOrUsername, password) {
    const users = this.getMockUsers();
    const input = (emailOrUsername || '').trim().toLowerCase();

    const user = users.find(u => {
      const emailMatch = u.email?.toLowerCase() === input;
      const nameMatch = u.name?.toLowerCase().replace(/\s+/g, '') === input.replace(/\s+/g, '');
      const clientMatch = u.clientID?.toLowerCase() === input;
      return (emailMatch || nameMatch || clientMatch) && u.password === password;
    });
    
    if (user) {
      const mockToken = `mock-token-${Date.now()}`;
      localStorage.setItem('token', mockToken);
      localStorage.setItem('user', JSON.stringify(user));
      localStorage.setItem('authToken', mockToken);
      localStorage.setItem('authUser', JSON.stringify(user));
      return {
        success: true,
        user: user,
        token: mockToken,
        access_token: mockToken
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
