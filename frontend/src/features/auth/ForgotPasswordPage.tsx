import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import ApiErrorNotice from '../../components/common/ApiErrorNotice';
import { ApiError, initializeCSRF } from '../../api/client';
import { codeGuidance, normalizeCode } from './registrationFeedback';
import {
  confirmPasswordReset, describeRecoveryFailure, RECOVERY_ASSISTED_HINT, RECOVERY_ASSISTED_INTRO, RECOVERY_CODE_SENT,
  RECOVERY_PASSWORD_HINT, requestPasswordReset, verifyAssistedRecoveryCode, verifyPasswordResetCode,
} from './passwordReset';
import type { RecoveryFailureKind, RecoveryStep } from './passwordReset';

type Stage = 'email' | 'code' | 'assisted' | 'password' | 'done';

const startsAssisted = () => {
  try { return new URLSearchParams(window.location.search).get('recovery') === 'code'; } catch { return false; }
};

/** WF-01.05 CR-01: Forgot Password → email → 6-digit code → new password → sign in.
 *  25 Nov 2026: "I have an account recovery code" (administrator-assisted) → email + code → new password. */
export default function ForgotPasswordPage() {
  const [stage, setStage] = useState<Stage>(() => (startsAssisted() ? 'assisted' : 'email'));
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [codeValidSeconds, setCodeValidSeconds] = useState(600);
  const [resendWait, setResendWait] = useState(0);
  const [retryWait, setRetryWait] = useState(0);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [kind, setKind] = useState<RecoveryFailureKind | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const inFlight = useRef(false);
  const assistedFlow = useRef(startsAssisted());
  const codeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (resendWait <= 0 && retryWait <= 0) return;
    const timer = window.setTimeout(() => {
      setResendWait((wait) => Math.max(0, wait - 1));
      setRetryWait((wait) => Math.max(0, wait - 1));
    }, 1000);
    return () => window.clearTimeout(timer);
  }, [resendWait, retryWait]);

  const clearFeedback = () => { setFailure(null); setKind(null); setFieldErrors({}); setMessage(''); };

  const fail = (problem: unknown, step: RecoveryStep) => {
    const result = describeRecoveryFailure(problem, step);
    setFailure(result.error);
    setKind(result.kind);
    if (result.kind === 'wait') setRetryWait(result.wait);
    if (result.kind === 'fields') {
      setFieldErrors(Object.fromEntries(Object.entries(result.error.fields).map(([key, values]) => [key, values.join(' ')])));
    }
    if (result.kind === 'session_invalid') { setCode(''); setStage(stage === 'password' && assistedFlow.current ? 'assisted' : 'email'); }
  };

  const run = async (action: () => Promise<void>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(true);
    try { await action(); } finally { inFlight.current = false; setPending(false); }
  };

  const sendCode = () => run(async () => {
    clearFeedback();
    try {
      const result = await requestPasswordReset(email);
      setCodeValidSeconds(result.codeValidSeconds);
      setResendWait(result.resendAfter);
      setStage('code');
      setMessage(RECOVERY_CODE_SENT);
      window.setTimeout(() => codeInput.current?.focus(), 0);
    } catch (problem) { fail(problem, 'request'); }
  });

  const submitEmail = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (retryWait > 0) return;
    if (!email.trim()) { clearFeedback(); setMessage('Enter your registered email.'); return; }
    void sendCode();
  };

  const submitCode = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (retryWait > 0) return;
    if (!/^[0-9]{6}$/.test(code)) { clearFeedback(); setFieldErrors({ code: 'Enter the 6-digit code from your email.' }); return; }
    void run(async () => {
      clearFeedback();
      try {
        await verifyPasswordResetCode(email, code);
        setStage('password');
      } catch (problem) { fail(problem, 'verify'); }
      finally { setCode(''); }
    });
  };

  const submitAssisted = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (retryWait > 0) return;
    const problems: Record<string, string> = {};
    if (!email.trim()) problems.email = 'Enter your registered email.';
    if (!/^[0-9]{6}$/.test(code)) problems.code = 'Enter the 6-digit code from your email.';
    if (Object.keys(problems).length) { clearFeedback(); setFieldErrors(problems); return; }
    void run(async () => {
      clearFeedback();
      try {
        assistedFlow.current = true;
        await verifyAssistedRecoveryCode(email, code);
        setStage('password');
      } catch (problem) { fail(problem, 'verify'); }
      finally { setCode(''); }
    });
  };

  const switchAssisted = (on: boolean) => {
    clearFeedback();
    setCode(''); setResendWait(0);
    setStage(on ? 'assisted' : 'email');
  };

  const submitPassword = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (retryWait > 0) return;
    clearFeedback();
    if (password.length < 8 || password !== confirmation) { setMessage('Enter matching passwords of at least 8 characters.'); return; }
    void run(async () => {
      try {
        await confirmPasswordReset(email, password, confirmation);
        setStage('done');
        setMessage('Password changed. You can now sign in.');
      } catch (problem) { fail(problem, 'reset'); }
      finally { setPassword(''); setConfirmation(''); } // never keep a password after an attempt
    });
  };

  const refreshSecurity = () => run(async () => {
    try {
      await initializeCSRF();
      clearFeedback();
      setMessage('Security check refreshed. Try again.');
    } catch (problem) {
      setFailure(problem instanceof ApiError ? problem : new ApiError('We could not refresh the security check.'));
    }
  });

  const startOver = () => {
    clearFeedback();
    setCode(''); setPassword(''); setConfirmation(''); setResendWait(0);
    setStage('email');
  };

  const waitNote = retryWait > 0 && <p id="recover-retry-wait" className="fg-muted text-xs">Try again in {retryWait} seconds.</p>;

  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="forgot-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="forgot-title" className="fg-strong text-2xl font-bold">Forgot Password</h1>
        {stage === 'email' && <p className="fg-muted mt-2 text-sm">Enter the email registered to your account. If it matches an eligible account, we'll send a 6-digit code.</p>}
        {failure && (
          <ApiErrorNotice error={failure}>
            {kind === 'security' && <Button type="button" disabled={pending} onClick={() => void refreshSecurity()}>Refresh security check</Button>}
          </ApiErrorNotice>
        )}

        {stage === 'email' && (
          <form onSubmit={submitEmail} noValidate className="mt-5 space-y-4" aria-busy={pending}>
            <Input id="recover-email" label="Registered email" type="email" value={email} maxLength={150} autoComplete="email" required
              error={fieldErrors.email} announceError={false} onChange={(e) => setEmail(e.target.value)} />
            <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
              aria-describedby={retryWait > 0 ? 'recover-retry-wait' : undefined}>{pending ? 'Sending…' : 'Send code'}</Button>
            {waitNote}
            <button type="button" className="link-accent text-sm" disabled={pending} onClick={() => switchAssisted(true)}>
              I have an account recovery code
            </button>
          </form>
        )}

        {stage === 'assisted' && (
          <>
            <p className="fg-muted mt-2 text-sm">{RECOVERY_ASSISTED_INTRO}</p>
            <form onSubmit={submitAssisted} noValidate className="mt-5 space-y-4" aria-busy={pending}>
              <Input id="assisted-email" label="Registered email" type="email" value={email} maxLength={150} autoComplete="email" required
                error={fieldErrors.email} announceError={false} onChange={(e) => setEmail(e.target.value)} />
              <Input id="assisted-code" name="code" label="Account recovery code" type="text" inputMode="numeric"
                autoComplete="one-time-code" pattern="[0-9]{6}" required value={code} error={fieldErrors.code} announceError={false}
                onChange={(e) => { setCode(normalizeCode(e.target.value)); setFieldErrors((current) => ({ ...current, code: '' })); }} />
              <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
                aria-describedby={retryWait > 0 ? 'recover-retry-wait' : undefined}>{pending ? 'Checking…' : 'Verify recovery code'}</Button>
              {waitNote}
            </form>
            <p className="fg-muted mt-3 text-xs">The code expires 10 minutes after it was sent. For a new one, ask the campus administrator again.</p>
            <button type="button" className="link-accent mt-3 text-sm" disabled={pending} onClick={() => switchAssisted(false)}>
              Use Forgot Password with a code sent to my email instead
            </button>
          </>
        )}

        {stage === 'code' && (
          <>
            <p className="fg-muted mt-2 text-xs">{codeGuidance(codeValidSeconds)}</p>
            <form onSubmit={submitCode} noValidate className="mt-5 space-y-4" aria-busy={pending}>
              {/* No maxLength: it would truncate a pasted "123-456" before digits are kept. */}
              <Input ref={codeInput} id="recover-code" name="code" label="Verification code" type="text" inputMode="numeric"
                autoComplete="one-time-code" pattern="[0-9]{6}" required value={code} error={fieldErrors.code} announceError={false}
                onChange={(e) => { setCode(normalizeCode(e.target.value)); setFieldErrors({}); }} />
              <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
                aria-describedby={retryWait > 0 ? 'recover-retry-wait' : undefined}>{pending ? 'Checking…' : 'Verify code'}</Button>
              {waitNote}
            </form>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              {/* Visible text equals the accessible name (WCAG 2.5.3); the countdown is a linked description. */}
              <Button type="button" variant="outline" size="sm" disabled={pending || resendWait > 0 || retryWait > 0}
                aria-describedby={resendWait > 0 ? 'recover-resend-wait' : undefined} onClick={() => void sendCode()}>Resend code</Button>
              <Button type="button" variant="outline" size="sm" disabled={pending} onClick={startOver}>Start over</Button>
              {resendWait > 0 && <span id="recover-resend-wait" className="fg-muted text-xs">Resend available in {resendWait}s</span>}
            </div>
            <p className="fg-muted mt-3 text-xs">{RECOVERY_ASSISTED_HINT}</p>
          </>
        )}

        {stage === 'password' && (
          <form onSubmit={submitPassword} noValidate className="mt-5 space-y-4" aria-busy={pending}>
            <Input id="reset-password" label="New password" type="password" value={password} maxLength={128} autoComplete="new-password" required
              aria-describedby="reset-password-hint" error={fieldErrors.password} announceError={false}
              onChange={(e) => { setPassword(e.target.value); setFieldErrors((current) => ({ ...current, password: '' })); }} />
            <Input id="reset-confirm" label="Confirm new password" type="password" value={confirmation} maxLength={128} autoComplete="new-password" required
              error={fieldErrors.password_confirmation} announceError={false}
              onChange={(e) => { setConfirmation(e.target.value); setFieldErrors((current) => ({ ...current, password_confirmation: '' })); }} />
            <p id="reset-password-hint" className="fg-muted text-xs leading-relaxed">{RECOVERY_PASSWORD_HINT}</p>
            <Button type="submit" fullWidth loading={pending} disabled={retryWait > 0}
              aria-describedby={retryWait > 0 ? 'recover-retry-wait' : undefined}>{pending ? 'Updating…' : 'Update password'}</Button>
            {waitNote}
          </form>
        )}

        {message && <p className="fg-body mt-4 text-sm" role="status">{message}</p>}
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
