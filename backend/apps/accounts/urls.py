
from django.urls import path

from .views import CSRFView, RegistrationView
from .session_auth import LoginView, LogoutView, SessionView
from .password_reset import PasswordResetRequestView, PasswordResetConfirmView

urlpatterns = [
  path("csrf/", CSRFView.as_view(), name="registration-csrf"),
  path("register/", RegistrationView.as_view(), name="register"),
  path("login/", LoginView.as_view(), name="workspace-login"),
  path("logout/", LogoutView.as_view(), name="workspace-logout"),
  path("session/", SessionView.as_view(), name="workspace-session"),
  path("forgot-password/", PasswordResetRequestView.as_view(), name="workspace-forgot-password"),
  path("reset-password/", PasswordResetConfirmView.as_view(), name="workspace-reset-password"),
]
