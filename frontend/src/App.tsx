
import PublicLayout from './layouts/PublicLayout';
import DashboardLayout from './layouts/DashboardLayout';

import HomePage from './features/home/pages/HomePage';
import RegisterPage from './features/auth/RegisterPage';
import VerifyEmailPage from './features/auth/VerifyEmailPage';
import ForgotPasswordPage from './features/auth/ForgotPasswordPage';
import ResetPasswordPage from './features/auth/ResetPasswordPage';
import SessionDashboardPage from './features/dashboard/SessionDashboardPage';
import FinancePage from './features/finance/FinancePage';
import HelpPage from './features/help/HelpPage';
import SettingsPage from './features/settings/SettingsPage';
import AnnouncementsPage from './features/announcements/AnnouncementsPage.tsx';
import NotificationsPage from './features/notifications/NotificationsPage.tsx';

export default function App() {
  const path = window.location.pathname.replace(/\/$/, '') || '/';

  if (path === '/dashboard') {
    return (
      <DashboardLayout>
        <SessionDashboardPage />
      </DashboardLayout>
    );
  }

  if (path === '/finance') {
    return (
      <DashboardLayout>
        <FinancePage />
      </DashboardLayout>
    );
  }

  if (path === '/help') {
    return <DashboardLayout><HelpPage /></DashboardLayout>;
  }

  if (path === '/settings') {
    return <DashboardLayout><SettingsPage /></DashboardLayout>;
  }

  if (path === '/announcements') {
    return <DashboardLayout><AnnouncementsPage /></DashboardLayout>;
  }

  if (path === '/notifications') {
    return <DashboardLayout><NotificationsPage /></DashboardLayout>;
  }

  return (
    <PublicLayout home={path === '/'}>
      {path === '/' ? (
        <HomePage />
      ) : path === '/register' ? (
        <RegisterPage />
      ) : path === '/register/verify' ? (
        <VerifyEmailPage />
      ) : path === '/forgot-password' ? (
        <ForgotPasswordPage />
      ) : path === '/reset-password' ? (
        <ResetPasswordPage />
      ) : (
        <div className="fg-body mx-auto max-w-xl px-6 py-16">
          <h1 className="fg-strong text-2xl font-bold">
            Page not found
          </h1>
          <a className="link-accent mt-4 inline-block" href="/">
            Return to home
          </a>
        </div>
      )}
    </PublicLayout>
  );
}
