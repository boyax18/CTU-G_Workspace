import type { MouseEvent } from 'react';
import type { DashboardView } from '../../features/dashboard/navigation';
import {
  getDashboardHref,
  getVisibleDashboardItems,
} from '../../features/dashboard/navigation';
import DashboardIcon from './DashboardIcon';

interface Props {
  permissions: readonly string[];
  active: DashboardView;
  navigate: (view: DashboardView) => void;
}

export default function DashboardNavigation({ permissions, active, navigate }: Props) {
  const visible = getVisibleDashboardItems(permissions);

  const follow = (event: MouseEvent<HTMLAnchorElement>, view: DashboardView) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(view);
  };

  const renderSection = (section: 'workspace' | 'modules') => {
    const items = visible.filter((item) => item.section === section);
    if (!items.length) return null;
    return (
      <div className="mb-5" key={section}>
        <p className="px-3 pb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-100/65">
          {section === 'workspace' ? 'Workspace' : 'Authorized module spaces'}
        </p>
        <div className="space-y-1">
          {items.map((item) => (
            <a
              key={item.id}
              href={getDashboardHref(item.id)}
              onClick={(event) => follow(event, item.id)}
              aria-current={active === item.id ? 'page' : undefined}
              className={`dashboard-nav-link flex min-h-11 items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white ${active === item.id ? 'dashboard-nav-active' : ''}`}
            >
              <DashboardIcon name={item.icon} />
              <span className="min-w-0 flex-1 truncate">{item.label}</span>
              {item.integration === 'planned' && <span className="text-[10px] text-emerald-100/65">Soon</span>}
            </a>
          ))}
        </div>
      </div>
    );
  };

  return (
    <nav aria-label="Dashboard navigation">
      {renderSection('workspace')}
      {renderSection('modules')}
      {visible.every((item) => item.section !== 'modules') && (
        <p className="px-3 text-xs leading-relaxed text-emerald-100/65">
          Module links appear only when your current session reports the required permissions.
        </p>
      )}
    </nav>
  );
}
