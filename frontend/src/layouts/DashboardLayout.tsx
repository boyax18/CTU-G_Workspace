
import type { ReactNode } from 'react';
import '../css/theme.css';
import ThemeProvider from '../contexts/ThemeProvider';

type DashboardLayoutProps = {
  children: ReactNode;
};

export default function DashboardLayout({
  children,
}: DashboardLayoutProps) {
  return (
    <ThemeProvider>
      <div className="app-bg fg-body min-h-screen">
        <header className="surface-header border-b px-4 py-4 sm:px-8">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
            <span className="fg-strong text-sm font-bold">
              CTU-G Workspace
            </span>
            <span className="fg-muted text-xs">
              Campus Portal
            </span>
          </div>
        </header>

        <main>{children}</main>
      </div>
    </ThemeProvider>
  );
}
