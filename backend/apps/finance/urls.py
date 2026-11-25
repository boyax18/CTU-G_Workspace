"""Finance routes (all default-off; see apps.finance.api). No payment, receipt or obligation route exists."""

from django.urls import path

from . import api

urlpatterns = [
    path("semester-fees/", api.SemesterFeeList.as_view(), name="finance-semester-fees"),
    path("semester-fees/<int:semester_id>/", api.SemesterFeeDetail.as_view(), name="finance-semester-fee"),
    path("semester-fees/<int:semester_id>/draft/", api.SemesterFeeDraft.as_view(), name="finance-semester-fee-draft"),
    path("semester-fees/<int:semester_id>/draft/withdraw/", api.SemesterFeeDraftWithdraw.as_view(),
         name="finance-semester-fee-draft-withdraw"),
    # GET preview (configuration switch) / POST confirmation (also WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED).
    path("semester-fees/<int:semester_id>/approval/", api.SemesterFeeApproval.as_view(),
         name="finance-semester-fee-approval"),
    path("semester-fees/<int:semester_id>/history/", api.SemesterFeeHistory.as_view(),
         name="finance-semester-fee-history"),
    path("semester-fees/<int:semester_id>/readiness/", api.SemesterFeeReadiness.as_view(),
         name="finance-semester-fee-readiness"),
]
