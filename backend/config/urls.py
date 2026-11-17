# config/urls.py
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from accounts.views import MeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", TokenObtainPairView.as_view(), name="login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("api/auth/logout/", TokenBlacklistView.as_view(), name="logout"),
    path("api/auth/me/", MeView.as_view(), name="me"),
    path("api/classes/", include("classes.urls")),
    path("api/ratings/", include("ratings.urls")),
    path("api/dashboard/", include("dashboards.urls")),
    path("api/notifications/", include("notifications.urls")),
]