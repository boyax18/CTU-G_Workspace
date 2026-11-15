import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { EyeIcon, EyeOffIcon } from '../../components/common/Icons';
import { ApiError, initializeCSRF } from '../../api/client';
import ApiErrorNotice from '../../components/common/ApiErrorNotice';
import { emptyRegistration, getRegistrationVerification, submitRegistration, validateRegistration } from './registration';
import { asApiError, clearRegistrationSecrets, registrationRecovery } from './registrationFeedback';
import type { RegistrationData } from './registration';
import RegistrationSchoolInformation from './RegistrationSchoolInformation';

export default function RegisterPage() {
  const [data, setData] = useState<RegistrationData>({ ...emptyRegistration });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState('');
  const [failure, setFailure] = useState<ApiError | null>(null);
  const [needsStatus, setNeedsStatus] = useState(false);
  const [verificationPending, setVerificationPending] = useState(false);
  const [retryWait, setRetryWait] = useState(0);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const inFlight = useRef(false);
  const result = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setRetryWait(wait => Math.max(0, wait - 1)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const change = (name: keyof RegistrationData, value: string) => {
    setData((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: '' }));
    setFailure(null);
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current || needsStatus || retryWait > 0) return;
    if (verificationPending) { window.location.assign('/register/verify'); return; }
    const found = validateRegistration(data);
    setErrors(found);
    setNotice('');
    setFailure(null);
    if (Object.keys(found).length) {
      setFailure(new ApiError('Check the highlighted registration fields.', 400, 'validation_error'));
      document.getElementById(`register-${Object.keys(found)[0]}`)?.focus();
      return;
    }
    inFlight.current = true;
    setLoading(true);
    try {
      const response = await submitRegistration(data);
      setData({ ...emptyRegistration });
      setShowPassword(false);
      setShowConfirmation(false);
      if (response.status === 'verification_required' || response.status === 'existing_verification') {
        window.location.assign('/register/verify');
        return;
      }
      setSubmitted(true);
      window.setTimeout(() => result.current?.focus(), 0);
    } catch (error) {
      const problem = asApiError(error);
      setFailure(problem);
      setErrors(Object.fromEntries(Object.entries(problem.fields).map(([key, values]) => [key, values.join(' ')])));
      if (clearRegistrationSecrets(problem)) {
        setData(current => ({ ...current, password: '', password_confirmation: '' }));
        setShowPassword(false);
        setShowConfirmation(false);
      }
      if (problem.code === 'delivery_failed') setVerificationPending(true);
      if (problem.outcomeUnknown) setNeedsStatus(true);
      if (problem.code === 'throttled') setRetryWait(problem.retryAfter ?? 60);
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  };

  const recover = async (action: 'security' | 'status') => {
    if (inFlight.current) return;
    inFlight.current = true;
    setLoading(true);
    try {
      if (action === 'security') {
        await initializeCSRF();
        setFailure(null);
        setNotice('Security check refreshed. Review your details and submit again.');
      } else {
        await getRegistrationVerification();
        setData({ ...emptyRegistration });
        window.location.assign('/register/verify');
      }
    } catch (error) {
      const problem = asApiError(error);
      setFailure(action === 'status' && needsStatus && problem.code === 'expired'
        ? new ApiError('We could not confirm whether the earlier registration completed. Its saved verification session is unavailable. Check its status with your School Admin before submitting again.', 410, 'expired', {}, { requestId: problem.requestId, outcomeUnknown: true })
        : problem);
    } finally { inFlight.current = false; setLoading(false); }
  };
  const recovery = failure ? registrationRecovery(failure, 'registration') : null;

  const field = (name: keyof RegistrationData, label: string, maxLength: number, autoComplete: string, required = false, type = 'text') => {
    const isPassword = type === 'password';
    const visible = name === 'password' ? showPassword : showConfirmation;
    return (
      <Input id={`register-${name}`} name={name} label={`${label}${required ? ' *' : ' (optional)'}`}
        type={isPassword && visible ? 'text' : type}
        value={data[name]} onChange={(event) => change(name, event.target.value)} error={errors[name]}
        maxLength={maxLength} autoComplete={autoComplete} required={required}
        rightAdornment={isPassword ? (
          <button type="button" aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}
            aria-pressed={visible} aria-controls={`register-${name}`}
            onClick={() => name === 'password' ? setShowPassword((current) => !current) : setShowConfirmation((current) => !current)}
            className="icon-btn flex h-8 w-8 items-center justify-center rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-500">
            {visible ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        ) : undefined} />
    );
  };

  const sectionHeading = 'fg-strong mb-4 w-full border-b border-emerald-500/20 pb-3 text-sm font-semibold';

  return (
    <section className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-14" aria-labelledby="registration-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <p className="fg-accent text-xs font-semibold uppercase tracking-widest">CTU-G Workspace</p>
        <h1 id="registration-title" className="fg-strong mt-2 text-2xl font-bold">Create Account</h1>
        {submitted ? (
          <div ref={result} tabIndex={-1} role="status" className="fg-body mt-6 space-y-3 rounded-xl border border-emerald-500/30 p-5">
            <h2 className="fg-strong text-lg font-semibold">Registration submitted</h2>
            <p className="text-sm">Eligible new accounts are pending administrative review. You can sign in after an administrator approves and activates your account.</p>
            <a href="/" className="link-accent inline-block text-sm font-medium">Return to home</a>
          </div>
        ) : (
          <>
            <p className="fg-muted mt-2 text-sm leading-relaxed">Create your CTU-G Workspace account. Student and Instructor registrations require administrative approval.</p>
            <p className="fg-muted mt-2 text-xs">Fields marked * are required.</p>
            <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-6" aria-busy={loading}>
              {failure && <ApiErrorNotice error={failure}>
                {recovery === 'security' && <Button type="button" disabled={loading} onClick={() => void recover('security')}>Refresh security check</Button>}
                {(needsStatus || recovery === 'check_status') && <Button type="button" disabled={loading} onClick={() => void recover('status')}>Check registration status</Button>}
                {failure.code === 'conflict' && <div className="space-y-2">
                  <p>Check both your School ID and email, then try again. If you already submitted an application, wait for its review.</p>
                  <p>Already have an approved account? <a href="/" className="link-accent underline">Sign in</a>.</p>
                </div>}
                {needsStatus && <Button type="button" disabled={loading} onClick={() => { setNeedsStatus(false); setFailure(null); setData(current => ({ ...current, password: '', password_confirmation: '' })); }}>Restart registration</Button>}
              </ApiErrorNotice>}
              {notice && <p role="status" aria-live="polite" className="notice rounded-lg p-3 text-sm">{notice}</p>}
              {retryWait > 0 && <p className="fg-muted text-sm">Try again in {retryWait} seconds.</p>}
              {verificationPending && <p className="fg-body text-sm">Your details are saved temporarily. Proceed to the verification screen to resend the code.</p>}
              {!verificationPending && <fieldset disabled={loading} className="min-w-0 space-y-7">
                <legend className="sr-only">Registration details</legend>
                <div className="sm:max-w-xs">
                  <label htmlFor="register-requested_role" className="fg-body mb-1.5 block text-xs font-medium">Register as</label>
                  <select id="register-requested_role" name="requested_role" required value={data.requested_role}
                    onChange={(event) => change('requested_role', event.target.value)}
                    aria-invalid={!!errors.requested_role} aria-describedby={errors.requested_role ? 'register-role-error' : undefined}
                    className="field w-full rounded-lg px-3 py-2.5 text-sm">
                    <option value="Student">Student</option><option value="Instructor">Instructor</option>
                  </select>
                  {errors.requested_role && <p id="register-role-error" role="alert" className="fg-error mt-1 text-xs">{errors.requested_role}</p>}
                </div>
                <fieldset className="min-w-0">
                  <legend className={sectionHeading}>01 — Login Credentials</legend>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {field('school_id', 'School ID', 7, 'username', true)}
                    {field('email', 'Email', 150, 'email', true, 'email')}
                    {field('password', 'Password', 128, 'new-password', true, 'password')}
                    {field('password_confirmation', 'Confirm Password', 128, 'new-password', true, 'password')}
                  </div>
                  <p className="fg-muted mt-3 text-xs leading-relaxed">School ID must contain 1–7 digits. Use at least 8 characters. Avoid common passwords, only numbers, and details similar to your name, school ID, or email.</p>
                </fieldset>

                <fieldset className="min-w-0">
                  <legend className={sectionHeading}>02 — Personal Information</legend>
                  <div className="grid gap-4 sm:grid-cols-2">
                    {field('first_name', 'First Name', 100, 'given-name', true)}
                    {field('last_name', 'Last Name', 100, 'family-name', true)}
                    {field('middle_name', 'Middle Name', 100, 'additional-name')}
                    {field('suffix', 'Suffix', 20, 'honorific-suffix')}
                  </div>
                </fieldset>

                <RegistrationSchoolInformation role={data.requested_role} />
              </fieldset>}
              <Button type="submit" loading={loading} disabled={needsStatus || retryWait > 0} fullWidth>{loading
                ? (data.requested_role === 'Student' ? 'Requesting verification…' : 'Submitting request…')
                : (data.requested_role === 'Student' ? 'Proceed Email Verification' : 'Submit Registration')}</Button>
              <a href="/" className="link-accent block text-center text-sm">Back to Home</a>
            </form>
          </>
        )}
      </div>
    </section>
  );
}
