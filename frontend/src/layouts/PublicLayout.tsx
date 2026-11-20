import { useEffect } from 'react';
import type { ReactNode } from 'react';
import '../css/theme.css';
import ThemeProvider from '../contexts/ThemeProvider';
import { useSectionPaging } from '../hooks/useSectionPaging';
import { PAGE_SECTION_IDS } from '../utils/constants';
import Navbar from '../components/navigation/Navbar';
import Footer from '../components/navigation/Footer';
import ScrollToTop from '../components/common/ScrollToTop';
import campusImage from '../assets/campus-building.jpg';
import { focusLoginForm, scrollToSection } from '../utils/scroll';

const NO_SECTIONS: readonly string[] = [];

export default function PublicLayout({ children, home = true }: { children: ReactNode; home?: boolean }) {
  useSectionPaging(home ? PAGE_SECTION_IDS : NO_SECTIONS);
  useEffect(() => {
    const previous = document.documentElement.style.scrollSnapType;
    if (!home) document.documentElement.style.scrollSnapType = 'none';
    const hash = window.location.hash.slice(1);
    const timer = window.setTimeout(() => {
      if (!home) return;
      if (hash === 'login') focusLoginForm();
      else if (PAGE_SECTION_IDS.some((id) => id === hash)) scrollToSection(hash);
    }, 100);
    return () => { window.clearTimeout(timer); document.documentElement.style.scrollSnapType = previous; };
  }, [home]);
  return (
    <ThemeProvider>
      <div className="app-bg relative isolate flex min-h-screen flex-col overflow-x-clip">
        {/* One continuous campus photo behind the whole page, independent of the content */}
        <div aria-hidden className="site-bg">
          <div className="site-bg-photo" style={{ backgroundImage: `url(${campusImage})` }} />
          <div className="site-bg-overlay" />
        </div>
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
        <ScrollToTop />
      </div>
    </ThemeProvider>
  );
}
