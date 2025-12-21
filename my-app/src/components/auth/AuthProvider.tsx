'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { User, AuthResponse } from '../../lib/types/auth';
import { authService } from '../../lib/api/authService';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password?: string) => Promise<AuthResponse>;
  signup: (username: string, password?: string, confirmPassword?: string) => Promise<AuthResponse>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false); // Used for initial load check if needed, or login process
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    // Check for existing token on mount
    const token = authService.getToken();
    if (token) {
      setIsAuthenticated(true);
      // In a real app, you might fetch the user profile here using the token
      // For now, we just restore a dummy user state if a token exists
      setUser({ id: '1', username: 'User', name: 'Returning User' }); 
    }
  }, []);

  const login = async (username: string, password?: string): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authService.login({ username, password });
      if (response.success && response.user) {
        setUser(response.user);
        setIsAuthenticated(true);
      }
      return response;
    } catch (error) {
      return { success: false, message: `An unexpected error occurred ${error}.` };
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (username: string, password?: string, confirmPassword?: string): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authService.signup({ username, password, confirmPassword });
      if (response.success && response.user) {
        setUser(response.user);
        setIsAuthenticated(true);
      }
      return response;
    } catch (error) {
      return { success: false, message: `An unexpected error occurred ${error}.` };
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    authService.logout();
    setUser(null);
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
