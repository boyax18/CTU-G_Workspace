import { useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { requestPasswordReset } from './passwordReset';

export default function ForgotPasswordPage() {
  const [schoolId, setSchoolId] = useState('');
  const [email, setEmail] = useState('');
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState('');
  const [done, setDone] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) return;
    if (!schoolId.trim() || !email.trim()) { setMessage('Enter your School ID and registered email.'); return; }
    setPending(true);
    setMessage('');
    try {
      await requestPasswordReset(schoolId, email);
      setDone(true);
      setMessage('If the account details match an eligible account, a password reset email will be sent.');
    } catch {
      setMessage('Password recovery is unavailable. Please try again later.');
    } finally { setPending(false); }
  };
  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="forgot-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="forgot-title" className="fg-strong text-2xl font-bold">Forgot Password</h1>
        <p className="fg-muted mt-2 text-sm">Enter your School ID and registered email. If the details match, you'll receive a reset link.</p>
        {!done && <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <Input id="recover-school-id" label="School ID" value={schoolId} maxLength={50} autoComplete="username" required onChange={(e) => setSchoolId(e.target.value)} />
          <Input id="recover-email" label="Registered email" type="email" value={email} maxLength={150} autoComplete="email" required onChange={(e) => setEmail(e.target.value)} />
          <Button type="submit" fullWidth loading={pending}>{pending ? 'Submitting…' : 'Send reset link'}</Button>
        </form>}
        {message && <p className="fg-body mt-4 text-sm" role="status">{message}</p>}
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
