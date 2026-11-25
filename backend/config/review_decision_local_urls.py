"""Loopback-only WF-02 decision routes plus normal read-only application routes."""

from django.urls import include, path

from apps.accounts.assisted_recovery import AssistedRecoveryStartView

from .urls import urlpatterns as normal_patterns

urlpatterns = [
    path(
        "api/v1/admin/registration-requests/",
        include("apps.accounts.registration_review_urls"),
    ),
    # 25 Nov 2026: operator step of assisted recovery (loopback -Local only). Inert unless
    # WORKSPACE_ASSISTED_RECOVERY_ENABLED and the exact permission is provisioned and granted.
    path(
        "api/v1/admin/school-accounts/<int:account_id>/assisted-recovery/",
        AssistedRecoveryStartView.as_view(),
        name="school-accounts-assisted-recovery",
    ),
    *normal_patterns,
]
