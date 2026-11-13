import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import '../css/theme.css';
import '../css/dashboard.css';
import ThemeProvider from '../contexts/ThemeProvider';
import { DashboardContext } from '../contexts/DashboardContext';
import DashboardShell from '../components/dashboard/DashboardShell';
import { getWorkspaceSession, logoutWorkspace } from '../features/auth/session';
import type { AuthenticatedWorkspaceSession } from '../features/auth/session';
import {
  canOpenDashboardView,
  getDashboardHref,
  getDashboardView,
} from '../features/dashboard/navigation';
import type { DashboardView } from '../features/dashboard/navigation';

type ScreenState =
  | { status: 'loading' }
  | { status: 'anonymous' }
  | { status: 'error' }
  | { status: 'ready'; session: AuthenticatedWorkspaceSession };

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ScreenState>({ status: 'loading' });
  const [refresh, setRefresh] = useState(0);
  const [view, setView] = useState<DashboardView>(() => getDashboardView(window.location.search));
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getWorkspaceSession().then((session) => {
      if (cancelled) return;
      setState(session.authenticated ? { status: 'ready', session } : { status: 'anonymous' });
    }).catch(() => {
      if (!cancelled) setState({ status: 'error' });
    });
    return () => { cancelled = true; };
  }, [refresh]);

  useEffect(() => {
    const onHistory = () => setView(getDashboardView(window.location.search));
    window.addEventListener('popstate', onHistory);
    return () => window.removeEventListener('popstate', onHistory);
  }, []);

  const navigate = useCallback((next: DashboardView) => {
    if (state.status !== 'ready' || !canOpenDashboardView(next, state.session.permissions)) return;
    const nextUrl = getDashboardHref(next);
    window.history.pushState(null, '', nextUrl);
    setView(next);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [state]);

  const signOut = useCallback(async () => {
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
  }, [signingOut]);

  const session = state.status === 'ready' ? state.session : null;
  const value = useMemo(
    () => session ? { session, view, navigate } : null,
    [session, view, navigate],
  );

  if (state.status !== 'ready' || !session || !value) {
    return (
      <ThemeProvider>
        <div className="dashboard-app flex min-h-screen items-center justify-center px-6">
          <section className="dashboard-panel w-full max-w-md rounded-2xl border p-7 shadow-lg" aria-live="polite">
            <p className="mb-2 text-sm font-bold text-emerald-700">CTU-G Workspace</p>
            {state.status === 'loading' && (
              <><h1 className="dashboard-heading text-xl font-semibold">Checking your session…</h1>
                <p className="dashboard-muted mt-2 text-sm">Your workspace will appear after verification.</p></>
            )}
            {state.status === 'anonymous' && (
              <><h1 className="dashboard-heading text-xl font-semibold">Sign in required</h1>
                <p className="dashboard-muted mt-2 text-sm">Sign in using an approved, active Workspace account.</p>
                <a className="dashboard-primary-link mt-5 inline-flex rounded-lg px-4 py-2 text-sm font-medium" href="/#login">Return to sign-in</a></>
            )}
            {state.status === 'error' && (
              <><h1 className="dashboard-heading text-xl font-semibold">Session unavailable</h1>
                <p role="alert" className="dashboard-muted mt-2 text-sm">We could not verify your session.</p>
                <button type="button" className="dashboard-primary-link mt-5 rounded-lg px-4 py-2 text-sm font-medium"
                  onClick={() => { setState({ status: 'loading' }); setRefresh((v) => v + 1); }}>
                  Try again
                </button></>
            )}
          </section>
        </div>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider>
      <DashboardContext.Provider value={value}>
        <DashboardShell
          session={session}
          view={view}
          navigate={navigate}
          signOut={signOut}
          signingOut={signingOut}
          signOutError={signOutError}
        >
          {children}
        </DashboardShell>
      </DashboardContext.Provider>
    </ThemeProvider>
  );
}
