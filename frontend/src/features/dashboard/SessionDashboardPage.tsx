import { useEffect, useState } from 'react';
import Button from '../../components/common/Button';
import { getWorkspaceSession, logoutWorkspace } from '../auth/session';
import type { AuthenticatedWorkspaceSession } from '../auth/session';

type ScreenState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'error'; message: string }
  | { status: 'ready'; session: AuthenticatedWorkspaceSession };

export default function SessionDashboardPage() {
  const [state, setState] = useState<ScreenState>({ status: 'loading' });
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState('');
  const [refreshIndex, setRefreshIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getWorkspaceSession().then((session) => {
      if (cancelled) return;
      setState(session.authenticated ? { status: 'ready', session } : { status: 'anonymous' });
    }).catch(() => {
      if (!cancelled) setState({ status: 'error', message: 'We could not verify your session.' });
    });
    return () => { cancelled = true; };
  }, [refreshIndex]);

  const signOut = async () => {
    if (signingOut) return;
    setSigningOut(true);
    setSignOutError('');
    try {
      await logoutWorkspace();
      window.location.assign('/');
    } catch {
      setSignOutError('Sign-out could not be confirmed. Please try again.');
      setSigningOut(false);
    }
  };

  if (state.status === 'loading') {
    return <p role="status" className="fg-muted mx-auto max-w-3xl p-8 text-sm">Checking your session…</p>;
  }
  if (state.status === 'anonymous') {
    return (
      <section className="mx-auto max-w-3xl p-8" aria-labelledby="session-heading">
        <h1 id="session-heading" className="fg-strong text-xl font-semibold">Sign in required</h1>
        <p className="fg-body mt-2 text-sm">You need an approved, active Workspace account to continue.</p>
        <a href="/#login" className="link-accent mt-4 inline-block text-sm font-medium">Return to sign-in</a>
      </section>
    );
  }
  if (state.status === 'error') {
    return (
      <section className="mx-auto max-w-3xl p-8" aria-labelledby="session-error">
        <h1 id="session-error" className="fg-strong text-xl font-semibold">Session unavailable</h1>
        <p role="alert" className="fg-body my-4 text-sm">{state.message}</p>
        <Button onClick={() => { setState({ status: 'loading' }); setRefreshIndex((current) => current + 1); }}>Try again</Button>
      </section>
    );
  }

  const { account } = state.session;
  return (
    <section className="mx-auto w-full max-w-4xl px-4 py-10 sm:px-8" aria-labelledby="dashboard-heading">
      <div className="surface-glass rounded-2xl p-6 sm:p-8">
        <p className="fg-accent text-xs font-semibold uppercase tracking-widest">CTU-G Workspace</p>
        <h1 id="dashboard-heading" className="fg-strong mt-2 text-2xl font-semibold">Welcome to your workspace</h1>
        <p className="fg-muted mt-2 text-sm">Your sign-in is active. The shared dashboard modules will be added after their permissions and workflows are approved.</p>
        <dl className="fg-body mt-6 space-y-3 text-sm">
          <div><dt className="font-semibold">School ID</dt><dd>{account.school_id}</dd></div>
          <div>
            <dt className="font-semibold">Assigned roles</dt>
            <dd>{account.roles.join(', ') || 'None'}</dd>
          </div>
        </dl>
        <p className="fg-muted mt-5 text-xs">Roles shown here are informational. Every protected operation must be authorized by Django.</p>
        {signOutError && <p role="alert" className="fg-error mt-4 text-sm">{signOutError}</p>}
        <div className="mt-6"><Button variant="outline" loading={signingOut} onClick={signOut}>Sign out</Button></div>
      </div>
    </section>
  );
}
