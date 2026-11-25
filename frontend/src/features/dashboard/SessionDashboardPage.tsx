/** Module outlet for the shared dashboard shell (Dashboard Shell v0.1 §2.1).
 * The shell renders the breadcrumbs and the page h1; views start their sections at h2.
 */
import { useDashboardContext } from '../../hooks/useDashboardContext';
import { canOpenDashboardView, getDashboardItem, getVisibleNavGroups } from './navigation';
import type { DashboardNavItem, DashboardView } from './navigation';
import type { CSSProperties } from 'react';
import campusPhoto from '../../assets/campus-building.jpg';
import DashboardIcon from '../../components/dashboard/DashboardIcon';
import EmailVerificationCard from './EmailVerificationCard';
import { AccessDenied, ModuleUnavailable, NoModules } from '../../components/dashboard/DashboardStates';
import RegistrationReviewLivePanel from '../admin/RegistrationReviewLivePanel';
import { REGISTRATION_REVIEW_LIVE_API_ENABLED } from '../admin/registrationReviewApiGate';
import PendingApplicationsPanel from '../admin/PendingApplicationsPanel';
import { PENDING_APPLICATIONS_LIST_ENABLED } from '../admin/pendingApplicationsConfig';
import AccountDirectoryPanel from '../admin/AccountDirectoryPanel';
import { ACCOUNT_DIRECTORY_ENABLED } from '../admin/accountStatusConfig';
import RoleAssignmentsPanel from '../access-control/RoleAssignmentsPanel';
import RolePermissionsPanel from '../access-control/RolePermissionsPanel';
import { ROLE_PERMISSION_MANAGEMENT_ENABLED } from '../access-control/rolePermissionConfig';
import AccountGrantsPanel from '../access-control/AccountGrantsPanel';
import { ACCOUNT_GRANTS_ENABLED } from '../access-control/accountGrantConfig';
import AccountRestrictionsPanel from '../access-control/AccountRestrictionsPanel';
import { ACCOUNT_RESTRICTIONS_ENABLED } from '../access-control/accountRestrictionConfig';
import EffectiveAccessPanel from '../access-control/EffectiveAccessPanel';
import { EFFECTIVE_ACCESS_INSPECT_ENABLED } from '../access-control/effectiveAccessConfig';
import AccessAuditPanel from '../access-control/AccessAuditPanel';
import { ACCESS_AUDIT_ENABLED } from '../access-control/accessAuditConfig';
import AppointmentManagementPanel from '../access-control/AppointmentManagementPanel';
import { APPOINTMENT_MANAGEMENT_ENABLED } from '../access-control/appointmentManagementConfig';
import { ROLE_ASSIGNMENT_ENABLED } from '../access-control/roleAssignmentConfig';
import RegistrationReviewPreview from '../admin/RegistrationReviewPreview';
import SchoolPeriodsPanel from '../academic/SchoolPeriodsPanel';
import { ACADEMIC_PERIODS_ENABLED } from '../academic/academicPeriodsConfig';
import AcademicSettingsPanel from '../academic/AcademicSettingsPanel';
import { ACADEMIC_CONFIGURATION_ENABLED } from '../academic/academicConfigurationConfig';
import SemesterFeesPanel from '../finance/SemesterFeesPanel';
import { SEMESTER_FEE_CONFIGURATION_ENABLED } from '../finance/semesterFeesConfig';
import { REGISTRATION_REVIEW_UI_PREVIEW_ENABLED } from '../admin/registrationReviewPreviewGate';

const primaryLink = 'dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';

interface Widget {
  id: string;
  view: DashboardView;
  title: string;
  body: string;
  action: string;
}

/** v0.1 §4.4: only permitted, working widgets render; no counts that the API does not provide (D-33). */
function getWidgets(permissions: readonly string[]): Widget[] {
  const widgets: Widget[] = [];
  const reviews = getDashboardItem('registration-review');
  if (canOpenDashboardView('registration-review', permissions) && reviews.integration === 'shell') {
    widgets.push({
      id: 'pending-applications', view: 'registration-review', title: 'Pending applications',
      body: 'Student and Instructor applications waiting for School Admin review.',
      action: 'Open applicant reviews',
    });
  }
  return widgets;
}

function ModuleCard({ item, onOpen }: { item: DashboardNavItem; onOpen: () => void }) {
  const soon = item.integration === 'planned';
  return (
    <button
      type="button"
      className="dashboard-glass dashboard-module-card group flex h-full flex-col rounded-2xl p-5 text-left transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]"
      onClick={onOpen}
    >
      <span className="flex w-full items-start justify-between gap-3">
        <span className="dashboard-placeholder-icon flex h-11 w-11 items-center justify-center rounded-xl">
          <DashboardIcon name={item.icon} />
        </span>
        <span className={`rounded-full border px-2 py-0.5 text-xs font-medium ${soon ? 'dashboard-muted' : 'dashboard-heading'}`}>
          {soon ? 'Soon' : 'Available'}
        </span>
      </span>
      <span className="dashboard-heading mt-4 font-semibold">{item.label}</span>
      <span className="dashboard-muted mt-1 text-sm leading-relaxed">{item.description}</span>
    </button>
  );
}

function Overview() {
  const { session, navigate } = useDashboardContext();
  const { permissions } = session;
  const currentRole = session.role_context?.choices.find(
    (r) => r.role_id === session.role_context?.active_role_id,
  );
  const displayRole = currentRole?.role_name === 'Admin' ? 'School Admin' : currentRole?.role_name;
  const widgets = getWidgets(permissions);
  const groups = getVisibleNavGroups(permissions, 'main').filter((group) => group.id !== 'overview');

  return (
    <div className="space-y-8">
      <section aria-labelledby="dashboard-welcome" className="dashboard-hero relative overflow-hidden rounded-3xl p-6 sm:p-8 lg:p-10"
        style={{ '--db-hero-photo': `url(${campusPhoto})` } as CSSProperties}>
        <div className="relative z-10 max-w-2xl">
          <p className="dashboard-hero-eyebrow text-xs font-semibold uppercase tracking-[0.18em]">Cebu Technological University · Ginatilan</p>
          <h2 id="dashboard-welcome" className="mt-4 text-2xl font-bold tracking-tight text-white sm:text-3xl">{displayRole ? `${displayRole} workspace` : 'Welcome to your workspace'}</h2>
          <p className="dashboard-hero-text mt-3 text-sm leading-relaxed">
            One shared campus dashboard. The modules below follow your current access, and every request is verified by the server.
          </p>
          <button className="dashboard-hero-button mt-6 inline-flex min-h-11 items-center rounded-xl border px-4 py-2.5 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            onClick={() => navigate('account')}>
            View my profile
          </button>
        </div>
        <div aria-hidden="true" className="dashboard-hero-ring absolute -right-20 -top-32 h-96 w-96 rounded-full" />
      </section>

      {widgets.length > 0 && (
        <section aria-labelledby="dashboard-glance">
          <h2 id="dashboard-glance" className="dashboard-heading mb-4 text-xl font-bold">At a glance</h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {widgets.map((widget) => (
              <article key={widget.id} className="dashboard-glass flex flex-col rounded-2xl p-5">
                <h3 className="dashboard-heading font-semibold">{widget.title}</h3>
                <p className="dashboard-muted mt-1 flex-1 text-sm leading-relaxed">{widget.body}</p>
                <button type="button" className={`${primaryLink} mt-4 self-start`} onClick={() => navigate(widget.view)}>
                  {widget.action}
                  <DashboardIcon name="chevron" width={15} height={15} />
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="dashboard-modules">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <h2 id="dashboard-modules" className="dashboard-heading text-xl font-bold">Your modules</h2>
          <p className="dashboard-muted text-xs">Shown from your effective permissions, never from role names.</p>
        </div>
        {groups.length === 0 ? <NoModules /> : (
          <div className="space-y-6">
            {groups.map((group) => (
              <section key={group.id} aria-labelledby={`modules-${group.id}`}>
                <h3 id={`modules-${group.id}`} className="dashboard-eyebrow mb-3">{group.label}</h3>
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                  {group.items.map((item) => (
                    <ModuleCard key={item.id} item={item} onOpen={() => navigate(item.id)} />
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function Profile() {
  const { session } = useDashboardContext();
  const { account, permissions } = session;
  return (
    <section className="dashboard-panel rounded-2xl border p-6 sm:p-8" aria-labelledby="profile-details">
      <h2 id="profile-details" className="dashboard-heading mb-6 text-lg font-semibold">Account details</h2>
      <dl className="grid gap-6 text-sm sm:grid-cols-2">
        <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">CTU-G ID</dt><dd className="dashboard-heading mt-2 font-semibold">{account.school_id}</dd></div>
        <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Assigned roles</dt><dd className="dashboard-heading mt-2 font-semibold">{account.roles.join(', ') || 'None'}</dd></div>
        {session.role_context?.enabled && (
          <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Active role context</dt>
            <dd className="dashboard-heading mt-2 font-semibold">{
              session.role_context.choices.find((r) => r.role_id === session.role_context?.active_role_id)?.role_name ?? 'Select a role'
            }</dd></div>)}
        <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Session status</dt><dd className="dashboard-heading mt-2 font-semibold">Authenticated</dd></div>
        <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Effective permission hints</dt><dd className="dashboard-heading mt-2 font-semibold">{permissions.length}</dd></div>
      </dl>
      <EmailVerificationCard />
      <p className="dashboard-muted mt-7 border-t pt-4 text-xs leading-relaxed">
        Role names and permission hints never authorize an API call. Django verifies access on every protected request.
      </p>
    </section>
  );
}

export default function SessionDashboardPage() {
  const { session, view, navigate } = useDashboardContext();
  const { permissions } = session;
  const back = () => navigate('overview');

  if (!canOpenDashboardView(view, permissions)) return <AccessDenied onBack={back} />;
  if (view === 'overview') return <Overview />;
  if (view === 'account') return <Profile />;

  if (view === 'registration-review') {
    // AR-6C7D.1: fictional mock UI only; hard-disabled pending separate approval.
    if (REGISTRATION_REVIEW_UI_PREVIEW_ENABLED) return <RegistrationReviewPreview permissions={permissions} />;
    // AR-6C7E.1: decisions; only after independently approved frontend/backend activation.
    if (REGISTRATION_REVIEW_LIVE_API_ENABLED) return <RegistrationReviewLivePanel permissions={permissions} />;
    // WF-02.01 (D-31): read-only pending applications; Django rechecks every request.
    if (PENDING_APPLICATIONS_LIST_ENABLED) return <PendingApplicationsPanel />;
  }

  // WF-02.05 (D-69, D-70): account directory and status controls; Django rechecks every request.
  if (view === 'account-directory' && ACCOUNT_DIRECTORY_ENABLED) return <AccountDirectoryPanel />;
  // WF-03.01 D-112: School operations ONLY, permission-gated and default-off.
  // This never exposes Role Assignments controls to School Admin.
  if (view === 'appointment-evidence' && APPOINTMENT_MANAGEMENT_ENABLED) return <AppointmentManagementPanel permissions={permissions} />;
  // WF-03.01 (D-86): Technical Super Admin role assignments; Django rechecks every request.
  if (view === 'role-assignments' && ROLE_ASSIGNMENT_ENABLED) return <RoleAssignmentsPanel permissions={permissions} />;
  // WF-03.02: role-permission matrix; each request is re-authorized by Django.
  if (view === 'role-permissions' && ROLE_PERMISSION_MANAGEMENT_ENABLED) return <RolePermissionsPanel permissions={permissions} />;
  // WF-03.03: exact account-specific Grants; no role-wide permission changes.
  if (view === 'account-overrides' && ACCOUNT_GRANTS_ENABLED) return <AccountGrantsPanel permissions={permissions} />;
  // WF-03.04: account-wide Deny and direct Grant/Deny removal; backend rechecks access.
  if (view === 'account-restrictions' && ACCOUNT_RESTRICTIONS_ENABLED) return <AccountRestrictionsPanel permissions={permissions} />;
  // WF-03.05: read-only effective access and service state inspection.
  if (view === 'access-reviews' && EFFECTIVE_ACCESS_INSPECT_ENABLED) return <EffectiveAccessPanel permissions={permissions} />;
  // WF-03.06: read-only, default-off audit history for Technical Super Admin.
  if (view === 'access-audit' && ACCESS_AUDIT_ENABLED) return <AccessAuditPanel permissions={permissions} />;
  // WF-11.01: Draft school years and semesters only; default-off, Django rechecks every request.
  if (view === 'school-periods' && ACADEMIC_PERIODS_ENABLED) return <SchoolPeriodsPanel />;
  // Academic configuration foundation: default-off; each tab's exact code is re-checked by Django.
  if (view === 'academic-references' && ACADEMIC_CONFIGURATION_ENABLED) return <AcademicSettingsPanel />;
  // Semester organizational fee (School Admin): default-off; Django authorizes every request.
  if (view === 'semester-fees' && SEMESTER_FEE_CONFIGURATION_ENABLED) return <SemesterFeesPanel />;

  return <ModuleUnavailable onBack={back} />;
}
