/** Shared dashboard states (Dashboard Shell v0.1 §2.1, PATTERNS §5). Fixed, non-sensitive copy. */
import type { ReactNode } from 'react';
import DashboardIcon from './DashboardIcon';

const secondaryButton = 'inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--db-edge)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600';

interface StateProps {
  icon?: 'shield' | 'clipboard' | 'list';
  title: string;
  children: ReactNode;
  action?: { label: string; onClick: () => void };
  role?: 'status' | 'alert';
}

export function DashboardState({ icon = 'shield', title, children, action, role }: StateProps) {
  return (
    <section role={role} className="dashboard-panel rounded-2xl border p-6 sm:p-8">
      <div className="dashboard-placeholder-icon mb-4 flex h-12 w-12 items-center justify-center rounded-xl">
        <DashboardIcon name={icon} />
      </div>
      <h2 className="dashboard-heading text-lg font-semibold">{title}</h2>
      <div className="dashboard-muted mt-2 max-w-2xl text-sm leading-relaxed">{children}</div>
      {action && <button type="button" className={`${secondaryButton} mt-5`} onClick={action.onClick}>{action.label}</button>}
    </section>
  );
}

/** Direct URL to a view the session does not report permission for. Reveals nothing about it. */
export function AccessDenied({ onBack }: { onBack: () => void }) {
  return (
    <DashboardState title="This section is unavailable" action={{ label: 'Return to dashboard', onClick: onBack }}>
      Your current session does not report the required module permission.
    </DashboardState>
  );
}

/** A permitted module whose workflow is not built or not enabled yet ("Soon"). */
export function ModuleUnavailable({ onBack }: { onBack: () => void }) {
  return (
    <DashboardState icon="clipboard" title="This module is not available yet" action={{ label: 'Return to dashboard', onClick: onBack }}>
      Your access includes this module, but its workflow has not been approved and connected yet.
      Nothing here can be viewed or changed until it is released.
    </DashboardState>
  );
}

/** No authorized modules beyond the dashboard and profile. */
export function NoModules() {
  return (
    <DashboardState icon="list" title="No modules are available to your account yet">
      Your account is verified. Modules appear here when your access includes them and their workflows are released.
      If you expected access, contact the School Admin office.
    </DashboardState>
  );
}
