import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { AuthenticatedWorkspaceSession } from '../../features/auth/session';
import type { DashboardView } from '../../features/dashboard/navigation';
import { DASHBOARD_NAV_ITEMS } from '../../features/dashboard/navigation';
import ThemeToggle from '../common/ThemeToggle';
import logo from '../../assets/logo.png';
import DashboardNavigation from './DashboardNavigation';
import DashboardIcon from './DashboardIcon';

interface Props {
  children: ReactNode;
  session: AuthenticatedWorkspaceSession;
  view: DashboardView;
  navigate: (next: DashboardView) => void;
  signOut: () => Promise<void>;
  signingOut: boolean;
  signOutError: string;
}

export default function DashboardShell({
  children, session, view, navigate, signOut, signingOut, signOutError,
}: Props) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const title = DASHBOARD_NAV_ITEMS.find((item) => item.id === view)?.label ?? 'Overview';
  const roles = session.account.roles.join(' · ') || 'Assigned account';

  useEffect(() => {
    if (!mobileOpen) return;
    closeButton.current?.focus();
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpen(false);
        menuButton.current?.focus();
      }
    };
    window.addEventListener('keydown', onEscape);
    return () => window.removeEventListener('keydown', onEscape);
  }, [mobileOpen]);

  const goTo = (next: DashboardView) => {
    navigate(next);
    setMobileOpen(false);
  };

  return (
    <div className="dashboard-app min-h-screen">
      <a href="#workspace-main" className="dashboard-skip-link">Skip to main content</a>

      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-[#09271b]/70 lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        aria-label="Workspace sidebar"
        className={`dashboard-sidebar fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col overflow-y-auto px-4 py-5 transition-transform duration-200 lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="mb-9 flex items-center gap-3 px-2">
          <img src={logo} alt="" className="h-10 w-10 rounded-xl bg-white object-contain p-1" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[15px] font-bold text-white">CTU-G Workspace</p>
            <p className="text-[11px] text-emerald-100/75">Ginatilan Campus</p>
          </div>
          <button
            ref={closeButton}
            type="button"
            className="rounded-md p-2 text-emerald-100 hover:bg-white/10 lg:hidden"
            onClick={() => { setMobileOpen(false); menuButton.current?.focus(); }}
            aria-label="Close sidebar"
          >
            <DashboardIcon name="close" />
          </button>
        </div>

        <DashboardNavigation permissions={session.permissions} active={view} navigate={goTo} />
        <div className="mt-auto border-t border-white/15 pt-5">
          <div className="mb-4 rounded-xl border border-white/15 bg-white/8 px-3 py-3">
            <p className="truncate text-[13px] font-semibold text-white">{session.account.school_id}</p>
            <p className="mt-1 text-xs text-emerald-100/80">{roles}</p>
          </div>
          <button
            type="button"
            className="flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-emerald-50 transition-colors hover:bg-white/10 disabled:opacity-60"
            onClick={() => { void signOut(); }}
            disabled={signingOut}
          >
            <DashboardIcon name="signout" />
            {signingOut ? 'Signing out…' : 'Sign out'}
          </button>
          {signOutError && <p role="alert" className="mt-2 px-3 text-xs text-red-100">{signOutError}</p>}
        </div>
      </aside>

      <div className="min-h-screen lg:ml-[272px]">
        <header className="dashboard-topbar sticky top-0 z-30 flex h-[76px] items-center justify-between gap-4 border-b px-4 sm:px-6 lg:px-10">
          <div className="flex min-w-0 items-center gap-3">
            <button
              ref={menuButton}
              type="button"
              className="dashboard-topbar-icon rounded-lg p-2 lg:hidden"
              aria-label="Open sidebar"
              aria-expanded={mobileOpen}
              onClick={() => setMobileOpen(true)}
            >
              <DashboardIcon name="menu" />
            </button>
            <div className="min-w-0">
              <p className="dashboard-muted truncate text-xs">Workspace / {title}</p>
              <h1 className="dashboard-heading truncate text-base font-bold sm:text-lg">{title}</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:block"><ThemeToggle /></div>
            <div className="dashboard-identity hidden border-l pl-3 md:block">
              <p className="text-xs font-semibold">{session.account.school_id}</p>
              <p className="dashboard-muted max-w-56 truncate text-[11px]">{roles}</p>
            </div>
          </div>
        </header>

        <main id="workspace-main" className="mx-auto w-full max-w-[1500px] p-4 sm:p-6 lg:p-10" tabIndex={-1}>
          {children}
        </main>
        <footer className="dashboard-muted px-4 pb-6 text-center text-xs sm:px-6">
          CTU-G Workspace · Shared campus dashboard
        </footer>
      </div>
    </div>
  );
}
