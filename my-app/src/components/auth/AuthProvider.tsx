'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, AuthResponse, GoogleStatus } from '../../lib/types/auth';
import { authService } from '../../lib/api/authService';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (username: string, password?: string) => Promise<AuthResponse>;
  signup: (username: string, password?: string, confirmPassword?: string) => Promise<AuthResponse>;
  logout: () => void;
  isAuthenticated: boolean;
  googleStatus: GoogleStatus | null;
  refreshGoogleStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus | null>(null);

  const hydrateFromMe = useCallback(async () => {
    const meData = await authService.fetchMe();
    if (meData.user) {
      setUser({
        id: String(meData.user.id),
        username: meData.user.username,
        name: meData.user.username,
      });
      setIsAuthenticated(true);
      setGoogleStatus(meData.google || { connected: false });
    } else {
      authService.logout();
      setUser(null);
      setIsAuthenticated(false);
      setGoogleStatus(null);
    }
  }, []);

  useEffect(() => {
    const token = authService.getToken();
    if (token) {
      hydrateFromMe().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [hydrateFromMe]);

  const refreshGoogleStatus = useCallback(async () => {
    const meData = await authService.fetchMe();
    if (meData.google) {
      setGoogleStatus(meData.google);
    }
  }, []);

  const login = async (username: string, password?: string): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authService.login({ username, password });
      if (response.success) {
        await hydrateFromMe();
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
      if (response.success) {
        await hydrateFromMe();
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
    setGoogleStatus(null);
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout, isAuthenticated, googleStatus, refreshGoogleStatus }}>
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
