"""WF-03.01 isolated URLconf for Technical Super Admin role assignments.

Proposed mount point: api/v1/admin/role-assignments/, ONLY in the owner-authorized local-review and
sandbox URLconfs, which is a separately authorized protected change (not done in this stage). It is
never included by config.urls; the release safeguard reports these RegistrationReviewAPI routes.
"""

from django.urls import path

from .role_assignment_api import AssignSchoolAdminView, RevokeSchoolAdminView, RoleAssignmentListView

urlpatterns = [
    path("", RoleAssignmentListView.as_view(), name="role-assignments-list"),
    path("<int:account_id>/school-admin/assign/", AssignSchoolAdminView.as_view(), name="role-assignments-assign-school-admin"),
    path("<int:account_id>/school-admin/revoke/", RevokeSchoolAdminView.as_view(), name="role-assignments-revoke-school-admin"),
]
