import type { MouseEvent, ReactNode } from 'react';
import type { DashboardView } from '../../features/dashboard/navigation';
import { getDashboardGroup, getDashboardHref, getDashboardItem } from '../../features/dashboard/navigation';

interface BreadcrumbsProps {
  view: DashboardView;
  navigate: (view: DashboardView) => void;
  /** Optional fourth crumb for a page inside the view; the view crumb then links back. */
  subpage?: string | null;
  onViewCrumb?: () => void;
}

/** Dashboard › Group › Page. The group is context text, not a link (groups have no page). */
export function Breadcrumbs({ view, navigate, subpage = null, onViewCrumb }: BreadcrumbsProps) {
  const item = getDashboardItem(view);
  const group = getDashboardGroup(view);
  const plainClick = (event: MouseEvent<HTMLAnchorElement>) =>
    event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey;
  const follow = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!plainClick(event)) return;
    event.preventDefault();
    navigate('overview');
  };
  const backToView = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!plainClick(event)) return;
    event.preventDefault();
    onViewCrumb?.();
  };
  const linkClass = 'rounded underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
  return (
    <nav aria-label="Breadcrumb">
      <ol className="dashboard-muted flex flex-wrap items-center gap-1.5 text-xs">
        {view === 'overview' ? (
          <li aria-current="page" className="dashboard-heading font-medium">Dashboard</li>
        ) : (
          <>
            <li>
              <a href={getDashboardHref('overview')} onClick={follow}
                className="rounded underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]">
                Dashboard
              </a>
            </li>
            {group.id !== 'overview' && (
              <li className="flex items-center gap-1.5"><span aria-hidden="true">/</span>{group.label}</li>
            )}
            {subpage ? (
              <>
                <li className="flex items-center gap-1.5">
                  <span aria-hidden="true">/</span>
                  <a href={getDashboardHref(view)} onClick={backToView} className={linkClass}>{item.label}</a>
                </li>
                <li aria-current="page" className="dashboard-heading flex items-center gap-1.5 font-medium">
                  <span aria-hidden="true" className="dashboard-muted font-normal">/</span>{subpage}
                </li>
              </>
            ) : (
              <li aria-current="page" className="dashboard-heading flex items-center gap-1.5 font-medium">
                <span aria-hidden="true" className="dashboard-muted font-normal">/</span>{item.label}
              </li>
            )}
          </>
        )}
      </ol>
    </nav>
  );
}

interface PageHeaderProps {
  title: string;
  description?: string;
  /** Optional quick action, for example a primary link. */
  actions?: ReactNode;
  status?: ReactNode;
}

/** The single h1 of every dashboard view. Views start their own sections at h2. */
export default function PageHeader({ title, description, actions, status }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-3xl">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="dashboard-heading text-2xl font-bold sm:text-3xl">{title}</h1>
          {status}
        </div>
        {description && <p className="dashboard-muted mt-2 text-sm leading-relaxed">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </div>
  );
}
