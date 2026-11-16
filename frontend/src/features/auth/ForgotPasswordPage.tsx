import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import ApiErrorNotice from '../../components/common/ApiErrorNotice';
import { ApiError, initializeCSRF } from '../../api/client';
import { describeRecoveryFailure, RECOVERY_ASSISTED_HINT, requestPasswordReset } from './passwordReset';
import type { RecoveryFailureKind } from './passwordReset';

export default function ForgotPasswordPage() {
  const [schoolId, setSchoolId] = useState('');
  const [email, setEmail] = useState('');
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [kind, setKind] = useState<RecoveryFailureKind | null>(null);
  const [retryWait, setRetryWait] = useState(0);
  const [done, setDone] = useState(false);
  const inFlight = useRef(false);

  useEffect(() => {
    if (retryWait <= 0) return;
    const timer = window.setTimeout(() => setRetryWait((wait) => Math.max(0, wait - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [retryWait]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current || retryWait > 0) return;
    setFailure(null);
    setKind(null);
    if (!schoolId.trim() || !email.trim()) { setMessage('Enter your School ID or Staff ID and registered email.'); return; }
    inFlight.current = true;
    setPending(true);
    setMessage('');
    try {
      await requestPasswordReset(schoolId, email);
      setDone(true);
      setMessage('If the account details match an eligible account, a password reset email will be sent.');
    } catch (problem) {
      const result = describeRecoveryFailure(problem, 'request');
      setFailure(result.error);
      setKind(result.kind);
      if (result.kind === 'wait') setRetryWait(result.wait);
    } finally { inFlight.current = false; setPending(false); }
  };

  const refreshSecurity = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    try {
      await initializeCSRF();
      setFailure(null);
      setKind(null);
      setMessage('Security check refreshed. Send the request again.');
    } catch (problem) {
      setFailure(problem instanceof ApiError ? problem : new ApiError('We could not refresh the security check.'));
    } finally { inFlight.current = false; setPending(false); }
  };

  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="forgot-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="forgot-title" className="fg-strong text-2xl font-bold">Forgot Password</h1>
        <p className="fg-muted mt-2 text-sm">Enter your School ID or Staff ID and registered email. If the details match, you'll receive a reset link.</p>
        {failure && (
          <ApiErrorNotice error={failure}>
            {kind === 'security' && <Button type="button" disabled={pending} onClick={() => void refreshSecurity()}>Refresh security check</Button>}
          </ApiErrorNotice>
        )}
        {!done && <form onSubmit={handleSubmit} noValidate className="mt-5 space-y-4" aria-busy={pending}>
          <Input id="recover-school-id" label="School ID or Staff ID" value={schoolId} maxLength={50} autoComplete="username" required onChange={(e) => setSchoolId(e.target.value)} />
          <Input id="recover-email" label="Registered email" type="email" value={email} maxLength={150} autoComplete="email" required onChange={(e) => setEmail(e.target.value)} />
          <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
            aria-describedby={retryWait > 0 ? 'recover-retry-wait' : undefined}>{pending ? 'Submitting…' : 'Send reset link'}</Button>
          {retryWait > 0 && <p id="recover-retry-wait" className="fg-muted text-xs">Try again in {retryWait} seconds.</p>}
        </form>}
        {message && <p className="fg-body mt-4 text-sm" role="status">{message}</p>}
        {done && <p className="fg-muted mt-2 text-xs">{RECOVERY_ASSISTED_HINT}</p>}
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
