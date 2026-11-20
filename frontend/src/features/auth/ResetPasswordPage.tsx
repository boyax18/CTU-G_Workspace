import { useEffect } from 'react';

/** WF-01.05 D-28: reset links are retired; recovery uses an emailed code on /forgot-password. */
export default function ResetPasswordPage() {
  useEffect(() => {
    // Drop any old link fragment from the address bar and history.
    if (window.location.hash) window.history.replaceState(null, '', '/reset-password');
  }, []);
  return (
    <section className="mx-auto w-full max-w-md px-4 py-12" aria-labelledby="reset-title">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <h1 id="reset-title" className="fg-strong text-2xl font-bold">Reset Password</h1>
        <p className="fg-body mt-4 text-sm">Password reset links are no longer used. Request a 6-digit code instead.</p>
        <a className="link-accent mt-4 inline-block text-sm" href="/forgot-password">Go to Forgot Password</a>
        <br />
        <a className="link-accent mt-5 inline-block text-sm" href="/">Back to login</a>
      </div>
    </section>
  );
}
