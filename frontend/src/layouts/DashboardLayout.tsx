import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import '../css/theme.css';
import '../css/dashboard.css';
import ThemeProvider from '../contexts/ThemeProvider';
import { DashboardContext } from '../contexts/DashboardContext';
import type { DashboardSubpage } from '../contexts/DashboardContext';
import DashboardShell from '../components/dashboard/DashboardShell';
import { getWorkspaceSession, switchWorkspaceRole } from '../features/auth/session';
import { ROLE_CONTEXT_SWITCHING_ENABLED } from '../features/dashboard/roleContextConfig';
import { signOutMessage, signOutWorkspace } from '../features/auth/signOut';
import { useSessionRevalidation } from '../hooks/useSessionRevalidation';
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
  // WF-01.06 P-05: a session this tab was using has ended (expiry, sign-out elsewhere,
  // lost eligibility). The server gives no reason; only this tab's history does.
  | { status: 'ended' }
  | { status: 'error' }
  | { status: 'ready'; session: AuthenticatedWorkspaceSession };

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ScreenState>({ status: 'loading' });
  const [refresh, setRefresh] = useState(0);
  const [view, setView] = useState<DashboardView>(() => getDashboardView(window.location.search));
  const [search, setSearch] = useState(() => window.location.search);
  const [subpage, setSubpage] = useState<DashboardSubpage | null>(null);
  const [signingOut, setSigningOut] = useState(false);
  const [signOutError, setSignOutError] = useState('');
  const [switchingRole, setSwitchingRole] = useState(false);
  const [roleSwitchError, setRoleSwitchError] = useState('');

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
    const onHistory = () => {
      setView(getDashboardView(window.location.search));
      setSearch(window.location.search);
    };
    window.addEventListener('popstate', onHistory);
    return () => window.removeEventListener('popstate', onHistory);
  }, []);

  const navigate = useCallback((next: DashboardView) => {
    if (state.status !== 'ready' || !canOpenDashboardView(next, state.session.permissions)) return;
    const nextUrl = getDashboardHref(next);
    window.history.pushState(null, '', nextUrl);
    setView(next);
    setSearch(window.location.search);
    setSubpage(null);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [state]);

  // A page inside the current view (WF-02.02 applicant detail). Only adds query parameters to
  // the same, already-permitted view; the view itself and every API call stay server-checked.
  const openSubpage = useCallback((params: Record<string, string> | null) => {
    const base = getDashboardHref(view);
    const extra = params ? new URLSearchParams(params).toString() : '';
    const nextUrl = extra ? `${base}${base.includes('?') ? '&' : '?'}${extra}` : base;
    window.history.pushState(null, '', nextUrl);
    setSearch(window.location.search);
    if (!params) setSubpage(null);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, [view]);

  // WF-01.04 P-02/P-03/P-04: re-read the server session when another tab signs
  // out, this tab becomes visible, a cached page is restored, or a protected API
  // answers 401. Only an anonymous answer replaces the shell; a failed read keeps
  // the current view (the backend still refuses every protected request).
  const rechecking = useRef(false);
  const recheckSession = useCallback(() => {
    if (rechecking.current) return;
    rechecking.current = true;
    getWorkspaceSession()
      .then((session) => setState((previous) => {
        if (session.authenticated) return { status: 'ready', session };
        // Dropping the ready state also drops every account detail and permission hint.
        return previous.status === 'ready' || previous.status === 'ended' ? { status: 'ended' } : { status: 'anonymous' };
      }))
      .catch(() => { /* keep the current view */ })
      .finally(() => { rechecking.current = false; });
  }, []);
  useSessionRevalidation(recheckSession);

  const signOut = useCallback(async () => {
    if (signingOut) return;
    setSigningOut(true);
    setSignOutError('');
    const outcome = await signOutWorkspace();
    if (outcome === 'signed_out') {
      // Replace the history entry so Back does not return to the dashboard.
      window.location.replace('/');
      return;
    }
    setSignOutError(signOutMessage(outcome));
    setSigningOut(false);
  }, [signingOut]);

  const switchRole = useCallback(async (roleId: number) => {
    if (!ROLE_CONTEXT_SWITCHING_ENABLED || switchingRole || state.status !== 'ready'
        || !state.session.role_context?.choices.some((r) => r.role_id === roleId)) return;
    setSwitchingRole(true);
    setRoleSwitchError('');
    try {
      const updated = await switchWorkspaceRole(roleId);
      // Use only freshly returned server permission hints after a confirmed switch.
      setState({ status: 'ready', session: updated });
      window.history.replaceState(null, '', getDashboardHref('overview'));
      setView('overview');
      setSearch(window.location.search);
      setSubpage(null);
    } catch {
      // A POST outcome may be ambiguous; refresh from server before trusting it.
      setRoleSwitchError('Role switch not confirmed. Check your session and try again.');
      recheckSession();
    } finally {
      setSwitchingRole(false);
    }
  }, [switchingRole, state, recheckSession]);

  const session = state.status === 'ready' ? state.session : null;
  const value = useMemo(
    () => session ? { session, view, navigate, search, openSubpage, subpage, setSubpage } : null,
    [session, view, navigate, search, openSubpage, subpage],
  );

  if (state.status !== 'ready' || !session || !value) {
    return (
      <ThemeProvider>
        <div className="dashboard-app flex min-h-screen items-center justify-center px-6">
          <section className="dashboard-panel w-full max-w-md rounded-2xl border p-7 shadow-lg" aria-live="polite">
            <p className="dashboard-accent mb-2 text-sm font-bold">CTU-G Workspace</p>
            {state.status === 'loading' && (
              <><h1 className="dashboard-heading text-xl font-semibold">Checking your session…</h1>
                <p className="dashboard-muted mt-2 text-sm">Your workspace will appear after verification.</p></>
            )}
            {(state.status === 'anonymous' || state.status === 'ended') && (
              <><h1 className="dashboard-heading text-xl font-semibold">Sign in required</h1>
                <p role="status" className="dashboard-muted mt-2 text-sm">
                  {state.status === 'ended'
                    ? 'Your session has ended. Sign in again to continue.'
                    : 'Sign in using an approved, active Workspace account.'}
                </p>
                <a className="dashboard-primary-link mt-5 inline-flex min-h-11 items-center rounded-lg px-4 py-2 text-sm font-medium" href="/#login">Return to sign-in</a></>
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
          viewPermitted={canOpenDashboardView(view, session.permissions)}
          subpage={subpage}
          openSubpage={openSubpage}
          navigate={navigate}
          signOut={signOut}
          signingOut={signingOut}
          signOutError={signOutError}
          switchingRole={switchingRole}
          roleSwitchError={roleSwitchError}
          switchRole={(roleId) => { void switchRole(roleId); }}
        >
          {children}
        </DashboardShell>
      </DashboardContext.Provider>
    </ThemeProvider>
  );
}
