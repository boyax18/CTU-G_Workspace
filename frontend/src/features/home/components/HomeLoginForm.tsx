import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../../components/common/Button';
import Input from '../../../components/common/Input';
import Reveal from '../../../components/common/Reveal';
import { EyeIcon, EyeOffIcon } from '../../../components/common/Icons';
import { REGISTER_PATH } from '../../../utils/constants';
import { GLASS } from '../../../utils/styles';

export interface LoginCredentials {
  schoolId: string;
  password: string;
}

interface HomeLoginFormProps {
  /**
   * Called with validated credentials. Not provided yet: connect this to
   * authService (Django REST API) in the authentication phase.
   */
  onSubmit?: (credentials: LoginCredentials) => Promise<void>;
}

interface FormErrors {
  schoolId?: string;
  password?: string;
}

export default function HomeLoginForm({ onSubmit }: HomeLoginFormProps) {
  const [schoolId, setSchoolId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const submitting = useRef(false);

  const validate = (): FormErrors => {
    const next: FormErrors = {};
    if (!schoolId.trim()) next.schoolId = 'Please enter your School ID.';
    if (!password) next.password = 'Please enter your password.';
    return next;
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting.current) return;

    const found = validate();
    setErrors(found);
    setNotice('');
    if (Object.keys(found).length > 0) return;

    if (!onSubmit) {
      setNotice('Sign-in is not available yet. This form will be connected in a later phase.');
      return;
    }

    submitting.current = true;
    setLoading(true);
    try {
      await onSubmit({ schoolId: schoolId.trim(), password });
    } catch {
      setNotice('Sign-in could not be completed. Please try again.');
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  return (
    <Reveal id="login" direction="right" delay={200} className={`w-full max-w-xl rounded-2xl p-6 sm:p-8 lg:max-w-md ${GLASS}`}>
      <h2 className="fg-strong text-lg font-semibold">Welcome Back</h2>
      <p className="fg-muted mt-1 text-xs">Sign in to access your campus services.</p>

      <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4">
        <Input
          id="school-id"
          label="School ID"
          type="text"
          autoComplete="username"
          placeholder="Enter your School ID"
          value={schoolId}
          onChange={(e) => setSchoolId(e.target.value)}
          error={errors.schoolId}
        />
        <Input
          id="password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          placeholder="Enter your password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={errors.password}
          rightAdornment={
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              aria-pressed={showPassword}
              className="icon-btn flex h-8 w-8 items-center justify-center rounded-md"
            >
              {showPassword ? <EyeOffIcon width={18} height={18} /> : <EyeIcon width={18} height={18} />}
            </button>
          }
        />

        <Button type="submit" fullWidth loading={loading}>
          {loading ? 'Signing in…' : 'Sign In'}
        </Button>

        {notice && (
          <p role="status" className="notice rounded-lg px-3 py-2 text-xs">
            {notice}
          </p>
        )}
      </form>

      {REGISTER_PATH && (
        <p className="fg-muted mt-5 text-center text-xs">
          Don’t have an account?{' '}
          <a href={REGISTER_PATH} className="link-accent font-medium">Get Started</a>
        </p>
      )}
    </Reveal>
  );
}
