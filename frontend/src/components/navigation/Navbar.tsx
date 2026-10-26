import { useState } from 'react';
import Button from '../common/Button';
import { CloseIcon, MenuIcon } from '../common/Icons';
import { BRAND_NAME, CAMPUS_NAME, REGISTER_PATH } from '../../utils/constants';
import { focusLoginForm, scrollToSection } from '../../utils/scroll';

const NAV_ITEMS = [
  { id: 'home', label: 'Home' },
  { id: 'services', label: 'Services' },
  { id: 'about', label: 'About' },
  { id: 'announcements', label: 'Announcements' },
  { id: 'help', label: 'Help' },
  { id: 'contact', label: 'Contact' },
];

export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState('home');

  const go = (id: string) => {
    setActive(id);
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
    <header className="sticky top-0 z-50 border-b border-gray-200 bg-white">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
        <button type="button" onClick={() => go('home')} className="flex min-w-0 items-center gap-2.5 text-left">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-green-900 text-xs font-bold text-white">
            CG
          </span>
          <span className="min-w-0">
            <span className="block truncate text-lg font-bold leading-tight text-gray-900">{BRAND_NAME}</span>
            <span className="hidden truncate text-xs leading-tight text-gray-500 sm:block">{CAMPUS_NAME}</span>
          </span>
        </button>

        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => go(item.id)}
              aria-current={active === item.id ? 'page' : undefined}
              className={`rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                active === item.id ? 'bg-green-100 text-green-900' : 'text-gray-600 hover:bg-green-50 hover:text-green-900'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <Button variant="outline" size="sm" onClick={signIn}>Sign In</Button>
          {REGISTER_PATH && <Button size="sm" onClick={getStarted}>Get Started</Button>}
        </div>

        <button
          type="button"
          className="flex h-10 w-10 items-center justify-center rounded-lg text-gray-700 hover:bg-green-50 lg:hidden"
          aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <CloseIcon /> : <MenuIcon />}
        </button>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-gray-200 bg-white px-4 pb-4 pt-2 lg:hidden">
          <nav aria-label="Mobile" className="flex flex-col">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => go(item.id)}
                className={`rounded-md px-3 py-3 text-left text-sm font-medium ${
                  active === item.id ? 'bg-green-100 text-green-900' : 'text-gray-700 hover:bg-green-50'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <div className="mt-3 flex gap-2">
            <Button variant="outline" fullWidth onClick={signIn}>Sign In</Button>
            {REGISTER_PATH && <Button fullWidth onClick={getStarted}>Get Started</Button>}
          </div>
        </div>
      )}
    </header>
  );
}