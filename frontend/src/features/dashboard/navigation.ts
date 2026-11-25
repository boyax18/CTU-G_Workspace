/**
 * Shared CTU-G Workspace navigation registry (Dashboard Shell v0.1, docs/design).
 *
 * One registry drives the sidebar, breadcrumbs, page headers and overview links. Groups follow
 * the v0.1 role proposals, but visibility is computed ONLY from the backend's effective
 * permission codes (session.permissions) — never from role names. Every code below exists in the
 * implemented permission catalogue (backend/apps/access_control/catalogue/v2_0.json); proposed
 * links with no catalogue code yet (Account Concerns, Integration Status, Role Management,
 * Operational Reports, Academic Period) are deliberately absent rather than invented.
 * Permission codes are point-in-time hints; Django authorizes every request.
 */
import { PENDING_APPLICATIONS_LIST_ENABLED } from '../admin/pendingApplicationsConfig.ts';
import { ACCOUNT_DIRECTORY_ENABLED } from '../admin/accountStatusConfig.ts';
import { ROLE_ASSIGNMENT_ENABLED } from '../access-control/roleAssignmentConfig.ts';
import { APPOINTMENT_MANAGEMENT_ENABLED } from '../access-control/appointmentManagementConfig.ts';
import { ROLE_PERMISSION_MANAGEMENT_ENABLED } from '../access-control/rolePermissionConfig.ts';
import { ACCOUNT_GRANTS_ENABLED } from '../access-control/accountGrantConfig.ts';
import { ACCOUNT_RESTRICTIONS_ENABLED } from '../access-control/accountRestrictionConfig.ts';
import { EFFECTIVE_ACCESS_INSPECT_ENABLED } from '../access-control/effectiveAccessConfig.ts';
import { ACCESS_AUDIT_ENABLED } from '../access-control/accessAuditConfig.ts';
import { ACADEMIC_PERIODS_ENABLED } from '../academic/academicPeriodsConfig.ts';

export type DashboardView =
  | 'overview'
  | 'account'
  | 'account-settings'
  // Account operations
  | 'registration-review'
  | 'account-directory'
  | 'appointment-evidence'
  // Academic (own)
  | 'my-subjects'
  | 'my-clearance'
  // Finance (own)
  | 'my-payments'
  // Teaching and clearance duties
  | 'student-lists'
  | 'clearance-reviews'
  | 'group-rating'
  // Financial management
  | 'fee-obligations'
  | 'student-fee-records'
  | 'payments'
  | 'receipts'
  | 'expenses'
  | 'financial-reports'
  // School configuration and oversight
  | 'school-periods'
  | 'academic-references'
  | 'clearance-monitoring'
  // Campus
  | 'announcements'
  | 'notifications'
  // Access control and Security (governance)
  | 'role-assignments'
  | 'role-permissions'
  | 'account-overrides'
  | 'account-restrictions'
  | 'permission-catalogue'
  | 'service-management'
  | 'access-audit'
  | 'access-reviews'
  | 'system-health';

export type DashboardNavGroupId =
  | 'overview'
  | 'account-operations'
  | 'academic'
  | 'finance'
  | 'teaching'
  | 'clearance'
  | 'academic-services'
  | 'financial-management'
  | 'reports'
  | 'academic-configuration'
  | 'clearance-oversight'
  | 'campus'
  | 'access-control'
  | 'security-audit'
  | 'system-operations'
  | 'account';

export type DashboardIconName =
  | 'home' | 'user' | 'users' | 'wallet' | 'clipboard' | 'book' | 'bell' | 'settings'
  | 'calendar' | 'chart' | 'receipt' | 'lock' | 'key' | 'list' | 'activity' | 'star';

export interface DashboardNavGroup {
  id: DashboardNavGroupId;
  label: string;
  /** 'utility' groups render in the sidebar footer and the header user menu. */
  placement: 'main' | 'utility';
}

export interface DashboardNavItem {
  id: DashboardView;
  label: string;
  icon: DashboardIconName;
  group: DashboardNavGroupId;
  /** One sentence for the page header. */
  description: string;
  /** Any one of these exact backend permission codes must appear in session.permissions. */
  requiredAny?: readonly string[];
  /** 'shell': a working page. 'planned': labelled "Soon" and shows a not-available page. */
  integration: 'shell' | 'planned';
}

export const DASHBOARD_NAV_GROUPS: readonly DashboardNavGroup[] = [
  { id: 'overview', label: 'Overview', placement: 'main' },
  { id: 'account-operations', label: 'Account management', placement: 'main' },
  { id: 'academic', label: 'Academic', placement: 'main' },
  { id: 'finance', label: 'Finance', placement: 'main' },
  { id: 'teaching', label: 'Teaching', placement: 'main' },
  { id: 'clearance', label: 'Clearance', placement: 'main' },
  { id: 'academic-services', label: 'Academic services', placement: 'main' },
  { id: 'financial-management', label: 'Financial management', placement: 'main' },
  { id: 'reports', label: 'Reports', placement: 'main' },
  { id: 'academic-configuration', label: 'Academic configuration', placement: 'main' },
  { id: 'clearance-oversight', label: 'Clearance oversight', placement: 'main' },
  { id: 'campus', label: 'Campus', placement: 'main' },
  { id: 'access-control', label: 'Access control', placement: 'main' },
  { id: 'security-audit', label: 'Security & audit', placement: 'main' },
  { id: 'system-operations', label: 'System operations', placement: 'main' },
  { id: 'account', label: 'Account', placement: 'utility' },
];

const planned = 'planned' as const;

export const DASHBOARD_NAV_ITEMS: readonly DashboardNavItem[] = [
  { id: 'overview', label: 'Dashboard', icon: 'home', group: 'overview', integration: 'shell',
    description: 'Your workspace at a glance. Modules appear according to your current access.' },

  // WF-02.01: live only when the list switch is on; Django still decides access. Decision controls
  // appear inside the page only when the server reports them available, so this text stays neutral.
  { id: 'registration-review', label: 'Applicant reviews', icon: 'users', group: 'account-operations',
    requiredAny: ['accounts.registration_requests.read'],
    integration: PENDING_APPLICATIONS_LIST_ENABLED ? 'shell' : planned,
    description: 'Pending Student and Instructor applications waiting for School Admin review.' },
  { id: 'account-directory', label: 'Account directory', icon: 'list', group: 'account-operations',
    // WF-02.05 (D-69, D-70): live only when its switch is on; Django still decides access.
    requiredAny: ['accounts.school_accounts.read'], integration: ACCOUNT_DIRECTORY_ENABLED ? 'shell' : planned,
    description: 'Eligible school accounts and their status.' },

  // D-112: recording/reviewing campus appointment evidence is SCHOOL operation,
  // not Access Control Management. Exact stored permissions drive visibility.
  { id: 'appointment-evidence', label: 'Appointment evidence', icon: 'clipboard', group: 'account-operations',
    requiredAny: ['access_control.appointments.record', 'access_control.appointments.verify'],
    integration: APPOINTMENT_MANAGEMENT_ENABLED ? 'shell' : planned,
    description: 'Record and independently review official appointments; never assign roles here.' },

  { id: 'my-subjects', label: 'My subjects', icon: 'book', group: 'academic',
    requiredAny: ['academic.profile.self.read'], integration: planned,
    description: 'Your academic profile and the subjects you submitted for the current period.' },
  { id: 'my-clearance', label: 'My clearance', icon: 'clipboard', group: 'academic',
    requiredAny: ['clearance.requests.self.read'], integration: planned,
    description: 'Your clearance requests and their progress.' },

  { id: 'my-payments', label: 'Payments & receipts', icon: 'wallet', group: 'finance',
    requiredAny: ['finance.payments.self.read', 'finance.receipts.self.read'], integration: planned,
    description: 'Your organizational-fee payments and receipts.' },

  { id: 'student-lists', label: 'Student lists', icon: 'users', group: 'teaching',
    requiredAny: ['academic.advisees.read'], integration: planned,
    description: 'Students assigned to you.' },

  { id: 'clearance-reviews', label: 'Clearance reviews', icon: 'clipboard', group: 'clearance',
    requiredAny: ['clearance.requests.assigned.read'], integration: planned,
    description: 'Clearance requests assigned to you for review.' },

  { id: 'group-rating', label: 'Group rating', icon: 'star', group: 'academic-services',
    requiredAny: ['group_rating.sheets.assigned.read'], integration: planned,
    description: 'Rating sheets for your assigned classes.' },

  { id: 'fee-obligations', label: 'Fee obligations', icon: 'calendar', group: 'financial-management',
    requiredAny: ['finance.fee_schedule.manage'], integration: planned,
    description: 'Organizational-fee schedules for each academic period.' },
  { id: 'student-fee-records', label: 'Student fee records', icon: 'list', group: 'financial-management',
    requiredAny: ['finance.ledger.read'], integration: planned,
    description: 'The working ledger of student fee records.' },
  { id: 'payments', label: 'Payments', icon: 'wallet', group: 'financial-management',
    requiredAny: ['finance.payments.read'], integration: planned,
    description: 'Recorded organizational-fee payments.' },
  { id: 'receipts', label: 'Receipts', icon: 'receipt', group: 'financial-management',
    requiredAny: ['finance.receipts.issue'], integration: planned,
    description: 'Payment receipts issued to students.' },
  { id: 'expenses', label: 'Expenses', icon: 'receipt', group: 'financial-management',
    requiredAny: ['finance.expenses.record'], integration: planned,
    description: 'Recorded organization expenses.' },

  { id: 'financial-reports', label: 'Financial reports', icon: 'chart', group: 'reports',
    requiredAny: ['reports.financial.drafts.read', 'reports.financial.final.read'], integration: planned,
    description: 'Draft and finalized financial reports.' },

  // WF-11.01 (restricted local development): Draft management only; live only when its switch is on.
  // Django still decides access (academic.periods.manage, Admin role context, Deny precedence).
  { id: 'school-periods', label: 'School years & semesters', icon: 'calendar', group: 'academic-configuration',
    requiredAny: ['academic.periods.manage'], integration: ACADEMIC_PERIODS_ENABLED ? 'shell' : planned,
    description: 'School years, semesters and their dates.' },
  { id: 'academic-references', label: 'Academic references', icon: 'book', group: 'academic-configuration',
    requiredAny: ['academic.courses.manage', 'academic.sections.manage'], integration: planned,
    description: 'Course, year-level and section definitions.' },

  { id: 'clearance-monitoring', label: 'Clearance monitoring', icon: 'activity', group: 'clearance-oversight',
    requiredAny: ['clearance.progress.read'], integration: planned,
    description: 'School-wide clearance progress.' },

  { id: 'announcements', label: 'Announcements', icon: 'bell', group: 'campus',
    requiredAny: ['announcements.read'], integration: planned,
    description: 'Official campus announcements.' },
  { id: 'notifications', label: 'Notifications', icon: 'bell', group: 'campus',
    requiredAny: ['notifications.read_state.self.read'], integration: planned,
    description: 'Your announcement notifications.' },

  { id: 'role-assignments', label: 'Role assignments', icon: 'users', group: 'access-control',
    // WF-03.01 (D-86, D-87): live only when its switch is on; Django still decides access.
    requiredAny: ['access_control.admin_assignments.manage'], integration: ROLE_ASSIGNMENT_ENABLED ? 'shell' : planned,
    description: 'School Admin assignments and separately gated ordinary role responsibilities.' },
  { id: 'role-permissions', label: 'Role permissions', icon: 'key', group: 'access-control',
    requiredAny: ['access_control.role_permissions.manage'], integration: ROLE_PERMISSION_MANAGEMENT_ENABLED ? 'shell' : planned,
    description: 'Permissions granted to ordinary roles.' },
  { id: 'account-overrides', label: 'Account overrides', icon: 'key', group: 'access-control',
    requiredAny: ['access_control.account_permissions.manage'], integration: ACCOUNT_GRANTS_ENABLED ? 'shell' : planned,
    description: 'Individual role-bound Grants (Deny and removal follow in WF-03.04).' },
  { id: 'account-restrictions', label: 'Account restrictions', icon: 'lock', group: 'access-control',
    requiredAny: ['access_control.account_permissions.manage'], integration: ACCOUNT_RESTRICTIONS_ENABLED ? 'shell' : planned,
    description: 'Deny an individual permission, revoke a direct Grant, or remove a Deny.' },
  { id: 'permission-catalogue', label: 'Permission catalogue', icon: 'list', group: 'access-control',
    requiredAny: ['access_control.catalogue.read'], integration: planned,
    description: 'The reviewed permission and service catalogue.' },
  { id: 'service-management', label: 'Service management', icon: 'settings', group: 'access-control',
    requiredAny: ['access_control.services.activation.manage'], integration: planned,
    description: 'Service activation under protected governance.' },

  { id: 'access-audit', label: 'Access audit logs', icon: 'lock', group: 'security-audit',
    requiredAny: ['access_control.audit.read'], integration: ACCESS_AUDIT_ENABLED ? 'shell' : planned,
    description: 'Access-control audit history.' },
  { id: 'access-reviews', label: 'Access reviews', icon: 'lock', group: 'security-audit',
    requiredAny: ['access_control.effective_permissions.inspect'], integration: EFFECTIVE_ACCESS_INSPECT_ENABLED ? 'shell' : planned,
    description: 'Inspect an account’s effective permissions.' },

  { id: 'system-health', label: 'System health', icon: 'activity', group: 'system-operations',
    requiredAny: ['access_control.diagnostics.read'], integration: planned,
    description: 'Redacted technical diagnostics.' },

  { id: 'account', label: 'My profile', icon: 'user', group: 'account', integration: 'shell',
    description: 'Read-only details from your verified session.' },
  { id: 'account-settings', label: 'Account settings', icon: 'settings', group: 'account',
    requiredAny: ['accounts.profile.self.update'], integration: planned,
    description: 'Update your personal details.' },
];

export function getVisibleDashboardItems(permissions: readonly string[]): DashboardNavItem[] {
  const grants = new Set(permissions);
  return DASHBOARD_NAV_ITEMS.filter(
    (item) => !item.requiredAny || item.requiredAny.some((code) => grants.has(code)),
  );
}

export interface VisibleNavGroup extends DashboardNavGroup {
  items: DashboardNavItem[];
}

/** Groups in registry order with their visible items; a group with no visible item is hidden. */
export function getVisibleNavGroups(
  permissions: readonly string[],
  placement: DashboardNavGroup['placement'] = 'main',
): VisibleNavGroup[] {
  const visible = getVisibleDashboardItems(permissions);
  return DASHBOARD_NAV_GROUPS
    .filter((group) => group.placement === placement)
    .map((group) => ({ ...group, items: visible.filter((item) => item.group === group.id) }))
    .filter((group) => group.items.length > 0);
}

export function getDashboardItem(view: DashboardView): DashboardNavItem {
  return DASHBOARD_NAV_ITEMS.find((item) => item.id === view) ?? DASHBOARD_NAV_ITEMS[0];
}

export function getDashboardGroup(view: DashboardView): DashboardNavGroup {
  const item = getDashboardItem(view);
  return DASHBOARD_NAV_GROUPS.find((group) => group.id === item.group) ?? DASHBOARD_NAV_GROUPS[0];
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
