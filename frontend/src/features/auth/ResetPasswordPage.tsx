import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import ApiErrorNotice from '../../components/common/ApiErrorNotice';
import { ApiError, initializeCSRF } from '../../api/client';
import { confirmPasswordReset, describeRecoveryFailure, readResetLink, RECOVERY_PASSWORD_HINT } from './passwordReset';
import type { RecoveryFailureKind } from './passwordReset';

export default function ResetPasswordPage() {
  const [link] = useState(() => readResetLink(window.location.hash));
  useEffect(() => {
    // Remove the token from browser history once captured in component state.
    if (link) window.history.replaceState(null, '', '/reset-password');
  }, [link]);
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [kind, setKind] = useState<RecoveryFailureKind | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [retryWait, setRetryWait] = useState(0);
  const [done, setDone] = useState(false);
  const inFlight = useRef(false);

  useEffect(() => {
    if (retryWait <= 0) return;
    const timer = window.setTimeout(() => setRetryWait((wait) => Math.max(0, wait - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [retryWait]);

  const clearFeedback = () => { setFailure(null); setKind(null); setFieldErrors({}); setMessage(''); };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current || !link || retryWait > 0) return;
    clearFeedback();
    if (password.length < 8 || password !== confirmation) { setMessage('Enter matching passwords of at least 8 characters.'); return; }
    inFlight.current = true;
    setPending(true);
    try {
      await confirmPasswordReset(link.uid, link.token, password, confirmation);
      window.history.replaceState(null, '', '/reset-password');
      setDone(true);
      setMessage('Password changed. You can now sign in.');
    } catch (problem) {
      const result = describeRecoveryFailure(problem, 'reset');
      setFailure(result.error);
      setKind(result.kind);
      if (result.kind === 'fields') {
        setFieldErrors(Object.fromEntries(Object.entries(result.error.fields).map(([key, values]) => [key, values.join(' ')])));
      }
      if (result.kind === 'wait') setRetryWait(result.wait);
    } finally {
      // Never keep a password after an attempt.
      setPassword('');
      setConfirmation('');
      inFlight.current = false;
      setPending(false);
    }
  };

  const refreshSecurity = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    try {
      await initializeCSRF();
      clearFeedback();
      setMessage('Security check refreshed. Enter your new password again.');
    } catch (problem) {
      setFailure(problem instanceof ApiError ? problem : new ApiError('We could not refresh the security check.'));
    } finally { inFlight.current = false; setPending(false); }
  };

  const linkUnusable = !link || kind === 'link_invalid';
  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="reset-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="reset-title" className="fg-strong text-2xl font-bold">Reset Password</h1>
        {!link && <p className="fg-body mt-4 text-sm" role="alert">This reset link is invalid or incomplete.</p>}
        {failure && (
          <ApiErrorNotice error={failure}>
            {kind === 'security' && <Button type="button" disabled={pending} onClick={() => void refreshSecurity()}>Refresh security check</Button>}
          </ApiErrorNotice>
        )}
        {linkUnusable && <a className="link-accent mt-4 inline-block text-sm" href="/forgot-password">Request a new reset link</a>}
        {!linkUnusable && !done && <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4" aria-busy={pending}>
          <Input id="reset-password" label="New password" type="password" value={password} maxLength={128} autoComplete="new-password" required
            aria-describedby="reset-password-hint" error={fieldErrors.password} announceError={false}
            onChange={(e) => { setPassword(e.target.value); setFieldErrors((current) => ({ ...current, password: '' })); }} />
          <Input id="reset-confirm" label="Confirm new password" type="password" value={confirmation} maxLength={128} autoComplete="new-password" required
            error={fieldErrors.password_confirmation} announceError={false}
            onChange={(e) => { setConfirmation(e.target.value); setFieldErrors((current) => ({ ...current, password_confirmation: '' })); }} />
          <p id="reset-password-hint" className="fg-muted text-xs leading-relaxed">{RECOVERY_PASSWORD_HINT}</p>
          <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
            aria-describedby={retryWait > 0 ? 'reset-retry-wait' : undefined}>{pending ? 'Updating…' : 'Update password'}</Button>
          {retryWait > 0 && <p id="reset-retry-wait" className="fg-muted text-xs">Try again in {retryWait} seconds.</p>}
        </form>}
        {message && <p className="fg-body mt-4 text-sm" role="status">{message}</p>}
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
