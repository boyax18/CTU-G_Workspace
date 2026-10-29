import { BRAND_NAME, CAMPUS_NAME } from '../../utils/constants';
import { scrollToSection } from '../../utils/scroll';
import logo from '../../assets/logo.png';

const LINKS = [
  { id: 'services', label: 'Services' },
  { id: 'about', label: 'About' },
  { id: 'announcements', label: 'Announcements' },
  { id: 'help', label: 'Help' },
  { id: 'contact', label: 'Contact' },
];

export default function Footer() {
  return (
    <footer className="surface-footer snap-end">
      <div className="mx-auto flex w-full max-w-[1920px] flex-col gap-4 px-4 py-8 sm:px-6 md:flex-row md:items-center md:justify-between lg:px-8">
        <div className="flex items-center gap-3">
          <img src={logo} alt="" className="h-9 w-9 shrink-0 rounded-lg object-cover" />
          <div>
            <p className="fg-strong text-sm font-semibold">{BRAND_NAME}</p>
            <p className="fg-muted text-xs">{CAMPUS_NAME}</p>
          </div>
        </div>
        <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2">
          {LINKS.map((l) => (
            <button key={l.id} type="button" onClick={() => scrollToSection(l.id)} className="link-muted text-xs">
              {l.label}
            </button>
          ))}
        </nav>
        <p className="fg-muted text-xs">Â© {new Date().getFullYear()} {BRAND_NAME}. All rights reserved.</p>
      </div>
    </footer>
  );
}

