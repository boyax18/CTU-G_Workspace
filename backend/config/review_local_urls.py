"""Local opt-in URLconf; does not change config.urls or deployed route tables."""
from django.urls import include, path
from apps.accounts.active_role_context_api import RoleContextSwitchView
from .urls import urlpatterns as original_patterns

urlpatterns = [
    *original_patterns,
    # D-113: isolated, independently gated role-context selection only.
    path("api/v1/auth/role-context/", RoleContextSwitchView.as_view(), name="workspace-role-context-switch"),
    path("api/v1/admin/registration-requests/", include("apps.accounts.registration_review_urls")),
    # WF-02.05 (owner-authorized 18 Nov 2026, local development only; never config.urls).
    path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls")),
    # WF-03.01 D-87: isolated local-review route ONLY. Gate remains default-off in the settings overlay.
    # Never mount this in config.urls or expose it on a non-loopback server.
    path("api/v1/admin/role-assignments/", include("apps.access_control.role_assignment_urls")),
    # WF-03.02: isolated role-permission management, independently gated off.
    path("api/v1/admin/role-permissions/", include("apps.access_control.role_permission_urls")),
    # WF-03.03 individual Grants; independently gated and isolated.
    path("api/v1/admin/account-grants/", include("apps.access_control.account_grant_urls")),
    # WF-03.04 individual Deny / revoke; independently gated isolated routes.
    path("api/v1/admin/account-restrictions/", include("apps.access_control.account_restriction_urls")),
]
