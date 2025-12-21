import { AuthResponse, LoginCredentials, SignUpCredentials, User } from '../types/auth';

const TOKEN_KEY = 'auth_token';

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // Mock validation
    if (credentials.username && credentials.password) {
      // Success
      const mockToken = `mock-jwt-token-${Date.now()}`;
      const mockUser: User = {
        id: '1',
        username: credentials.username,
        name: credentials.username.charAt(0).toUpperCase() + credentials.username.slice(1),
        avatar: undefined,
      };

      // Store token
      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, mockToken);
      }

      return {
        success: true,
        token: mockToken,
        user: mockUser,
      };
    } else {
      return {
        success: false,
        message: 'Invalid username or password',
      };
    }
  },

  async signup(credentials: SignUpCredentials): Promise<AuthResponse> {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    if (!credentials.username || !credentials.password) {
        return { success: false, message: 'Username and password are required' };
    }

    if (credentials.password !== credentials.confirmPassword) {
        return { success: false, message: 'Passwords do not match' };
    }

    // Success (Mock)
    const mockToken = `mock-jwt-token-${Date.now()}`;
    const mockUser: User = {
      id: Date.now().toString(),
      username: credentials.username,
      name: credentials.username.charAt(0).toUpperCase() + credentials.username.slice(1),
    };

    // Store token
    if (typeof window !== 'undefined') {
      localStorage.setItem(TOKEN_KEY, mockToken);
    }

    return {
      success: true,
      token: mockToken,
      user: mockUser,
    };
  },

  logout() {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(TOKEN_KEY);
    }
  },

  getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(TOKEN_KEY);
    }
    return null;
  },

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
};
