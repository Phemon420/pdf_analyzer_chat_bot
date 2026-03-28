export interface User {
  id: string;
  username: string;
  name: string;
  avatar?: string;
}

export interface GoogleStatus {
  connected: boolean;
  email?: string;
  name?: string;
  picture?: string;
  expires_at?: string;
  scopes?: string[];
}

export interface AuthResponse {
  success: boolean;
  token?: string;
  user?: User;
  message?: string;
}

export interface LoginCredentials {
  username: string;
  password?: string;
}

export interface SignUpCredentials extends LoginCredentials {
  confirmPassword?: string;
}
