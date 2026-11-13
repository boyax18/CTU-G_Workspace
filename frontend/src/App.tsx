
import PublicLayout from './layouts/PublicLayout';
import DashboardLayout from './layouts/DashboardLayout';

import HomePage from './features/home/pages/HomePage';
import RegisterPage from './features/auth/RegisterPage';
import ForgotPasswordPage from './features/auth/ForgotPasswordPage';
import ResetPasswordPage from './features/auth/ResetPasswordPage';
import SessionDashboardPage from './features/dashboard/SessionDashboardPage';

export default function App() {
  const path = window.location.pathname.replace(/\/$/, '') || '/';

  if (path === '/dashboard') {
    return (
      <DashboardLayout>
        <SessionDashboardPage />
      </DashboardLayout>
    );
  }

  return (
    <PublicLayout home={path === '/'}>
      {path === '/' ? (
        <HomePage />
      ) : path === '/register' ? (
        <RegisterPage />
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
