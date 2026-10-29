import type { ReactNode } from 'react';
import '../css/theme.css';
import ThemeProvider from '../contexts/ThemeProvider';
import { useSectionPaging } from '../hooks/useSectionPaging';
import { PAGE_SECTION_IDS } from '../utils/constants';
import Navbar from '../components/navigation/Navbar';
import Footer from '../components/navigation/Footer';
import ScrollToTop from '../components/common/ScrollToTop';
import campusImage from '../assets/campus-building.jpg';

export default function PublicLayout({ children }: { children: ReactNode }) {
  useSectionPaging(PAGE_SECTION_IDS);
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
