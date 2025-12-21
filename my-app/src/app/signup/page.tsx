import { SignUpForm } from '../../components/auth/SignUpForm';
import { AuthProvider } from '../../components/auth/AuthProvider';

export default function SignUpPage() {
  return (
    <AuthProvider>
        <SignUpForm />
    </AuthProvider>
  );
}
