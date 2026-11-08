
from django.urls import path

from .views import CSRFView, RegistrationView
from .session_auth import LoginView, LogoutView, SessionView

urlpatterns = [
  path("csrf/", CSRFView.as_view(), name="registration-csrf"),
  path("register/", RegistrationView.as_view(), name="register"),
  path("login/", LoginView.as_view(), name="workspace-login"),
  path("logout/", LogoutView.as_view(), name="workspace-logout"),
  path("session/", SessionView.as_view(), name="workspace-session"),
]
