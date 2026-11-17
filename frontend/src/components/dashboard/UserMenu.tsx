/** Header user menu (Dashboard Shell v0.1 §2): profile, account settings and sign-out.
 * Menu-button pattern: Enter/Space/ArrowDown open on the first item, ArrowUp on the last;
 * arrows, Home and End move; Escape closes and returns focus; Tab or an outside click closes.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent } from 'react';
import type { DashboardNavItem, DashboardView } from '../../features/dashboard/navigation';
import DashboardIcon from './DashboardIcon';

interface Props {
  schoolId: string;
  roles: string;
  items: readonly DashboardNavItem[];
  navigate: (view: DashboardView) => void;
  signOut: () => void;
  signingOut: boolean;
}

export default function UserMenu({ schoolId, roles, items, navigate, signOut, signingOut }: Props) {
  const id = useId();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const firstFocus = useRef<'first' | 'last'>('first');

  const entries = () => [...(menu.current?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]:not([disabled])') ?? [])];

  useEffect(() => {
    if (!open) return;
    const list = entries();
    (firstFocus.current === 'last' ? list.at(-1) : list[0])?.focus();
    const outside = (event: PointerEvent) => {
      if (!menu.current?.contains(event.target as Node) && !button.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);

  const close = (returnFocus: boolean) => {
    setOpen(false);
    if (returnFocus) button.current?.focus();
  };

  const onButtonKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      firstFocus.current = event.key === 'ArrowUp' ? 'last' : 'first';
      setOpen(true);
    }
  };

  const onMenuKey = (event: KeyboardEvent<HTMLDivElement>) => {
    const list = entries();
    const index = list.indexOf(document.activeElement as HTMLButtonElement);
    const move = (next: number) => { event.preventDefault(); list[(next + list.length) % list.length]?.focus(); };
    if (event.key === 'ArrowDown') move(index + 1);
    else if (event.key === 'ArrowUp') move(index - 1);
    else if (event.key === 'Home') move(0);
    else if (event.key === 'End') move(list.length - 1);
    else if (event.key === 'Escape') { event.preventDefault(); close(true); }
    else if (event.key === 'Tab') close(false);
  };

  const choose = (view: DashboardView) => { close(false); navigate(view); };

  return (
    <div className="relative">
      <button
        ref={button}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? `${id}-menu` : undefined}
        aria-label={`Account menu for ${schoolId}`}
        onClick={() => { firstFocus.current = 'first'; setOpen((value) => !value); }}
        onKeyDown={onButtonKey}
        className="dashboard-topbar-icon flex min-h-11 items-center gap-2 rounded-xl px-2 py-1.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600"
      >
        <span aria-hidden="true" className="dashboard-placeholder-icon flex h-8 w-8 items-center justify-center rounded-full"><DashboardIcon name="user" width={16} height={16} /></span>
        <span className="hidden min-w-0 md:block">
          <span className="block text-xs font-semibold">{schoolId}</span>
          <span className="dashboard-muted block max-w-40 truncate text-xs">{roles}</span>
        </span>
        <DashboardIcon name="chevronDown" width={15} height={15} />
      </button>
      {open && (
        <div
          ref={menu}
          id={`${id}-menu`}
          role="menu"
          aria-label="Account"
          onKeyDown={onMenuKey}
          className="dashboard-panel absolute right-0 z-[60] mt-2 w-64 rounded-xl border p-2 shadow-lg"
        >
          <div className="border-b px-3 pb-2 pt-1 md:hidden" role="none">
            <p className="dashboard-heading text-xs font-semibold">{schoolId}</p>
            <p className="dashboard-muted truncate text-xs">{roles}</p>
          </div>
          {items.map((item) => (
            <button key={item.id} type="button" role="menuitem" tabIndex={-1}
              onClick={() => choose(item.id)}
              className="dashboard-heading flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--db-edge)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-emerald-600">
              <DashboardIcon name={item.icon} />
              <span className="flex-1">{item.label}</span>
              {item.integration === 'planned' && <span className="dashboard-muted text-xs">Soon</span>}
            </button>
          ))}
          <div role="separator" className="my-1 border-t border-[var(--db-edge)]" />
          <button type="button" role="menuitem" tabIndex={-1} disabled={signingOut}
            onClick={() => { close(false); signOut(); }}
            className="dashboard-heading flex min-h-11 w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm hover:bg-[var(--db-edge)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-50">
            <DashboardIcon name="signout" />
            {signingOut ? 'Signing out…' : 'Sign out of Workspace'}
          </button>
        </div>
      )}
    </div>
  );
}
