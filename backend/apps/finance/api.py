"""Semester organizational fee API under ``api/v1/finance/semester-fees/`` (all default-off).

Reuses the academic API conventions (session, explicit CSRF on POST, bounded duplicate-key-refusing
JSON, no-store, fixed error codes). Every view answers 503 unless
WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED is exactly True; approval confirmation also needs
WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED (503 ``feature_disabled``). Authorization is decided only
by apps.finance.fees (exact finance.fee_schedule.manage through a genuine Admin role grant).
"""

from rest_framework import exceptions
from rest_framework.response import Response

from apps.academic import services
from apps.academic.api import AcademicPeriodAPI, AcademicPeriodsUnavailable, _AccountThrottle, _error
from apps.accounts.session_auth import WorkspaceSessionAPI

from . import fees

FIELD_MESSAGES = {
    "amount": "Enter the full fee in pesos, from 0.00 to 100,000.00, with up to two decimal places.",
    "change_reason": "Explain the change in 10 to 500 characters.",
    "expected_draft_version": "Reload and try again.",
    "expected_version": "Reload and try again.",
    "revision_id": "Reload and try again.",
    "expected_current_approved_revision_id": "Reload and try again.",
    "acknowledged_warnings": "Review the warnings again.",
    "confirm_zero_amount": "Confirm the zero amount explicitly.",
}
REQUIRED = {"amount": "Enter the fee amount. ₱0.00 must be entered explicitly."}
CONFLICT_MESSAGES = {
    "period_closed": "Closed and Archived semesters keep their fee history; it cannot be changed here.",
    "draft_exists": "This semester already has a Draft fee. Edit it instead.",
    "no_draft": "There is no Draft fee to change or approve. Reload and try again.",
    "stale_version": "This fee was changed by someone else. Reload and try again.",
    "no_change": "Nothing changed.",
    "reason_required": "Explain why the approved fee is being revised.",
    "approved_changed": "The approved fee changed. Review it again.",
    "confirmation_required": "Confirm the approval to continue.",
    "zero_confirmation_required": "Confirm that the full fee for this semester is ₱0.00.",
    "warnings_changed": "The warnings changed. Review them again.",
    "impact_unavailable": "The effect on existing student fee obligations cannot be checked yet, so this revision cannot be approved.",
    "obligations_assessed": "Student fee obligations already use the approved fee. A financial adjustment process is required.",
    "transition_conflict": "The change could not be applied. Reload and try again.",
}


class FeeReadThrottle(_AccountThrottle):
    scope = "workspace_finance_fee_read"
    rate = "120/min"


class FeeWriteThrottle(_AccountThrottle):
    scope = "workspace_finance_fee_write"
    rate = "30/min"


class SemesterFeeAPI(AcademicPeriodAPI):
    def initial(self, request, *args, **kwargs):
        if not fees.configuration_enabled():
            raise AcademicPeriodsUnavailable()
        WorkspaceSessionAPI.initial(self, request, *args, **kwargs)  # skip the period gate; keep CSRF/throttles

    def get_throttles(self):
        return [FeeReadThrottle()] if self.request.method in ("GET", "HEAD", "OPTIONS") else [FeeWriteThrottle()]

    def handle_exception(self, exc):
        if isinstance(exc, fees.FeeConflict):
            return _error("fee_conflict", CONFLICT_MESSAGES[exc.reason], 409, reason=exc.reason)
        if isinstance(exc, services.AcademicPeriodInvalid):
            fields = {name: [REQUIRED.get(name) if code == "required" and name in REQUIRED else FIELD_MESSAGES[name]]
                      for name, code in exc.fields.items() if name in FIELD_MESSAGES}
            return _error("invalid_request", "Check the submitted fee details.", 400, fields=fields)
        if isinstance(exc, services.AcademicPeriodFeatureDisabled):
            return _error("feature_disabled", "Semester fee approval is not enabled.", 503)
        if isinstance(exc, (services.AcademicPeriodUnavailable, AcademicPeriodsUnavailable)):
            return _error("semester_fees_unavailable", "Semester fee configuration is unavailable.", 503)
        if isinstance(exc, services.AcademicPeriodNotFound):
            return _error("not_found", "The semester is unavailable.", 404)
        return super().handle_exception(exc)

    def no_query(self, request):
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query fields.")


class SemesterFeeList(SemesterFeeAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        self.no_query(request)
        return Response(fees.list_semester_fees(actor=self.actor(request)))


class SemesterFeeDetail(SemesterFeeAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request, semester_id):
        self.no_query(request)
        return Response(fees.get_semester_fee(actor=self.actor(request), semester_id=semester_id))


class SemesterFeeDraft(SemesterFeeAPI):
    http_method_names = ["post", "options"]

    def post(self, request, semester_id):
        actor = self.actor(request)
        data = self.body(request, frozenset({"amount", "expected_draft_version", "change_reason"}),
                         frozenset({"amount", "expected_draft_version"}))
        return Response(fees.save_draft(actor=actor, semester_id=semester_id, amount=data["amount"],
                                        expected_draft_version=data["expected_draft_version"],
                                        change_reason=data.get("change_reason")))


class SemesterFeeDraftWithdraw(SemesterFeeAPI):
    http_method_names = ["post", "options"]

    def post(self, request, semester_id):
        actor = self.actor(request)
        data = self.body(request, frozenset({"expected_draft_version"}))
        return Response(fees.withdraw_draft(actor=actor, semester_id=semester_id,
                                            expected_draft_version=data["expected_draft_version"]))


APPROVAL_FIELDS = frozenset({"revision_id", "expected_version", "expected_current_approved_revision_id",
                             "acknowledged_warnings", "confirmed", "confirm_zero_amount"})


class SemesterFeeApproval(SemesterFeeAPI):
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request, semester_id):
        self.no_query(request)
        return Response(fees.approval_preview(actor=self.actor(request), semester_id=semester_id))

    def post(self, request, semester_id):
        actor = self.actor(request)
        data = self.body(request, APPROVAL_FIELDS, APPROVAL_FIELDS - {"confirm_zero_amount"})
        return Response(fees.approve(
            actor=actor, semester_id=semester_id, revision_id=data["revision_id"],
            expected_version=data["expected_version"],
            expected_current_approved_revision_id=data["expected_current_approved_revision_id"],
            acknowledged_warnings=data["acknowledged_warnings"], confirmed=data["confirmed"],
            confirm_zero_amount=data.get("confirm_zero_amount", False)))


class SemesterFeeHistory(SemesterFeeAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request, semester_id):
        self.no_query(request)
        return Response(fees.fee_history(actor=self.actor(request), semester_id=semester_id))


class SemesterFeeReadiness(SemesterFeeAPI):
    """Read-only approved-fee readiness for the academic activation actor (academic.periods.manage)."""

    http_method_names = ["get", "head", "options"]

    def get(self, request, semester_id):
        self.no_query(request)
        return Response(fees.readiness_for_activation(actor=self.actor(request), semester_id=semester_id))
