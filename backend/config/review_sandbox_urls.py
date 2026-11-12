"""Routes only when Django is launched with config.review_sandbox_settings.

Regular config.urls remains untouched; no Registration Review routes are
mounted in the real CTU-G Workspace development server.
"""

from django.urls import include, path

from .urls import urlpatterns as original_patterns

urlpatterns = [
    *original_patterns,
    path(
        "api/v1/admin/registration-requests/",
        include("apps.accounts.registration_review_urls"),
    ),
]
