/** My profile: confirm the signed-in account's current email (enables password recovery).
 *  Django checks the session, CSRF, OTP policy and rate limits; this card only shows results. */
import { useEffect, useId, useState } from 'react';
import type { FormEvent } from 'react';
import {
  confirmEmailVerificationCode, getEmailVerificationStatus, requestEmailVerificationCode,
} from '../auth/emailVerification.ts';
import type { EmailVerificationStatus } from '../auth/emailVerification.ts';

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
const fieldClass = `dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm ${focus}`;
const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${focus}`;
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${focus}`;

type State =
  | { status: 'loading' }
  | { status: 'unavailable' }
  | { status: 'ready'; data: EmailVerificationStatus };

function errorCode(error: unknown): string {
  return error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
}

function retryAfter(error: unknown): number | undefined {
  return error && typeof error === 'object' && 'retryAfter' in error
    ? (error as { retryAfter?: number }).retryAfter : undefined;
}

export default function EmailVerificationCard() {
  const ids = useId();
  const [state, setState] = useState<State>({ status: 'loading' });
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getEmailVerificationStatus()
      .then((data) => { if (!cancelled) setState({ status: 'ready', data }); })
      .catch(() => { if (!cancelled) setState({ status: 'unavailable' }); });
    return () => { cancelled = true; };
  }, []);

  async function sendCode() {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const { validSeconds } = await requestEmailVerificationCode();
      setCodeSent(true);
      setNotice(`A 6-digit code was sent to your email address. It expires in ${Math.round(validSeconds / 60)} minutes. `
        + 'Check Spam if it does not arrive within a few minutes.');
    } catch (err) {
      const code = errorCode(err);
      const wait = retryAfter(err);
      setError(code === 'already_verified' ? 'Your email address is already verified.'
        : code === 'verification_wait' || code === 'rate_limited'
          ? `Please wait${wait ? ` ${wait} seconds` : ''} before requesting another code.`
          : code === 'email_missing' ? 'Your account has no email address. Contact the campus administrator.'
            : code === 'authentication_required' ? 'Your session has ended. Sign in again to continue.'
              : 'The code could not be requested. No automatic retry was made.');
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try {
      await confirmEmailVerificationCode(code.trim());
      setState((current) => current.status === 'ready'
        ? { status: 'ready', data: { ...current.data, email_verified: true } } : current);
      setCodeSent(false); setCode('');
      setNotice('Your email address is verified. You can now use Forgot password if you ever need it.');
    } catch (err) {
      setError(errorCode(err) === 'verification_code_invalid' ? 'The code is incorrect or has expired.'
        : errorCode(err) === 'rate_limited' ? 'Too many attempts. Wait a minute, then try again.'
          : 'The code could not be checked. No automatic retry was made.');
    } finally {
      setBusy(false);
    }
  }

  if (state.status === 'loading') {
    return <p role="status" className="dashboard-muted mt-6 text-sm">Checking email verification…</p>;
  }
  if (state.status === 'unavailable') return null; // feature off or session ended: nothing to offer

  const { email, email_verified: verified } = state.data;
  return (
    <section aria-labelledby={`${ids}-title`} className="dashboard-panel mt-6 rounded-xl border p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 id={`${ids}-title`} className="dashboard-heading text-base font-semibold">Email verification</h3>
        <span className="dashboard-heading inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium">
          <span aria-hidden="true">{verified ? '✓' : '!'}</span>{verified ? 'Verified' : 'Not verified'}
        </span>
      </div>
      <p className="dashboard-muted mt-2 break-all text-sm">{email ?? 'No email address on file'}</p>
      {!verified && (
        <p className="dashboard-muted mt-2 text-sm">
          Confirm this address with a one-time code so you can recover your password by email.
        </p>
      )}
      {notice && <p role="status" aria-live="polite" className="dashboard-heading mt-3 text-sm">{notice}</p>}
      {error && <p role="alert" className="dashboard-error-block mt-3 rounded-lg border p-3 text-sm">{error}</p>}
      {!verified && email && (
        <div className="mt-4 flex flex-wrap items-end gap-3">
          {codeSent && (
            <form onSubmit={verify} noValidate className="flex flex-wrap items-end gap-3">
              <label className="dashboard-muted flex flex-col gap-1 text-xs font-medium">
                Verification code
                <input value={code} inputMode="numeric" autoComplete="one-time-code" maxLength={6}
                  pattern="[0-9]{6}" className={`${fieldClass} w-40 tracking-widest`}
                  onChange={(event) => setCode(event.target.value.replace(/\D/g, '').slice(0, 6))} />
              </label>
              <button type="submit" className={primaryButton} disabled={busy || code.length !== 6}>Verify email</button>
            </form>
          )}
          <button type="button" className={codeSent ? secondaryButton : primaryButton} disabled={busy}
            onClick={() => { void sendCode(); }}>
            {codeSent ? 'Resend code' : 'Send verification code'}
          </button>
        </div>
      )}
    </section>
  );
}
