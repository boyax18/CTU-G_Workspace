import type { ReactNode, SVGProps } from 'react';
import type { DashboardNavItem } from '../../features/dashboard/navigation';

type IconName = DashboardNavItem['icon'] | 'menu' | 'close' | 'chevron' | 'signout' | 'shield';
type Props = SVGProps<SVGSVGElement> & { name: IconName };

export default function DashboardIcon({ name, ...props }: Props) {
  const base = {
    width: 19, height: 19, viewBox: '0 0 24 24', fill: 'none',
    stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const,
    strokeLinejoin: 'round' as const, 'aria-hidden': true as const,
  };

  const paths: Record<IconName, ReactNode> = {
    home: <><rect x="3" y="4" width="7" height="7" rx="1"/><rect x="14" y="4" width="7" height="7" rx="1"/><rect x="3" y="15" width="7" height="6" rx="1"/><rect x="14" y="15" width="7" height="6" rx="1"/></>,
    user: <><circle cx="12" cy="8" r="3.5"/><path d="M4.5 21c0-4.3 3-7 7.5-7s7.5 2.7 7.5 7"/></>,
    users: <><circle cx="9" cy="8" r="3"/><path d="M3 20c0-4.1 2.3-6 6-6s6 1.9 6 6M17 5a3 3 0 0 1 0 6M18 14c2.1.4 3 2.1 3 5"/></>,
    wallet: <><rect x="3" y="6" width="18" height="15" rx="2"/><path d="M3 9h18M6 3h13"/><circle cx="17" cy="15" r="1"/></>,
    clipboard: <><rect x="5" y="5" width="14" height="17" rx="2"/><path d="M9 5V3h6v2M9 13l2 2 4-4"/></>,
    book: <><path d="M12 5c-2.8-2-5.5-2-9-1v15c3.6-1 6.3-1 9 1 2.7-2 5.4-2 9-1V4c-3.6-1-6.3-1-9 1ZM12 5v15"/></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 6-3 7-3 8h18c0-1-3-2-3-8ZM10 21h4"/></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
    close: <path d="M5 5l14 14M19 5L5 19"/>,
    chevron: <path d="m9 6 6 6-6 6"/>,
    signout: <><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M14 7l5 5-5 5M9 12h10"/></>,
    shield: <><path d="m12 2 8 4v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-4Z"/><path d="m9 12 2 2 4-4"/></>,
  };
  return <svg {...base} {...props}>{paths[name]}</svg>;
}
