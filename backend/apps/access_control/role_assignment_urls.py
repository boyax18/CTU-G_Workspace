"""WF-03.01 isolated URLconf for Technical Super Admin role assignments.

Mounted at api/v1/admin/role-assignments/ ONLY in local-review and sandbox URLconfs,
behind their separate default-off opt-in flags, including the D-100 ordinary gate. It is NEVER included by config.urls; the
release safeguard reports these RegistrationReviewAPI routes if inspected.
"""

from django.urls import path

from .role_assignment_api import AssignSchoolAdminView, RevokeSchoolAdminView, RoleAssignmentListView
from .ordinary_role_assignment_api import OrdinaryRoleChangeView, OrdinaryRoleListView
from .appointment_registry_api import (
    AppointmentCandidateView, AppointmentMySubmissionsView, AppointmentVerifiedQueueView,
    AppointmentReviewQueueView, AppointmentReviewView, AppointmentSubmitView,
)

urlpatterns = [
    path("", RoleAssignmentListView.as_view(), name="role-assignments-list"),
    path("<int:account_id>/school-admin/assign/", AssignSchoolAdminView.as_view(), name="role-assignments-assign-school-admin"),
    path("<int:account_id>/school-admin/revoke/", RevokeSchoolAdminView.as_view(), name="role-assignments-revoke-school-admin"),
    # D-104: separate default-off School Admin appointment evidence registry;
    # independent recorder/verifier permissions are NOT provisioned.
    path("appointments/", AppointmentSubmitView.as_view(), name="ordinary-appointment-submit"),
    # D-112: exact ID lookup, recorder status and revocation queue. All default-off.
    path("appointments/candidate/", AppointmentCandidateView.as_view(), name="ordinary-appointment-candidate"),
    path("appointments/my-submissions/", AppointmentMySubmissionsView.as_view(), name="ordinary-appointment-submissions"),
    path("appointments/verified/", AppointmentVerifiedQueueView.as_view(), name="ordinary-appointment-verified"),
    path("appointments/review-queue/", AppointmentReviewQueueView.as_view(), name="ordinary-appointment-review-queue"),
    path("appointments/<int:appointment_id>/<str:action>/", AppointmentReviewView.as_view(), name="ordinary-appointment-review"),
    # D-100: extra default-off authorization gate; no Technical Super Admin or base-role writer.
    path("ordinary/", OrdinaryRoleListView.as_view(), name="role-assignments-ordinary-list"),
    path("<int:account_id>/ordinary/<slug:role_slug>/<str:action>/", OrdinaryRoleChangeView.as_view(),
         name="role-assignments-ordinary-change"),
]
