import type { ReactNode, SVGProps } from 'react';
import type { DashboardIconName } from '../../features/dashboard/navigation';

type IconName = DashboardIconName | 'menu' | 'close' | 'chevron' | 'chevronDown' | 'signout' | 'shield' | 'sidebar';
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
    settings: <><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></>,
    chart: <><path d="M4 20V4M4 20h16"/><path d="M8 16v-5M12 16V8M16 16v-3"/></>,
    receipt: <><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3Z"/><path d="M9 8h6M9 12h6"/></>,
    lock: <><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
    key: <><circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l2 2M14 9l2 2"/></>,
    list: <><path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/></>,
    activity: <path d="M3 12h4l3-8 4 16 3-8h4"/>,
    star: <path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9L12 3Z"/>,
    menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
    close: <path d="M5 5l14 14M19 5L5 19"/>,
    chevron: <path d="m9 6 6 6-6 6"/>,
    chevronDown: <path d="m6 9 6 6 6-6"/>,
    signout: <><path d="M10 4H5a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h5M14 7l5 5-5 5M9 12h10"/></>,
    shield: <><path d="m12 2 8 4v6c0 5-3 8-8 10-5-2-8-5-8-10V6l8-4Z"/><path d="m9 12 2 2 4-4"/></>,
    sidebar: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16"/></>,
  };
  return <svg {...base} {...props}>{paths[name]}</svg>;
}
