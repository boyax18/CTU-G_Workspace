import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { ApiError, initializeCSRF } from '../../api/client';
import ApiErrorNotice from '../../components/common/ApiErrorNotice';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { cancelRegistrationVerification, getRegistrationVerification, resendRegistrationCode, verifyRegistrationCode } from './registration';
import type { RegistrationVerification } from './registration';
import { asApiError, registrationRecovery } from './registrationFeedback';

export default function VerifyEmailPage() {
  const [verification, setVerification] = useState<RegistrationVerification | null>(null);
  const [code, setCode] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [complete, setComplete] = useState(false);
  const [needsStatus, setNeedsStatus] = useState(false);
  const [uncertainWrite, setUncertainWrite] = useState(false);
  const [requestWait, setRequestWait] = useState(0);
  const inFlight = useRef(false);
  const result = useRef<HTMLDivElement>(null);
  const codeInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    getRegistrationVerification().then(state => { if (active) setVerification(state); })
      .catch((error: unknown) => { if (active) { setCode(''); setFailure(asApiError(error)); } })
      .finally(() => { if (active) setChecking(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setRequestWait(wait => Math.max(0, wait - 1));
      setVerification(state => state ? { ...state,
        retry_after: Math.max(0, (state.retry_after ?? 0) - 1),
        expires_in: Math.max(0, (state.expires_in ?? 0) - 1),
      } : state);
    }, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const showFailure = (error: unknown) => {
    const next = asApiError(error);
    setCode('');
    setFailure(next);
    setNotice('');
    if (next.code === 'expired' || next.code === 'conflict') setVerification(null);
    if (next.outcomeUnknown) { setNeedsStatus(true); setUncertainWrite(true); }
    if (next.code === 'throttled') setRequestWait(next.retryAfter ?? 60);
    if (typeof next.context.expires_in === 'number' && typeof next.context.delivery_sent === 'boolean') {
      setVerification(previous => ({ ...previous, ...next.context, status: 'verification_required' }));
    }
  };

  const checkStatus = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      const state = await getRegistrationVerification();
      setVerification(state);
      setFailure(null);
      setNeedsStatus(false);
      setUncertainWrite(false);
      setNotice('Verification status checked. You can continue with this saved attempt.');
    } catch (error) {
      showFailure(error);
      // A missing stage cannot tell us whether an earlier uncertain write committed.
      if (uncertainWrite) setNeedsStatus(true);
    } finally { inFlight.current = false; setBusy(false); }
  };

  const refreshSecurity = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    try {
      await initializeCSRF();
      setFailure(null);
      setNotice('Security check refreshed. Enter your code and submit again.');
    } catch (error) { showFailure(error); }
    finally { inFlight.current = false; setBusy(false); }
  };

  const perform = async (action: 'verify' | 'resend' | 'cancel') => {
    if (inFlight.current || needsStatus || requestWait > 0) return;
    if (action === 'verify' && !/^[0-9]{6}$/.test(code)) {
      setFailure(new ApiError('Enter the six-digit code from your email.', 400, 'validation_error', { code: ['Enter a six-digit verification code.'] }));
      return;
    }
    inFlight.current = true;
    setBusy(true);
    setNotice('');
    setFailure(null);
    try {
      if (action === 'cancel') {
        await cancelRegistrationVerification();
        setCode('');
        window.location.assign('/register');
        return;
      }
      const state = action === 'verify' ? await verifyRegistrationCode(code) : await resendRegistrationCode();
      setCode('');
      if (state.status === 'completed') {
        setVerification(null);
        setComplete(true);
        window.setTimeout(() => result.current?.focus(), 0);
      } else {
        setVerification(state);
        setNotice('A new code was sent. The earlier code is no longer valid.');
      }
    } catch (error) { showFailure(error); }
    finally { inFlight.current = false; setBusy(false); }
  };

  const submit = (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); void perform('verify'); };
  const recovery = failure ? registrationRecovery(failure, 'verification') : null;
  const expired = verification?.expires_in === 0 || recovery === 'restart';
  const exhausted = verification?.attempts_remaining === 0;
  const blocked = busy || needsStatus || requestWait > 0;
  const codeError = failure?.fields.code?.join(' ') || (failure?.code === 'otp_invalid' ? failure.message : undefined);

  return (
    <section className="mx-auto w-full max-w-xl px-4 py-10 sm:px-6 sm:py-14" aria-labelledby="verification-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <p className="fg-accent text-xs font-semibold uppercase tracking-widest">CTU-G Workspace</p>
        <h1 id="verification-title" className="fg-strong mt-2 text-2xl font-bold">Verify your email</h1>
        {complete ? (
          <div ref={result} role="status" tabIndex={-1} className="fg-body mt-6 space-y-3">
            <h2 className="fg-strong text-lg font-semibold">Registration submitted</h2>
            <p>Your email is verified. Your account is pending administrative review. You can sign in after approval and activation.</p>
            <a href="/" className="link-accent inline-block">Return to home</a>
          </div>
        ) : (
          <>
            {failure && <ApiErrorNotice error={failure}>
              {recovery === 'correct' && <Button type="button" onClick={() => codeInput.current?.focus()}>Enter verification code</Button>}
              {recovery === 'security' && <Button type="button" disabled={busy} onClick={() => void refreshSecurity()}>Refresh security check</Button>}
              {(recovery === 'retry' || needsStatus || recovery === 'check_status') && <Button type="button" disabled={busy} onClick={() => void checkStatus()}>Check registration status</Button>}
            </ApiErrorNotice>}
            {notice && <p role="status" aria-live="polite" className="fg-body mt-4 text-sm">{notice}</p>}
            {checking && <p role="status" className="fg-body mt-4">Checking your registration...</p>}
            {uncertainWrite && <p role="status" className="fg-body mt-4 text-sm">We could not confirm whether the earlier registration completed. Check its status before submitting again; a missing verification session alone does not confirm the outcome.</p>}
            {verification && !expired && !checking && !needsStatus && (
              <>
                <p className="fg-body mt-4 text-sm">{exhausted
                  ? 'This verification attempt has reached the failed-code limit.' : verification.delivery_sent
                  ? 'Enter the six-digit code sent to the email address in your saved Student registration.'
                  : 'Your registration is saved temporarily, but we could not send a code. Use Resend code after the waiting period.'}</p>
                <p className="fg-muted mt-2 text-xs">No account has been created yet. Your saved details remain unchanged.</p>
                <form onSubmit={submit} noValidate className="mt-6 space-y-4" aria-busy={busy}>
                  <Input ref={codeInput} id="registration-otp" name="code" label="Verification code" type="text"
                    inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} error={codeError}
                    value={code} onChange={event => { setCode(event.target.value.replace(/[^0-9]/g, '')); setFailure(null); }}
                    disabled={blocked || exhausted} required />
                  <Button type="submit" loading={busy} disabled={blocked || exhausted || !verification.delivery_sent} fullWidth>Verify and submit registration</Button>
                </form>
                {exhausted && <p className="fg-body mt-4 text-sm">The attempt limit was reached. Cancel this attempt to start again.</p>}
                <p className="fg-muted mt-3 text-xs">{verification.attempts_remaining} attempts remaining.</p>
                <div className="mt-5 flex flex-wrap gap-3">
                  <Button type="button" onClick={() => void perform('resend')} aria-label="Resend code"
                    disabled={blocked || exhausted || (verification.retry_after ?? 0) > 0 || verification.resends_remaining === 0}>
                    {(verification.retry_after ?? 0) > 0 ? 'Resend in ' + verification.retry_after + 's' : 'Resend code'}
                  </Button>
                  <Button type="button" onClick={() => void perform('cancel')} disabled={blocked}>Cancel registration</Button>
                </div>
              </>
            )}
            {requestWait > 0 && <p className="fg-muted mt-3 text-sm">Try again in {requestWait} seconds.</p>}
            {(expired || needsStatus) && <a href="/register" className="link-accent mt-5 inline-block text-sm">Start new registration</a>}
            {expired && !uncertainWrite && <p role="status" className="fg-body mt-4 text-sm">Your saved verification session is unavailable. Start a new registration.</p>}
          </>
        )}
      </div>
    </section>
  );
}
