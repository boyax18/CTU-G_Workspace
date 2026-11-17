import type { MouseEvent } from 'react';
import type { DashboardNavItem, DashboardView } from '../../features/dashboard/navigation';
import { getDashboardHref, getVisibleNavGroups } from '../../features/dashboard/navigation';
import DashboardIcon from './DashboardIcon';

interface Props {
  permissions: readonly string[];
  active: DashboardView;
  navigate: (view: DashboardView) => void;
  /** Desktop icon rail: labels stay available to assistive technology and as tooltips. */
  collapsed?: boolean;
}

const linkBase = 'dashboard-nav-link flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white';

function followLink(event: MouseEvent<HTMLAnchorElement>, view: DashboardView, navigate: Props['navigate']) {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  navigate(view);
}

export function DashboardNavLink({ item, active, navigate, collapsed = false }: {
  item: DashboardNavItem; active: DashboardView; navigate: Props['navigate']; collapsed?: boolean;
}) {
  const soon = item.integration === 'planned';
  return (
    <a
      href={getDashboardHref(item.id)}
      onClick={(event) => followLink(event, item.id, navigate)}
      aria-current={active === item.id ? 'page' : undefined}
      title={collapsed ? `${item.label}${soon ? ' (Soon)' : ''}` : undefined}
      className={`${linkBase} ${collapsed ? 'justify-center' : ''} ${active === item.id ? 'dashboard-nav-active' : ''}`}
    >
      <DashboardIcon name={item.icon} />
      <span className={collapsed ? 'sr-only' : 'min-w-0 flex-1 truncate'}>{item.label}</span>
      {soon && <span className={collapsed ? 'sr-only' : 'dashboard-nav-soon rounded-full px-2 py-0.5 text-xs'}>Soon</span>}
    </a>
  );
}

export default function DashboardNavigation({ permissions, active, navigate, collapsed = false }: Props) {
  const groups = getVisibleNavGroups(permissions, 'main');
  const onlyOverview = groups.every((group) => group.id === 'overview');

  return (
    <nav aria-label="Dashboard navigation">
      {groups.map((group) => (
        <div className="mb-5" key={group.id} role="group" aria-labelledby={`nav-group-${group.id}`}>
          <p id={`nav-group-${group.id}`}
            className={collapsed ? 'sr-only' : 'dashboard-nav-group px-3 pb-2 text-xs font-semibold uppercase tracking-[0.16em]'}>
            {group.label}
          </p>
          <div className="space-y-1">
            {group.items.map((item) => (
              <DashboardNavLink key={item.id} item={item} active={active} navigate={navigate} collapsed={collapsed} />
            ))}
          </div>
        </div>
      ))}
      {onlyOverview && !collapsed && (
        <p className="dashboard-nav-group px-3 text-xs leading-relaxed">
          Module links appear only when your current session reports the required permissions.
        </p>
      )}
    </nav>
  );
}
