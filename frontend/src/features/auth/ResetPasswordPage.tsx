import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import Button from '../../components/common/Button';
import Input from '../../components/common/Input';
import { confirmPasswordReset, readResetLink } from './passwordReset';

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
  const [done, setDone] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending || !link) return;
    if (password.length < 8 || password !== confirmation) { setMessage('Enter matching passwords of at least 8 characters.'); return; }
    setPending(true);
    setMessage('');
    try {
      await confirmPasswordReset(link.uid, link.token, password, confirmation);
      window.history.replaceState(null, '', '/reset-password');
      setPassword('');
      setConfirmation('');
      setDone(true);
      setMessage('Password changed. You can now sign in.');
    } catch { setMessage('Unable to reset password. Your link may be invalid or expired.'); }
    finally { setPending(false); }
  };
  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="reset-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="reset-title" className="fg-strong text-2xl font-bold">Reset Password</h1>
        {!link && <p className="fg-body mt-4 text-sm" role="alert">This reset link is invalid or incomplete.</p>}
        {link && !done && <form onSubmit={handleSubmit} className="mt-5 space-y-4">
          <Input id="reset-password" label="New password" type="password" value={password} maxLength={128} autoComplete="new-password" required onChange={(e) => setPassword(e.target.value)} />
          <Input id="reset-confirm" label="Confirm new password" type="password" value={confirmation} maxLength={128} autoComplete="new-password" required onChange={(e) => setConfirmation(e.target.value)} />
          <Button type="submit" fullWidth loading={pending}>{pending ? 'Updating…' : 'Update password'}</Button>
        </form>}
        {message && <p className="fg-body mt-4 text-sm" role="status">{message}</p>}
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
