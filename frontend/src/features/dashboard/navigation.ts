/**
 * Shared CTU-G Workspace navigation.
 * Permission codes are backend-provided, point-in-time hints, never authority.
 * Module destinations intentionally render a safe placeholder until approved APIs exist.
 */
export type DashboardView =
  | 'overview'
  | 'account'
  | 'registration-review'
  | 'finance'
  | 'clearance'
  | 'academic'
  | 'announcements';

export type DashboardNavSection = 'workspace' | 'modules';

export interface DashboardNavItem {
  id: DashboardView;
  label: string;
  icon: 'home' | 'user' | 'users' | 'wallet' | 'clipboard' | 'book' | 'bell';
  section: DashboardNavSection;
  /** Any one of these exact backend permission codes must appear in session.permissions. */
  requiredAny?: readonly string[];
  /** The shell exists; the feature's live API/page is not connected. */
  integration: 'shell' | 'planned';
}

export const DASHBOARD_NAV_ITEMS: readonly DashboardNavItem[] = [
  { id: 'overview', label: 'Overview', icon: 'home', section: 'workspace', integration: 'shell' },
  { id: 'account', label: 'My account', icon: 'user', section: 'workspace', integration: 'shell' },
  {
    id: 'registration-review', label: 'Registration review', icon: 'users', section: 'modules',
    requiredAny: ['accounts.registration_requests.read'], integration: 'planned',
  },
  {
    id: 'finance', label: 'Finance & payments', icon: 'wallet', section: 'modules',
    requiredAny: ['finance.payments.self.read', 'finance.summary.read', 'finance.payments.read'],
    integration: 'planned',
  },
  {
    id: 'clearance', label: 'Clearance', icon: 'clipboard', section: 'modules',
    requiredAny: ['clearance.requests.self.read', 'clearance.requests.assigned.read'],
    integration: 'planned',
  },
  {
    id: 'academic', label: 'Academic information', icon: 'book', section: 'modules',
    requiredAny: ['academic.catalogue.read', 'academic.profile.self.read', 'academic.advisees.read'],
    integration: 'planned',
  },
  {
    id: 'announcements', label: 'Announcements', icon: 'bell', section: 'modules',
    requiredAny: ['announcements.read'], integration: 'planned',
  },
];

export function getVisibleDashboardItems(permissions: readonly string[]): DashboardNavItem[] {
  const grants = new Set(permissions);
  return DASHBOARD_NAV_ITEMS.filter(
    (item) => !item.requiredAny || item.requiredAny.some((code) => grants.has(code)),
  );
}

export function canOpenDashboardView(view: DashboardView, permissions: readonly string[]): boolean {
  return getVisibleDashboardItems(permissions).some((item) => item.id === view);
}

export function getDashboardView(search: string): DashboardView {
  const candidate = new URLSearchParams(search).get('view');
  if (!candidate) return 'overview';
  const item = DASHBOARD_NAV_ITEMS.find((entry) => entry.id === candidate);
  return item?.id ?? 'overview';
}

export function getDashboardHref(view: DashboardView): string {
  return view === 'overview' ? '/dashboard' : `/dashboard?view=${encodeURIComponent(view)}`;
}
