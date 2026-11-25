/** My profile: confirm the signed-in account's current email (enables password recovery).
 *  Django checks the session, CSRF, OTP policy and rate limits; this card only shows results.
 *  An accepted request means the code is queued for email, never that it was delivered. */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { normalizeCode } from '../auth/registrationFeedback';
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

const minutes = (seconds: number) => Math.max(1, Math.round(seconds / 60));

export default function EmailVerificationCard() {
  const ids = useId();
  const [state, setState] = useState<State>({ status: 'loading' });
  const [codeSent, setCodeSent] = useState(false);
  const [code, setCode] = useState('');
  const [resendWait, setResendWait] = useState(0);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const codeInput = useRef<HTMLInputElement>(null);
  const [focusTick, setFocusTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getEmailVerificationStatus()
      .then((data) => {
        if (cancelled) return;
        setState({ status: 'ready', data });
        if (data.codePending && !data.email_verified) {
          // A code is already on its way (for example after a page refresh): keep the entry box.
          setCodeSent(true);
          setResendWait(data.resendAfter);
          setNotice(`A code is already on its way. It expires in ${minutes(data.codeExpiresIn)} minutes.`);
        }
      })
      .catch(() => { if (!cancelled) setState({ status: 'unavailable' }); });
    return () => { cancelled = true; };
  }, []);

  // Focus after React has rendered the code box (a timer could run before the input exists).
  useEffect(() => { if (focusTick > 0) codeInput.current?.focus(); }, [focusTick]);

  useEffect(() => {
    if (resendWait <= 0) return;
    const timer = window.setTimeout(() => setResendWait((wait) => Math.max(0, wait - 1)), 1000);
    return () => window.clearTimeout(timer);
  }, [resendWait]);

  async function refresh() {
    try {
      const data = await getEmailVerificationStatus();
      setState({ status: 'ready', data });
      setCodeSent(false); setCode(''); setResendWait(0);
      setNotice(data.email_verified ? 'Your email address is already verified.' : '');
      if (!data.email) setError('Your account has no email address. Contact the campus administrator.');
    } catch {
      setState({ status: 'unavailable' });
    }
  }

  async function sendCode() {
    if (busy || resendWait > 0) return;
    setBusy(true); setError(''); setNotice('');
    try {
      const { resendAfter, validSeconds } = await requestEmailVerificationCode();
      setCodeSent(true); setCode('');
      setResendWait(resendAfter);
      setNotice(`A 6-digit code is on its way to your email. It can take a few minutes to arrive, so check Spam too. `
        + `It expires in ${minutes(validSeconds)} minutes.`);
      setFocusTick((tick) => tick + 1);
    } catch (err) {
      const reason = errorCode(err);
      const wait = retryAfter(err);
      if (reason === 'verification_wait' && wait) setResendWait(wait);
      if (reason === 'conflict') { await refresh(); return; } // already verified or no email: Django says which
      setError(reason === 'verification_wait' || reason === 'throttled'
        ? `Please wait${wait ? ` ${wait} seconds` : ''} before requesting another code.`
        : reason === 'authentication_required' ? 'Your session has ended. Sign in again to continue.'
          : reason === 'verification_unavailable' ? 'Email verification is temporarily unavailable. Try again later.'
            : 'The code could not be requested. No automatic retry was made.');
    } finally {
      setBusy(false);
    }
  }

  async function verify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    if (code.length !== 6) { setError('Enter the 6-digit code from your email.'); return; }
    setBusy(true); setError(''); setNotice('');
    try {
      await confirmEmailVerificationCode(code);
      setState((current) => current.status === 'ready'
        ? { status: 'ready', data: { ...current.data, email_verified: true, codePending: false } } : current);
      setCodeSent(false); setCode(''); setResendWait(0);
      setNotice('Your email address is verified. You can now use Forgot password if you ever need it.');
    } catch (err) {
      const reason = errorCode(err);
      setCode('');
      if (reason === 'verification_code_expired' || reason === 'verification_locked') setResendWait(0);
      if (reason === 'conflict') { await refresh(); return; }
      setError(reason === 'verification_code_expired' ? 'This code has expired. Send a new code.'
        : reason === 'verification_locked' ? 'Too many incorrect codes. Send a new code when the resend button is available.'
          : reason === 'verification_code_invalid' || reason === 'validation_error'
            ? 'That code is incorrect. Check the latest email and try again.'
            : reason === 'throttled' ? 'Too many attempts. Wait a minute, then try again.'
              : reason === 'authentication_required' ? 'Your session has ended. Sign in again to continue.'
                : 'The code could not be checked. No automatic retry was made.');
      setFocusTick((tick) => tick + 1);
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
        <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
          {codeSent && (
            <form onSubmit={verify} noValidate className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <label htmlFor={`${ids}-code`} className="dashboard-muted flex flex-col gap-1 text-xs font-medium">
                Verification code
                {/* No maxLength: a pasted "123 456" keeps its six digits (normalizeCode trims the rest). */}
                <input id={`${ids}-code`} ref={codeInput} value={code} inputMode="numeric" autoComplete="one-time-code"
                  enterKeyHint="done" pattern="[0-9]{6}" aria-describedby={`${ids}-code-hint`}
                  className={`${fieldClass} w-full text-base tracking-[0.3em] sm:w-44`}
                  onChange={(event) => setCode(normalizeCode(event.target.value))} />
              </label>
              <button type="submit" className={primaryButton} disabled={busy || code.length !== 6}>
                {busy ? 'Checking…' : 'Verify email'}
              </button>
            </form>
          )}
          <button type="button" className={codeSent ? secondaryButton : primaryButton} disabled={busy || resendWait > 0}
            aria-describedby={resendWait > 0 ? `${ids}-resend-wait` : undefined} onClick={() => { void sendCode(); }}>
            {codeSent ? 'Resend code' : 'Send verification code'}
          </button>
        </div>
      )}
      {!verified && email && codeSent && (
        <p id={`${ids}-code-hint`} className="dashboard-muted mt-2 text-xs">
          Enter the 6 digits from the newest email.
          {resendWait > 0 && <span id={`${ids}-resend-wait`}> Resend available in {resendWait}s.</span>}
        </p>
      )}
    </section>
  );
}
