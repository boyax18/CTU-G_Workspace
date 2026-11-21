"""Routes only when Django is launched with config.review_sandbox_settings.

Regular config.urls remains untouched; no Registration Review routes are
mounted in the real CTU-G Workspace development server.
"""

from django.urls import include, path
from apps.accounts.active_role_context_api import RoleContextSwitchView

from .urls import urlpatterns as original_patterns

urlpatterns = [
    *original_patterns,
    # D-113: isolated, independently gated role-context selection only.
    path("api/v1/auth/role-context/", RoleContextSwitchView.as_view(), name="workspace-role-context-switch"),
    path(
        "api/v1/admin/registration-requests/",
        include("apps.accounts.registration_review_urls"),
    ),
    # WF-02.05 (owner-authorized 18 Nov 2026, local development only; never config.urls).
    path("api/v1/admin/school-accounts/", include("apps.accounts.account_status_urls")),
    # WF-03.01 D-87: sandbox-only route, gated off unless the sandbox operator opts in.
    path("api/v1/admin/role-assignments/", include("apps.access_control.role_assignment_urls")),
    # WF-03.02: isolated role-permission management, independently gated off.
    path("api/v1/admin/role-permissions/", include("apps.access_control.role_permission_urls")),
]
