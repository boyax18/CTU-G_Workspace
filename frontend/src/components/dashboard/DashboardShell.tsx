/** The single reusable dashboard shell (docs/design Dashboard Shell v0.1 §2 wireframe).
 *
 *  ┌ Global header (full width): brand │ academic period │ theme │ profile menu ┐
 *  ├ Sidebar ─────────┬ Breadcrumb / academic period context row ───────────────┤
 *  │ Dashboard        │ Page title (+ quick action)                             │
 *  │ Grouped modules  │ Module outlet (cards, tables, forms, empty states)      │
 *  │ Profile/Settings │                                                         │
 *  │ Sign out         │                                                         │
 *  └──────────────────┴─────────────────────────────────────────────────────────┘
 *
 * The sidebar is persistent and collapsible at lg+, and an off-canvas drawer with a focus trap
 * below lg. Every role uses this same shell; only the permission-filtered registry differs.
 * Search and Alerts from the wireframe are omitted until their workflows exist (v0.1 §5: an
 * unfinished module must not look like a working feature).
 */
import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import type { AuthenticatedWorkspaceSession } from '../../features/auth/session';
import type { DashboardSubpage } from '../../contexts/DashboardContext';
import type { DashboardView } from '../../features/dashboard/navigation';
import { getDashboardItem, getVisibleNavGroups } from '../../features/dashboard/navigation';
import ThemeToggle from '../common/ThemeToggle';
import logo from '../../assets/logo.png';
import DashboardNavigation, { DashboardNavLink } from './DashboardNavigation';
import DashboardIcon from './DashboardIcon';
import PageHeader, { Breadcrumbs } from './PageHeader';
import UserMenu from './UserMenu';

interface Props {
  children: ReactNode;
  session: AuthenticatedWorkspaceSession;
  view: DashboardView;
  /** Whether the session may open `view`; a denied view gets a neutral title. */
  viewPermitted: boolean;
  /** A page inside the view (fourth breadcrumb and description), or null. */
  subpage: DashboardSubpage | null;
  openSubpage: (params: Record<string, string> | null) => void;
  navigate: (next: DashboardView) => void;
  signOut: () => Promise<void>;
  signingOut: boolean;
  signOutError: string;
}

const DESKTOP = '(min-width: 1024px)';
const PERIOD_HINT = 'The active school year and semester appear here once academic periods are configured.';
const iconButton = 'dashboard-topbar-icon rounded-lg p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';

function AcademicPeriod({ className }: { className: string }) {
  return (
    <p className={`dashboard-muted items-center gap-2 text-xs ${className}`} title={PERIOD_HINT}>
      <DashboardIcon name="calendar" width={15} height={15} />
      <span>Academic period: <span className="dashboard-heading font-medium">not yet configured</span></span>
    </p>
  );
}

export default function DashboardShell({
  children, session, view, viewPermitted, subpage, openSubpage, navigate, signOut, signingOut, signOutError,
}: Props) {
  const [mobileOpen, setMobileOpen] = useState(false);
  // Desktop expand/collapse lives in memory only (only the theme may use localStorage).
  const [collapsed, setCollapsed] = useState(false);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const sidebar = useRef<HTMLElement>(null);
  const returnFocus = useRef(false);
  const item = getDashboardItem(view);
  const roles = session.account.roles.join(' · ') || 'Assigned account';
  const utilities = getVisibleNavGroups(session.permissions, 'utility').flatMap((group) => group.items);

  const closeDrawer = (restore: boolean) => {
    returnFocus.current = restore;
    setMobileOpen(false);
  };

  useEffect(() => {
    if (!mobileOpen) {
      // Header and content are inert while the drawer is open, so focus returns after it closes.
      if (returnFocus.current) menuButton.current?.focus();
      returnFocus.current = false;
      return;
    }
    closeButton.current?.focus();
    const onEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      returnFocus.current = true;
      setMobileOpen(false);
    };
    // The drawer exists only below lg; growing the window closes it and releases the trap.
    const desktop = window.matchMedia(DESKTOP);
    const onResize = () => { if (desktop.matches) setMobileOpen(false); };
    window.addEventListener('keydown', onEscape);
    desktop.addEventListener('change', onResize);
    return () => {
      window.removeEventListener('keydown', onEscape);
      desktop.removeEventListener('change', onResize);
    };
  }, [mobileOpen]);

  // Keep keyboard focus inside the open drawer (v0.1 §6: focus trap).
  const trapFocus = (event: KeyboardEvent<HTMLElement>) => {
    if (!mobileOpen || event.key !== 'Tab' || !sidebar.current) return;
    const focusable = [...sidebar.current.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')];
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
  };

  const goTo = (next: DashboardView) => {
    navigate(next);
    closeDrawer(false);
  };

  const rail = collapsed;
  const title = viewPermitted ? item.label : 'Section unavailable';

  return (
    <div className="dashboard-app min-h-screen">
      <a href="#workspace-main" className="dashboard-skip-link">Skip to main content</a>

      <header inert={mobileOpen}
        className="dashboard-topbar sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b px-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <button
            ref={menuButton}
            type="button"
            className={`${iconButton} inline-flex lg:hidden`}
            aria-label="Open navigation"
            aria-controls="workspace-sidebar"
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen(true)}
          >
            <DashboardIcon name="menu" />
          </button>
          <button
            type="button"
            className={`${iconButton} hidden lg:inline-flex`}
            aria-label={rail ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-controls="workspace-sidebar"
            aria-expanded={!rail}
            onClick={() => setCollapsed((value) => !value)}
          >
            <DashboardIcon name="sidebar" />
          </button>
          <div className="flex min-w-0 items-center gap-3">
            <img src={logo} alt="" className="h-9 w-9 shrink-0 rounded-lg bg-white object-contain p-0.5 shadow-sm" />
            <div className="min-w-0">
              <p className="dashboard-heading truncate text-sm font-bold sm:text-base">CTU-G Workspace</p>
              <p className="dashboard-muted hidden text-xs sm:block">Ginatilan Campus</p>
            </div>
          </div>
          <AcademicPeriod className="dashboard-identity ml-2 hidden border-l pl-4 md:flex" />
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden sm:block"><ThemeToggle /></div>
          <UserMenu
            schoolId={session.account.school_id}
            roles={roles}
            items={utilities}
            navigate={goTo}
            signOut={() => { void signOut(); }}
            signingOut={signingOut}
          />
        </div>
      </header>

      {mobileOpen && (
        <button
          type="button"
          tabIndex={-1}
          className="dashboard-scrim fixed inset-0 z-40 lg:hidden"
          aria-label="Close navigation overlay"
          onClick={() => closeDrawer(true)}
        />
      )}

      <aside
        ref={sidebar}
        id="workspace-sidebar"
        aria-label="Workspace sidebar"
        onKeyDown={trapFocus}
        className={`dashboard-sidebar fixed bottom-0 left-0 top-0 z-50 flex w-[272px] flex-col overflow-y-auto px-4 py-5 transition-[transform,width] duration-200 lg:top-16 lg:translate-x-0 ${rail ? 'lg:w-20 lg:px-3' : ''} ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        {/* Drawer header (below lg only): the global header holds the brand on desktop. */}
        <div className="mb-6 flex items-center gap-3 px-2 lg:hidden">
          <img src={logo} alt="" className="h-10 w-10 shrink-0 rounded-xl bg-white object-contain p-1" />
          <div className="min-w-0 flex-1">
            <p className="dashboard-sidebar-strong truncate text-base font-bold">CTU-G Workspace</p>
            <p className="dashboard-nav-group text-xs">Ginatilan Campus</p>
          </div>
          <button
            ref={closeButton}
            type="button"
            className="dashboard-nav-link rounded-md p-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--db-focus)]"
            onClick={() => closeDrawer(true)}
            aria-label="Close navigation"
          >
            <DashboardIcon name="close" />
          </button>
        </div>

        <DashboardNavigation permissions={session.permissions} active={view} navigate={goTo} collapsed={rail} />

        <div className="dashboard-sidebar-divider mt-auto border-t pt-4">
          <div role="group" aria-label="Account" className="mb-3 space-y-1">
            {utilities.map((entry) => (
              <DashboardNavLink key={entry.id} item={entry} active={view} navigate={goTo} collapsed={rail} />
            ))}
          </div>
          <div className={`dashboard-sidebar-card mb-3 rounded-xl px-3 py-3 ${rail ? 'lg:hidden' : ''}`}>
            <p className="dashboard-sidebar-strong truncate text-sm font-semibold">{session.account.school_id}</p>
            <p className="dashboard-nav-group mt-1 text-xs">{roles}</p>
          </div>
          <button
            type="button"
            className={`dashboard-nav-link flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-[color:var(--db-focus)] disabled:opacity-50 ${rail ? 'lg:justify-center' : ''}`}
            onClick={() => { void signOut(); }}
            disabled={signingOut}
            title={rail ? 'Sign out' : undefined}
          >
            <DashboardIcon name="signout" />
            <span className={rail ? 'lg:sr-only' : ''}>{signingOut ? 'Signing out…' : 'Sign out'}</span>
          </button>
          {signOutError && <p role="alert" className="dashboard-error mt-2 px-3 text-xs">{signOutError}</p>}
        </div>
      </aside>

      <div inert={mobileOpen} className={`transition-[margin] duration-200 ${rail ? 'lg:ml-20' : 'lg:ml-[272px]'}`}>
        <main id="workspace-main" className="mx-auto w-full max-w-[1500px] space-y-6 p-4 sm:p-6 lg:p-10" tabIndex={-1}>
          <div className="space-y-3">
            {/* Breadcrumb / context row (v0.1 §2): location plus the academic-period context. */}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <Breadcrumbs view={viewPermitted ? view : 'overview'} navigate={goTo}
                subpage={viewPermitted ? subpage?.label ?? null : null} onViewCrumb={() => openSubpage(null)} />
              <AcademicPeriod className="flex md:hidden" />
            </div>
            <PageHeader
              title={title}
              description={viewPermitted ? subpage?.description ?? item.description : undefined}
              status={viewPermitted && item.integration === 'planned'
                ? <span className="dashboard-muted rounded-full border px-2 py-0.5 text-xs font-medium">Soon</span> : undefined}
            />
          </div>
          {children}
        </main>
        <footer className="dashboard-muted px-4 pb-6 text-center text-xs sm:px-6">
          CTU-G Workspace · Shared campus dashboard
        </footer>
      </div>
    </div>
  );
}
