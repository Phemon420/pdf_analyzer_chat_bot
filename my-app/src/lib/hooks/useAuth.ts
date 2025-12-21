import { useAuthContext } from '../../components/auth/AuthProvider';

// Re-exporting for easier import paths or abstraction
export function useAuth() {
  return useAuthContext();
}
