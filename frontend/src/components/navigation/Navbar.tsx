import { useEffect, useRef, useState } from 'react';
import Button from '../common/Button';
import ThemeToggle from '../common/ThemeToggle';
import { CloseIcon, MenuIcon } from '../common/Icons';
import { useActiveSection } from '../../hooks/useActiveSection';
import { useScrollHeader } from '../../hooks/useScrollHeader';
import { BRAND_NAME, CAMPUS_NAME, REGISTER_PATH } from '../../utils/constants';
import { focusLoginForm, scrollToSection } from '../../utils/scroll';
import logo from '../../assets/logo.png';

const NAV_ITEMS = [
  { id: 'home', label: 'Home' },
  { id: 'services', label: 'Services' },
  { id: 'about', label: 'About' },
  { id: 'announcements', label: 'Announcements' },
  { id: 'help', label: 'Help' },
  { id: 'contact', label: 'Contact' },
] as const;

const NAV_IDS = NAV_ITEMS.map((item) => item.id);

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const { active, activate } = useActiveSection(NAV_IDS);
  const { scrolled, progressRef } = useScrollHeader();
  const headerRef = useRef<HTMLElement | null>(null);

  // Close the dropdown on outside click or Escape
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (headerRef.current && !headerRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('pointerdown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('pointerdown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [open]);

  const go = (id: string) => {
    activate(id);
    setOpen(false);
    scrollToSection(id);
  };

  const signIn = () => {
    setOpen(false);
    focusLoginForm();
  };

  const getStarted = () => {
    if (REGISTER_PATH) window.location.assign(REGISTER_PATH);
  };

  return (
    <header ref={headerRef} className={`surface-header sticky top-0 z-50 ${scrolled ? 'is-scrolled' : ''}`}>
      <div className="grid h-16 w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 sm:px-6 lg:px-8 min-[1152px]:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <button type="button" onClick={() => go('home')} className="flex min-w-0 items-center gap-2.5 justify-self-start text-left">
          <img src={logo} alt="" className="h-9 w-9 shrink-0 rounded-lg object-cover" />
          <span className="min-w-0">
            <span className="fg-strong block truncate text-lg font-bold leading-tight">{BRAND_NAME}</span>
            <span className="fg-muted hidden truncate text-xs leading-tight sm:block">{CAMPUS_NAME}</span>
          </span>
        </button>

        <nav aria-label="Primary" className="hidden items-center justify-self-center gap-1 min-[1152px]:flex">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => go(item.id)}
              aria-current={active === item.id ? 'page' : undefined}
              className="nav-link rounded-md px-2 py-2 text-sm font-medium xl:px-3"
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="flex items-center justify-end gap-2 justify-self-end">
          <div className="hidden sm:block">
            <ThemeToggle />
          </div>
          <div className="hidden items-center gap-2 min-[1152px]:flex">
            <Button variant="outline" size="sm" onClick={signIn}>Sign In</Button>
            {REGISTER_PATH && <Button size="sm" onClick={getStarted}>Get Started</Button>}
          </div>
          <button
            type="button"
            className="icon-btn flex h-10 w-10 shrink-0 items-center justify-center rounded-lg min-[1152px]:hidden"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            aria-controls="mobile-menu"
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </div>

      <div id="mobile-menu" className="mobile-menu min-[1152px]:hidden" data-open={open}>
        <div className="mobile-menu-scroll p-3">
          <nav aria-label="Mobile" className="flex flex-col gap-0.5">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => go(item.id)}
                aria-current={active === item.id ? 'page' : undefined}
                className="nav-link rounded-lg px-3 py-2.5 text-left text-sm font-medium"
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="mt-3 flex gap-2">
            <Button variant="outline" fullWidth onClick={signIn}>Sign In</Button>
            {REGISTER_PATH && <Button fullWidth onClick={getStarted}>Get Started</Button>}
          </div>
          <div className="mt-4 flex items-center justify-between sm:hidden">
            <span className="fg-muted text-xs font-medium">Theme</span>
            <ThemeToggle />
          </div>
        </div>
      </div>

      <div ref={progressRef} className="scroll-progress" aria-hidden />
    </header>
  );
}

