"""Local opt-in URLconf; does not change config.urls or deployed route tables."""
from django.urls import include, path
from .urls import urlpatterns as original_patterns

urlpatterns = [
    *original_patterns,
    path("api/v1/admin/registration-requests/", include("apps.accounts.registration_review_urls")),
]
