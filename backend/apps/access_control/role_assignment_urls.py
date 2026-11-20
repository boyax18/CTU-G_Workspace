"""WF-03.01 isolated URLconf for Technical Super Admin role assignments.

Mounted at api/v1/admin/role-assignments/ ONLY in local-review and sandbox URLconfs,
behind their separate default-off opt-in flags, including the D-100 ordinary gate. It is NEVER included by config.urls; the
release safeguard reports these RegistrationReviewAPI routes if inspected.
"""

from django.urls import path

from .role_assignment_api import AssignSchoolAdminView, RevokeSchoolAdminView, RoleAssignmentListView
from .ordinary_role_assignment_api import OrdinaryRoleChangeView, OrdinaryRoleListView

urlpatterns = [
    path("", RoleAssignmentListView.as_view(), name="role-assignments-list"),
    path("<int:account_id>/school-admin/assign/", AssignSchoolAdminView.as_view(), name="role-assignments-assign-school-admin"),
    path("<int:account_id>/school-admin/revoke/", RevokeSchoolAdminView.as_view(), name="role-assignments-revoke-school-admin"),
    # D-100: extra default-off authorization gate; no Technical Super Admin or base-role writer.
    path("ordinary/", OrdinaryRoleListView.as_view(), name="role-assignments-ordinary-list"),
    path("<int:account_id>/ordinary/<slug:role_slug>/<str:action>/", OrdinaryRoleChangeView.as_view(),
         name="role-assignments-ordinary-change"),
]
