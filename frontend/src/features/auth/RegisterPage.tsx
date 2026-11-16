import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { EyeIcon, EyeOffIcon } from '../../components/common/Icons';
import { ApiError } from '../../api/client';
import { emptyRegistration, submitRegistration, requestReapplicationLink, validateRegistration } from './registration';
import type { RegistrationData } from './registration';
import RegistrationSchoolInformation from './RegistrationSchoolInformation';

// Capture before first render; Strict Mode may run state initializers twice.
const initialReapplicationToken = typeof window !== 'undefined'
  ? new URLSearchParams(window.location.hash.slice(1)).get('reapply') || '' : '';

export default function RegisterPage() {
  const [reapplicationToken] = useState(initialReapplicationToken);
  useEffect(() => {
    if (reapplicationToken) window.history.replaceState(null, '', window.location.pathname);
  }, [reapplicationToken]);
  const [linkSchoolId, setLinkSchoolId] = useState('');
  const [linkEmail, setLinkEmail] = useState('');
  const [linkRequested, setLinkRequested] = useState(false);
  const [linkBusy, setLinkBusy] = useState(false);
  const [linkError, setLinkError] = useState('');
  const [data, setData] = useState<RegistrationData>({ ...emptyRegistration });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const inFlight = useRef(false);
  const result = useRef<HTMLDivElement>(null);

  const change = (name: keyof RegistrationData, value: string) => {
    setData((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: '' }));
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current) return;
    const found = validateRegistration(data);
    setErrors(found);
    setNotice('');
    if (Object.keys(found).length) {
      document.getElementById(`register-${Object.keys(found)[0]}`)?.focus();
      return;
    }
    inFlight.current = true;
    setLoading(true);
    try {
      await submitRegistration(data, reapplicationToken || undefined);
      setData({ ...emptyRegistration });
      setShowPassword(false);
      setShowConfirmation(false);
      setSubmitted(true);
      window.setTimeout(() => result.current?.focus(), 0);
    } catch (error) {
      if (error instanceof ApiError) {
        const fields = Object.fromEntries(Object.entries(error.fields).map(([key, values]) => [key, values.join(' ')]));
        setErrors(fields);
        setNotice(error.fields.non_field_errors?.join(' ') || error.message);
        document.getElementById(`register-${Object.keys(fields)[0]}`)?.focus();
      } else {
        setNotice('Registration could not be completed. Please try again.');
      }
    } finally {
      inFlight.current = false;
      setLoading(false);
    }
  };

  const requestLink = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (linkBusy) return;
    if (!/^[0-9]{1,7}$/.test(linkSchoolId.trim()) || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(linkEmail.trim())) {
      setLinkError('Enter a valid School ID and your previously registered email.');
      return;
    }
    setLinkBusy(true);
    setLinkError('');
    try {
      await requestReapplicationLink(linkSchoolId, linkEmail);
      setLinkRequested(true);
    } catch (error) {
      setLinkError(error instanceof ApiError ? error.message : 'The verification request could not be completed.');
    } finally {
      setLinkBusy(false);
    }
  };

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
        <h1 id="registration-title" className="fg-strong mt-2 text-2xl font-bold">{reapplicationToken ? 'Reapply for Registration' : 'Create Account'}</h1>
        {submitted ? (
          <div ref={result} tabIndex={-1} role="status" className="fg-body mt-6 space-y-3 rounded-xl border border-emerald-500/30 p-5">
            <h2 className="fg-strong text-lg font-semibold">Registration submitted</h2>
            <p className="text-sm">Eligible new accounts are pending administrative review. You can sign in after an administrator approves and activates your account.</p>
            <p className="text-sm">If this was a verified reapplication, your account returns to Pending for a fresh administrative review. Otherwise, previously submitted requests are unchanged.</p>
            <a href="/" className="link-accent inline-block text-sm font-medium">Return to home</a>
          </div>
        ) : (
          <>
            <p className="fg-muted mt-2 text-sm leading-relaxed">{reapplicationToken
              ? 'Your verification link was received. Enter every field again, including your new password. Previous details are not prefilled.'
              : 'Create your CTU-G Workspace account. Student and Instructor registrations require administrative approval.'}</p>
            <p className="fg-muted mt-2 text-xs">Fields marked * are required.</p>
            <form onSubmit={handleSubmit} noValidate className="mt-6 space-y-6" aria-busy={loading}>
              {notice && <p role="alert" className="notice rounded-lg p-3 text-sm">{notice}</p>}
              <fieldset disabled={loading} className="min-w-0 space-y-7">
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
              </fieldset>
              <Button type="submit" loading={loading} fullWidth>{loading ? 'Submitting request…' : reapplicationToken ? 'Resubmit Registration' : 'Submit Registration'}</Button>
              <a href="/" className="link-accent block text-center text-sm">Back to Home</a>
            </form>
          </>
        )}
        {!reapplicationToken && !submitted && (
          <div className="mt-8 border-t border-emerald-500/20 pt-6">
            <h2 className="fg-strong text-base font-semibold">Was your registration rejected?</h2>
            <p className="fg-muted mt-2 text-sm">Request a secure reapplication link sent only to the email already on your rejected registration. After verification, you must complete the entire registration form again.</p>
            {linkRequested ? (
              <p role="status" className="fg-body mt-3 text-sm">If those details match an eligible rejected registration, a verification link will be sent. Check your email.</p>
            ) : (
              <form onSubmit={requestLink} className="mt-4 space-y-3" aria-busy={linkBusy}>
                {linkError && <p role="alert" className="fg-error text-sm">{linkError}</p>}
                <div className="grid gap-3 sm:grid-cols-2">
                  <Input id="reapply-school-id" label="Previously registered School ID" name="school_id" value={linkSchoolId}
                    maxLength={7} required onChange={(event) => setLinkSchoolId(event.target.value)} />
                  <Input id="reapply-email" label="Previously registered email" name="email" type="email" value={linkEmail}
                    maxLength={150} required onChange={(event) => setLinkEmail(event.target.value)} />
                </div>
                <Button type="submit" loading={linkBusy} fullWidth>Request Reapplication Link</Button>
              </form>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
