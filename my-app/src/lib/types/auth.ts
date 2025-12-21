export interface User {
  id: string;
  username: string;
  name: string;
  avatar?: string;
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
