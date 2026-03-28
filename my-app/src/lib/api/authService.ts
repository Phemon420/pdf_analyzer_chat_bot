import { AuthResponse, LoginCredentials, SignUpCredentials, GoogleStatus } from '../types/auth';

const TOKEN_KEY = 'auth_token';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ;

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    try {
      console.log('API_BASE_URL:', API_BASE_URL);
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });

      const data = await response.json();

      if (response.ok && data.status === 1) {
        if (typeof window !== 'undefined') {
          localStorage.setItem(TOKEN_KEY, data.Token);
        }
        return { success: true, token: data.Token };
      }

      return { success: false, message: data.detail || 'Login failed' };
    } catch (error) {
      return { success: false, message:`Network error occurred: ${error}` };
    }
  },

  async signup(credentials: SignUpCredentials): Promise<AuthResponse> {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: credentials.username,
            password: credentials.password
        }),
      });

      const data = await response.json();

      if (response.ok && data.status === 1) {
        if (typeof window !== 'undefined') {
          localStorage.setItem(TOKEN_KEY, data.Token);
        }
        return { success: true, token: data.Token };
      }

      return { success: false, message: data.detail || 'Signup failed' };
    } catch (error) {
      return { success: false, message: `Network error occurred: ${error}` };
    }
  },

  async fetchMe(): Promise<{ user: { id: string; username: string } | null; google: GoogleStatus | null; error?: string }> {
    const token = this.getToken();
    if (!token) return { user: null, google: null };

    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.status === 401) {
        return { user: null, google: null, error: 'UNAUTHORIZED' };
      }

      const data = await response.json();

      if (response.ok && data.status === 1) {
        return {
          user: data.user,
          google: data.google || { connected: false },
        };
      }

      return { user: null, google: null, error: 'SERVER_ERROR' };
    } catch (error) {
      console.error('fetchMe failed:', error);
      return { user: null, google: null, error: 'NETWORK_ERROR' };
    }
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