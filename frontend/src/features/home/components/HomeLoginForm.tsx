import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../../components/common/Button';
import Input from '../../../components/common/Input';
import { EyeIcon, EyeOffIcon } from '../../../components/common/Icons';
import { REGISTER_PATH } from '../../../utils/constants';

interface FormErrors {
  schoolId?: string;
  password?: string;
}

export default function HomeLoginForm() {
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

    submitting.current = true;
    setLoading(true);
    try {
      // FRONTEND PLACEHOLDER: no authentication API is connected yet.
      // Replace this block with a call to authService (Django REST API) later.
      await new Promise((resolve) => setTimeout(resolve, 800));
      setNotice('Development mode: sign-in is not connected to the server yet, so nothing was submitted.');
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  return (
    <div id="login" className="w-full max-w-md rounded-2xl border border-gray-200 bg-white p-6 shadow-lg shadow-green-900/5 sm:p-8">
      <h2 className="text-lg font-semibold text-gray-900">Welcome Back</h2>
      <p className="mt-1 text-xs text-gray-500">Sign in to access your campus services.</p>

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
              className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 hover:text-green-800"
            >
              {showPassword ? <EyeOffIcon width={18} height={18} /> : <EyeIcon width={18} height={18} />}
            </button>
          }
        />

        <Button type="submit" fullWidth loading={loading}>
          {loading ? 'Signing in…' : 'Sign In'}
        </Button>

        {notice && (
          <p role="status" className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {notice}
          </p>
        )}
      </form>

      {REGISTER_PATH && (
        <p className="mt-5 text-center text-xs text-gray-500">
          Don’t have an account?{' '}
          <a href={REGISTER_PATH} className="font-medium text-green-800 hover:underline">Get Started</a>
        </p>
      )}
    </div>
  );
}