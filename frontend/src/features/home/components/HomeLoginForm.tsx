import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../../components/common/Button';
import Input from '../../../components/common/Input';
import Reveal from '../../../components/common/Reveal';
import ApiErrorNotice from '../../../components/common/ApiErrorNotice';
import { EyeIcon, EyeOffIcon } from '../../../components/common/Icons';
import { ApiError, initializeCSRF } from '../../../api/client';
import { getWorkspaceSession, logoutWorkspace } from '../../auth/session';
import type { AuthenticatedWorkspaceSession } from '../../auth/session';
import { describeLoginFailure, LOGIN_APPROVAL_HINT, LOGIN_UNCONFIRMED, notCompletedMessage } from '../../auth/loginFeedback';
import type { LoginRecovery } from '../../auth/loginFeedback';
import { REGISTER_PATH } from '../../../utils/constants';
import { GLASS } from '../../../utils/styles';

export interface LoginCredentials {
  schoolId: string;
  password: string;
}

interface HomeLoginFormProps {
  /** Called with validated credentials; resolves after the session is established. */
  onSubmit?: (credentials: LoginCredentials) => Promise<void>;
}

interface FormErrors {
  schoolId?: string;
  password?: string;
}

const DASHBOARD_PATH = '/dashboard';

export default function HomeLoginForm({ onSubmit }: HomeLoginFormProps) {
  const [schoolId, setSchoolId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [approvalHint, setApprovalHint] = useState(false);
  const [recovery, setRecovery] = useState<LoginRecovery>(null);
  const [retryWait, setRetryWait] = useState(0);
  const [signedIn, setSignedIn] = useState<AuthenticatedWorkspaceSession | null>(null);
  const submitting = useRef(false);

  // WF-01.03 P-03: a browser that already holds a valid session is offered the
  // dashboard instead of a second sign-in. A failed check simply keeps the form.
  useEffect(() => {
    if (!onSubmit) return;
    let cancelled = false;
    getWorkspaceSession()
      .then((session) => { if (!cancelled && session.authenticated) setSignedIn(session); })
      .catch(() => { /* keep the sign-in form */ });
    return () => { cancelled = true; };
  }, [onSubmit]);

  useEffect(() => {
    if (retryWait <= 0) return;
    const timer = window.setTimeout(() => setRetryWait((wait) => Math.max(0, wait - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [retryWait]);

  const resetFeedback = () => {
    setNotice('');
    setFailure(null);
    setApprovalHint(false);
    setRecovery(null);
  };

  const validate = (): FormErrors => {
    const next: FormErrors = {};
    if (!schoolId.trim()) next.schoolId = 'Please enter your School ID or Staff ID.';
    if (!password) next.password = 'Please enter your password.';
    return next;
  };

  const showFailure = async (problem: unknown) => {
    const result = describeLoginFailure(problem);
    // Never keep a password after a failed attempt.
    setPassword('');
    setShowPassword(false);
    if (result.recovery === 'confirm') {
      // The POST may have created a session: read it (GET) before claiming failure.
      try {
        const session = await getWorkspaceSession();
        if (session.authenticated) {
          window.location.assign(DASHBOARD_PATH);
          return;
        }
        setFailure(new ApiError(notCompletedMessage(result.error), result.error.status, result.error.code, {}, { requestId: result.error.requestId }));
      } catch {
        setFailure(new ApiError(LOGIN_UNCONFIRMED, 0, 'network_error', {}, { requestId: result.error.requestId }));
      }
      setRecovery(null);
      return;
    }
    setFailure(result.error);
    setApprovalHint(result.approvalHint);
    setRecovery(result.recovery);
    if (result.recovery === 'wait') setRetryWait(result.wait);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (submitting.current || retryWait > 0) return;

    const found = validate();
    setErrors(found);
    resetFeedback();
    if (Object.keys(found).length > 0) return;

    if (!onSubmit) {
      setNotice('Sign-in is not available yet. This form will be connected in a later phase.');
      return;
    }

    submitting.current = true;
    setLoading(true);
    try {
      await onSubmit({ schoolId: schoolId.trim(), password });
    } catch (problem) {
      await showFailure(problem);
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  const refreshSecurity = async () => {
    if (submitting.current) return;
    submitting.current = true;
    setLoading(true);
    try {
      await initializeCSRF();
      resetFeedback();
      setNotice('Security check refreshed. Enter your password and sign in again.');
    } catch (problem) {
      setFailure(problem instanceof ApiError ? problem : new ApiError(LOGIN_UNCONFIRMED));
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  const signOut = async () => {
    if (submitting.current) return;
    submitting.current = true;
    setLoading(true);
    resetFeedback();
    try {
      await logoutWorkspace();
      setSignedIn(null);
      window.setTimeout(() => document.getElementById('school-id')?.focus(), 0);
    } catch (problem) {
      setFailure(problem instanceof ApiError ? problem : new ApiError('Could not confirm sign-out. Please try again.'));
    } finally {
      submitting.current = false;
      setLoading(false);
    }
  };

  if (signedIn) {
    return (
      <Reveal id="login" direction="right" delay={200} className={`w-full max-w-xl rounded-2xl p-6 sm:p-8 lg:max-w-md ${GLASS}`}>
        <h2 className="fg-strong text-lg font-semibold">Welcome Back</h2>
        <p role="status" className="fg-body mt-2 text-sm">
          You’re signed in as <span className="fg-strong font-semibold">{signedIn.account.school_id}</span>.
        </p>
        {failure && <ApiErrorNotice error={failure} />}
        <div className="mt-5 flex flex-col gap-3">
          <Button fullWidth onClick={() => window.location.assign(DASHBOARD_PATH)}>Continue to Dashboard</Button>
          <Button variant="outline" fullWidth loading={loading} onClick={() => void signOut()}>
            {loading ? 'Signing out…' : 'Sign Out'}
          </Button>
        </div>
      </Reveal>
    );
  }

  return (
    <Reveal id="login" direction="right" delay={200} className={`w-full max-w-xl rounded-2xl p-6 sm:p-8 lg:max-w-md ${GLASS}`}>
      <h2 className="fg-strong text-lg font-semibold">Welcome Back</h2>
      <p className="fg-muted mt-1 text-xs">Sign in to access your campus services.</p>

      <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4" aria-busy={loading}>
        {failure && (
          <ApiErrorNotice error={failure}>
            {approvalHint && <p>{LOGIN_APPROVAL_HINT}</p>}
            {recovery === 'security' && (
              <Button type="button" disabled={loading} onClick={() => void refreshSecurity()}>Refresh security check</Button>
            )}
          </ApiErrorNotice>
        )}
        <Input
          id="school-id"
          label="School ID or Staff ID"
          type="text"
          autoComplete="username"
          placeholder="Enter your School ID or Staff ID"
          maxLength={50}
          value={schoolId}
          onChange={(e) => { setSchoolId(e.target.value); setErrors((current) => ({ ...current, schoolId: undefined })); }}
          error={errors.schoolId}
        />
        <Input
          id="password"
          label="Password"
          type={showPassword ? 'text' : 'password'}
          autoComplete="current-password"
          placeholder="Enter your password"
          maxLength={256}
          value={password}
          onChange={(e) => { setPassword(e.target.value); setErrors((current) => ({ ...current, password: undefined })); }}
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

        <Button type="submit" fullWidth loading={loading} disabled={retryWait > 0}
          aria-describedby={retryWait > 0 ? 'login-retry-wait' : undefined}>
          {loading ? 'Signing in…' : 'Sign In'}
        </Button>
        {retryWait > 0 && <p id="login-retry-wait" className="fg-muted text-xs">Try again in {retryWait} seconds.</p>}

        {notice && (
          <p role="status" className="notice rounded-lg px-3 py-2 text-xs">
            {notice}
          </p>
        )}
      </form>

      <p className="mt-3 text-center text-xs"><a className="link-accent" href="/forgot-password">Forgot Password?</a></p>
      {REGISTER_PATH && (
        <p className="fg-muted mt-5 text-center text-xs">
          Don’t have an account?{' '}
          <a href={REGISTER_PATH} className="link-accent font-medium">Get Started</a>
        </p>
      )}
    </Reveal>
  );
}
