import { LoginForm } from '../../components/auth/LoginForm';
import { AuthProvider } from '../../components/auth/AuthProvider';

export default function LoginPage() {
  return (
    <AuthProvider>
        <LoginForm />
    </AuthProvider>
  );
}
