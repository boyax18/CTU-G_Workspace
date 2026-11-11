import { useDashboardContext } from '../../hooks/useDashboardContext';
import {
  canOpenDashboardView,
  DASHBOARD_NAV_ITEMS,
  getVisibleDashboardItems,
} from './navigation';
import DashboardIcon from '../../components/dashboard/DashboardIcon';
import RegistrationReviewPreview from '../admin/RegistrationReviewPreview';
import { REGISTRATION_REVIEW_UI_PREVIEW_ENABLED } from '../admin/registrationReviewPreviewGate';

export default function SessionDashboardPage() {
  const { session, view, navigate } = useDashboardContext();
  const { account, permissions } = session;

  if (!canOpenDashboardView(view, permissions)) {
    return (
      <section className="dashboard-panel rounded-2xl border p-6 sm:p-8">
        <h2 className="dashboard-heading text-xl font-bold">This section is unavailable</h2>
        <p className="dashboard-muted mt-2 text-sm">Your current session does not report the required module permission.</p>
        <button className="dashboard-primary-link mt-5 rounded-lg px-4 py-2 text-sm font-medium" onClick={() => navigate('overview')}>
          Return to overview
        </button>
      </section>
    );
  }

  if (view === 'account') {
    return (
      <div className="space-y-5">
        <div>
          <p className="dashboard-eyebrow">Account information</p>
          <h2 className="dashboard-heading mt-1 text-2xl font-bold sm:text-3xl">Your Workspace account</h2>
          <p className="dashboard-muted mt-2 text-sm">Read-only details from your verified session.</p>
        </div>
        <section className="dashboard-panel rounded-2xl border p-6 sm:p-8" aria-label="Account details">
          <dl className="grid gap-6 text-sm sm:grid-cols-2">
            <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">School ID</dt><dd className="dashboard-heading mt-2 font-semibold">{account.school_id}</dd></div>
            <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Assigned roles</dt><dd className="dashboard-heading mt-2 font-semibold">{account.roles.join(', ') || 'None'}</dd></div>
            <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Session status</dt><dd className="mt-2 font-semibold text-emerald-700">Authenticated</dd></div>
            <div><dt className="dashboard-muted text-xs font-medium uppercase tracking-wider">Effective permission hints</dt><dd className="dashboard-heading mt-2 font-semibold">{permissions.length}</dd></div>
          </dl>
          <p className="dashboard-muted mt-7 border-t pt-4 text-xs leading-relaxed">
            Role names and permission hints never authorize an API call. Django verifies access on every protected request.
          </p>
        </section>
      </div>
    );
  }

  // AR-6C7D.1: fictional mock UI only; hard-disabled pending separate approval.
  if (view === 'registration-review' && REGISTRATION_REVIEW_UI_PREVIEW_ENABLED) {
    return <RegistrationReviewPreview permissions={permissions} />;
  }

  if (view !== 'overview') {
    const item = DASHBOARD_NAV_ITEMS.find((entry) => entry.id === view);
    return (
      <div className="space-y-5">
        <div>
          <p className="dashboard-eyebrow">Module space</p>
          <h2 className="dashboard-heading mt-1 text-2xl font-bold sm:text-3xl">{item?.label ?? 'Workspace module'}</h2>
        </div>
        <section className="dashboard-panel rounded-2xl border p-6 sm:p-8">
          <div className="dashboard-placeholder-icon mb-4 flex h-12 w-12 items-center justify-center rounded-xl">
            <DashboardIcon name="shield" />
          </div>
          <h3 className="dashboard-heading text-lg font-semibold">Module integration is pending</h3>
          <p className="dashboard-muted mt-2 max-w-2xl text-sm leading-relaxed">
            Your session currently includes a permission hint for this module. This page is only the shared shell placeholder;
            no live module API or account action has been connected.
          </p>
          <button className="dashboard-primary-link mt-5 rounded-lg px-4 py-2 text-sm font-medium" onClick={() => navigate('overview')}>
            Back to overview
          </button>
        </section>
      </div>
    );
  }

  const modules = getVisibleDashboardItems(permissions).filter((item) => item.section === 'modules');

  return (
    <div className="space-y-7">
      <section className="dashboard-hero relative overflow-hidden rounded-3xl p-6 sm:p-8 lg:p-10">
        <div className="relative z-10 max-w-2xl">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-100">Cebu Technological University · Ginatilan</p>
          <h2 className="mt-4 text-2xl font-bold tracking-tight text-white sm:text-3xl">Welcome to your workspace</h2>
          <p className="mt-3 text-sm leading-relaxed text-emerald-50/90">
            A shared campus portal with one dashboard layout. Your available module spaces depend on your current effective permissions.
          </p>
          <button className="mt-6 rounded-xl border border-white/35 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-white/25"
            onClick={() => navigate('account')}>
            View account details
          </button>
        </div>
        <div aria-hidden="true" className="dashboard-hero-ring absolute -right-20 -top-32 h-96 w-96 rounded-full" />
      </section>

      <section aria-label="Workspace summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="dashboard-panel rounded-2xl border p-5">
          <p className="dashboard-muted text-xs font-semibold uppercase tracking-wide">Session</p>
          <p className="dashboard-heading mt-3 text-xl font-bold">Verified</p>
          <p className="dashboard-muted mt-1 text-xs">Approved Workspace session</p>
        </div>
        <div className="dashboard-panel rounded-2xl border p-5">
          <p className="dashboard-muted text-xs font-semibold uppercase tracking-wide">Effective permissions</p>
          <p className="dashboard-heading mt-3 text-xl font-bold">{permissions.length}</p>
          <p className="dashboard-muted mt-1 text-xs">Current session hints, not cached grants</p>
        </div>
        <div className="dashboard-panel rounded-2xl border p-5">
          <p className="dashboard-muted text-xs font-semibold uppercase tracking-wide">Available module spaces</p>
          <p className="dashboard-heading mt-3 text-xl font-bold">{modules.length}</p>
          <p className="dashboard-muted mt-1 text-xs">Live module pages not yet connected</p>
        </div>
      </section>

      <section aria-labelledby="dashboard-modules-heading">
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <p className="dashboard-eyebrow">Your access</p>
            <h3 id="dashboard-modules-heading" className="dashboard-heading mt-1 text-xl font-bold">Module spaces</h3>
          </div>
          <p className="dashboard-muted text-xs">Shown by exact permission code · not role name</p>
        </div>
        {modules.length === 0 ? (
          <div className="dashboard-panel rounded-2xl border p-6">
            <h4 className="dashboard-heading font-semibold">No additional module spaces yet</h4>
            <p className="dashboard-muted mt-2 text-sm">Your account is verified. New modules will appear after their backend permissions and integrations are approved.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {modules.map((item) => (
              <button
                type="button"
                key={item.id}
                className="dashboard-panel dashboard-module-card group rounded-2xl border p-5 text-left transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700"
                onClick={() => navigate(item.id)}
              >
                <div className="dashboard-placeholder-icon mb-4 flex h-11 w-11 items-center justify-center rounded-xl">
                  <DashboardIcon name={item.icon}/>
                </div>
                <p className="dashboard-heading font-semibold">{item.label}</p>
                <p className="dashboard-muted mt-2 text-xs">Integration pending</p>
                <p className="mt-4 flex items-center gap-1 text-xs font-semibold text-emerald-700">Open module space <DashboardIcon name="chevron"/></p>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
