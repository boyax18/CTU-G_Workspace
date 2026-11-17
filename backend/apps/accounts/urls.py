
from django.urls import path

from .views import CSRFView, RegistrationView
from .student_registration_api import (
    StudentVerificationStatusView, StudentVerificationActionView,
    StudentVerificationResendView, StudentVerificationCancelView,
)
from .reapplication_api import ReapplicationLinkView, ReapplicationCompleteView
from .session_auth import LoginView, LogoutView, SessionView
from .password_reset import PasswordResetRequestView, PasswordResetVerifyView, PasswordResetConfirmView

urlpatterns = [
  path("csrf/", CSRFView.as_view(), name="registration-csrf"),
  path("register/", RegistrationView.as_view(), name="register"),
  path("register/verification/", StudentVerificationStatusView.as_view(), name="student-registration-status"),
  path("register/verify/", StudentVerificationActionView.as_view(), name="student-registration-verify"),
  path("register/resend/", StudentVerificationResendView.as_view(), name="student-registration-resend"),
  path("register/cancel/", StudentVerificationCancelView.as_view(), name="student-registration-cancel"),
  # Present but fail closed (503) unless the separate reapplication gate is enabled.
  path("reapply/link/", ReapplicationLinkView.as_view(), name="workspace-reapplication-link"),
  path("reapply/complete/", ReapplicationCompleteView.as_view(), name="workspace-reapplication-complete"),
  path("login/", LoginView.as_view(), name="workspace-login"),
  path("logout/", LogoutView.as_view(), name="workspace-logout"),
  path("session/", SessionView.as_view(), name="workspace-session"),
  path("forgot-password/", PasswordResetRequestView.as_view(), name="workspace-forgot-password"),
  path("forgot-password/verify/", PasswordResetVerifyView.as_view(), name="workspace-forgot-password-verify"),
  path("reset-password/", PasswordResetConfirmView.as_view(), name="workspace-reset-password"),
]
