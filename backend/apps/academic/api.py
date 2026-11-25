"""WF-11.01 Draft academic-period API (versioned, default-off, HDAC-enforced).

Mounted from config.urls under ``api/v1/academic/``. Every view answers 503 unless
``WORKSPACE_ACADEMIC_PERIODS_ENABLED`` is exactly True, then requires the Workspace session, the
explicit CSRF check on POST, the bounded duplicate-key-refusing JSON parser and no-store headers
inherited from WorkspaceSessionAPI. Authorization is decided ONLY by apps.academic.services
(fresh HDAC evaluation on every request, re-checked under lock for every mutation).

This is deliberately NOT a RegistrationReviewAPI subclass: the existing WF-02 release safeguard
(init_registration_review_metadata_local_dev.unexpected_review_routes) keeps covering exactly the
review routes it was approved for, and these routes neither match nor weaken it.

Lifecycle (activation/closure/archive) and correction confirmations are additionally gated by
WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED / WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED
(default off, refused in production); their GET previews need only the base gate and report
``feature_enabled``. No fee-setting or curriculum route exists here.
"""

from django.contrib.auth import get_user
from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import Account
from apps.accounts.session_auth import WorkspaceSessionAPI, _workspace_account

from . import corrections, history, lifecycle, services
from .dependencies import CLOSURE_OBLIGATIONS, IMPACT_RECORDS, REQUIRED_PREREQUISITES

CREATE_FIELDS = frozenset({"start_year"})
DATES_FIELDS = frozenset({"start_date", "end_date", "expected_version", "acknowledge_cross_year_overlap"})
DATES_REQUIRED = frozenset({"start_date", "end_date", "expected_version"})
DELETE_FIELDS = frozenset({"expected_start_year"})
LIST_QUERY_FIELDS = frozenset({"page"})

FIELD_MESSAGES = {
    "start_year": "Enter a starting year from 2000 to 2100.",
    "start_date": "Enter a valid start date.",
    "end_date": "Enter a valid end date.",
    "expected_version": "Reload the semester and try again.",
    "expected_start_year": "Confirm the school year you are deleting.",
    "acknowledge_cross_year_overlap": "Confirm the overlap warning.",
    "page": "Invalid page.",
    "reason_code": "Choose the reason for this change.",
    "reason_note": "Explain the change in 10 to 500 characters.",
    "acknowledged_warnings": "Review the warnings again.",
    "acknowledged_impacts": "Review the impact summary again.",
}
CODE_MESSAGES = {
    "outside_school_year": "Dates must fall within the two calendar years of this school year.",
    "start_not_before_end": "The end date must be after the start date.",
}
REQUIRED_MESSAGES = {"start_date": "Enter the start date.", "end_date": "Enter the end date."}
CONFLICT_MESSAGES = {
    "school_year_exists": "This school year already exists.",
    "stale_version": "This semester was changed by someone else. Reload and try again.",
    "period_not_draft": "Only Draft semesters can be changed here.",
    "semesters_overlap": "The First semester must end before the Second semester starts.",
    "cross_year_overlap": "These dates overlap a semester of another school year. Review and confirm to save.",
    "period_in_use": "This school year is in use and cannot be deleted.",
    "confirmation_mismatch": "The confirmed school year does not match. Reload and try again.",
    "period_is_draft": "Draft semesters are edited with their Draft dates instead.",
    "impact_unavailable": ("The effect on student, fee or clearance records cannot be checked yet, "
                           "so this change is not allowed."),
    "impact_review_required": "This change affects existing records. Review the impact summary and confirm.",
    "no_change": "The dates are unchanged.",
}
TRANSITION_MESSAGES = {
    "not_draft": "Only a Draft semester can be activated.",
    "not_active": "Only the Active semester can be closed.",
    "not_closed": "Only a Closed semester can be archived.",
    "prerequisites_missing": "Activation prerequisites are not met.",
    "active_changed": "The Active semester changed. Review the summary again.",
    "confirmation_required": "Confirm the change to continue.",
    "warnings_changed": "The warnings changed. Review the summary again.",
    "stale_version": "This semester was changed by someone else. Reload and try again.",
    "transition_conflict": "The change could not be applied. Reload and try again.",
}
_DETAIL_KEYS = (frozenset(REQUIRED_PREREQUISITES) | frozenset(CLOSURE_OBLIGATIONS) | frozenset(IMPACT_RECORDS)
                | {"valid_dates"})


class AcademicPeriodsUnavailable(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Academic-period management is unavailable."
    default_code = "academic_periods_unavailable"


class _AccountThrottle(SimpleRateThrottle):
    """Per signed-in account (session read exactly as the views do); never forwarding headers."""

    def get_cache_key(self, request, view):
        user = get_user(request._request)
        account_id = getattr(user, "pk", None) if isinstance(user, Account) else None
        ident = (f"account:{account_id}" if type(account_id) is int
                 else "address:" + request.META.get("REMOTE_ADDR", "unknown"))
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AcademicReadThrottle(_AccountThrottle):
    scope = "workspace_academic_read"
    rate = "60/min"


class AcademicWriteThrottle(_AccountThrottle):
    scope = "workspace_academic_write"
    rate = "20/min"


def _error(code, message, http_status, **extra):
    body = {"code": code, "message": message}
    body.update(extra)
    return Response({"error": body}, status=http_status)


class AcademicPeriodAPI(WorkspaceSessionAPI):
    def initial(self, request, *args, **kwargs):
        if not services.gate_open():
            raise AcademicPeriodsUnavailable()
        super().initial(request, *args, **kwargs)

    def get_throttles(self):
        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AcademicReadThrottle()]
        return [AcademicWriteThrottle()]

    def actor(self, request):
        actor = _workspace_account(get_user(request._request))
        if actor is None:
            raise exceptions.NotAuthenticated()
        return actor

    @staticmethod
    def body(request, allowed, required=None):
        data = request.data
        required = allowed if required is None else required
        if not isinstance(data, dict) or set(data) - allowed or required - set(data):
            raise exceptions.ValidationError("Unsupported or missing fields.")
        return data

    def handle_exception(self, exc):
        if isinstance(exc, services.AcademicPeriodInvalid):
            fields = {name: [REQUIRED_MESSAGES.get(name) if code == "required" and name in REQUIRED_MESSAGES
                             else CODE_MESSAGES.get(code, FIELD_MESSAGES.get(name, "Check this value."))]
                      for name, code in exc.fields.items() if name in FIELD_MESSAGES}
            return _error("invalid_request", "Check the submitted academic-period details.", 400, fields=fields)
        if isinstance(exc, services.AcademicPeriodConflict):
            return _error("period_conflict", CONFLICT_MESSAGES[exc.reason], 409, reason=exc.reason,
                          details=[k for k in exc.details if k in _DETAIL_KEYS])
        if isinstance(exc, lifecycle.TransitionRefused):
            return _error("period_conflict", TRANSITION_MESSAGES[exc.reason], 409, reason=exc.reason,
                          details=[k for k in exc.missing if k in _DETAIL_KEYS])
        if isinstance(exc, services.AcademicPeriodFeatureDisabled):
            return _error("feature_disabled", "This academic-period action is not enabled.", 503)
        if isinstance(exc, services.AcademicPeriodDenied):
            return _error("access_denied", "You cannot manage academic periods.", 403, reason=exc.reason)
        if isinstance(exc, services.AcademicPeriodNotFound):
            return _error("period_unavailable", "The academic period is unavailable.", 404)
        if isinstance(exc, (services.AcademicPeriodUnavailable, DatabaseError)):
            return _error("academic_periods_unavailable", "Academic-period management is unavailable.", 503)
        if isinstance(exc, RequestDataTooBig):
            exc = exceptions.ParseError()
        if isinstance(exc, exceptions.APIException):
            if isinstance(exc, exceptions.PermissionDenied):
                # The only PermissionDenied raised outside the service is WorkspaceSessionAPI's CSRF check.
                return _error("csrf_failed", "Security check failed. Refresh the page and try again.", 403)
            messages = {
                400: ("invalid_request", "Check the submitted academic-period details."),
                401: ("authentication_required", "Sign in to continue."),
                404: ("period_unavailable", "The academic period is unavailable."),
                405: ("method_not_allowed", "This method is not supported."),
                406: ("not_acceptable", "Accept application/json."),
                415: ("unsupported_media_type", "Send application/json."),
                429: ("rate_limited", "Too many requests. Please wait before trying again."),
                503: ("academic_periods_unavailable", "Academic-period management is unavailable."),
            }
            code, message = messages.get(exc.status_code, ("request_failed", "The request could not be completed."))
            response = _error(code, message, exc.status_code)
            wait = getattr(exc, "wait", None)
            if exc.status_code == 429 and wait:
                response["Retry-After"] = str(int(wait) + 1)
            return response
        return super().handle_exception(exc)


class SchoolYearCollectionView(AcademicPeriodAPI):
    http_method_names = ["get", "post", "head", "options"]

    def get(self, request):
        actor = self.actor(request)
        params = request.query_params
        if set(params) - LIST_QUERY_FIELDS or len(params.getlist("page")) > 1:
            raise exceptions.ValidationError("Unsupported query fields.")
        raw = params.get("page", "1")
        if not raw.isascii() or not raw.isdecimal() or len(raw) > 4:
            raise services.AcademicPeriodInvalid({"page": "invalid"})
        return Response(services.list_school_years(actor=actor, page=int(raw)))

    def post(self, request):
        actor = self.actor(request)
        data = self.body(request, CREATE_FIELDS)
        payload = services.create_school_year(actor=actor, start_year=data["start_year"])
        return Response(payload, status=201)


class SemesterDatesView(AcademicPeriodAPI):
    http_method_names = ["post", "options"]

    def post(self, request, semester_id):
        actor = self.actor(request)
        data = self.body(request, DATES_FIELDS, DATES_REQUIRED)
        payload = services.update_semester_dates(
            actor=actor, semester_id=semester_id, start_date=data["start_date"], end_date=data["end_date"],
            expected_version=data["expected_version"],
            acknowledge_cross_year_overlap=data.get("acknowledge_cross_year_overlap", False))
        return Response(payload)


class SchoolYearDeleteView(AcademicPeriodAPI):
    http_method_names = ["post", "options"]

    def post(self, request, school_year_id):
        actor = self.actor(request)
        data = self.body(request, DELETE_FIELDS)
        return Response(services.delete_school_year(
            actor=actor, school_year_id=school_year_id, expected_start_year=data["expected_start_year"]))


class _SemesterPreviewConfirmView(AcademicPeriodAPI):
    """GET = read-only preview (base gate); POST = explicit confirmation (separately gated)."""

    http_method_names = ["get", "post", "head", "options"]
    preview = None
    confirm_fields = frozenset()
    optional_fields = frozenset()

    def get(self, request, semester_id):
        actor = self.actor(request)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query fields.")
        return Response(type(self).preview(actor=actor, semester_id=semester_id))

    def post(self, request, semester_id):
        actor = self.actor(request)
        data = self.body(request, self.confirm_fields | self.optional_fields, self.confirm_fields)
        return Response(self.confirm(actor, semester_id, data))


TRANSITION_FIELDS = frozenset({"confirmed", "expected_version", "acknowledged_warnings"})


class SemesterActivationView(_SemesterPreviewConfirmView):
    preview = staticmethod(lifecycle.activation_preview)
    confirm_fields = TRANSITION_FIELDS | {"expected_active_semester_id"}

    def confirm(self, actor, semester_id, data):
        return lifecycle.activate_semester(
            actor=actor, semester_id=semester_id, expected_version=data["expected_version"],
            expected_active_semester_id=data["expected_active_semester_id"],
            acknowledged_warnings=data["acknowledged_warnings"], confirmed=data["confirmed"])


class SemesterClosureView(_SemesterPreviewConfirmView):
    preview = staticmethod(lifecycle.closure_preview)
    confirm_fields = TRANSITION_FIELDS

    def confirm(self, actor, semester_id, data):
        return lifecycle.close_semester(
            actor=actor, semester_id=semester_id, expected_version=data["expected_version"],
            acknowledged_warnings=data["acknowledged_warnings"], confirmed=data["confirmed"])


class SemesterArchiveView(_SemesterPreviewConfirmView):
    preview = staticmethod(lifecycle.archive_preview)
    confirm_fields = TRANSITION_FIELDS

    def confirm(self, actor, semester_id, data):
        return lifecycle.archive_semester(
            actor=actor, semester_id=semester_id, expected_version=data["expected_version"],
            acknowledged_warnings=data["acknowledged_warnings"], confirmed=data["confirmed"])


class SemesterCorrectionView(_SemesterPreviewConfirmView):
    preview = staticmethod(corrections.correction_preview)
    confirm_fields = frozenset({"start_date", "end_date", "expected_version", "reason_code", "reason_note"})
    optional_fields = frozenset({"acknowledged_impacts", "acknowledge_cross_year_overlap"})

    def confirm(self, actor, semester_id, data):
        return corrections.correct_semester_dates(
            actor=actor, semester_id=semester_id, start_date=data["start_date"], end_date=data["end_date"],
            expected_version=data["expected_version"], reason_code=data["reason_code"],
            reason_note=data["reason_note"], acknowledged_impacts=data.get("acknowledged_impacts", []),
            acknowledge_cross_year_overlap=data.get("acknowledge_cross_year_overlap", False))


class SchoolYearHistoryView(AcademicPeriodAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request, school_year_id):
        actor = self.actor(request)
        params = request.query_params
        if set(params) - LIST_QUERY_FIELDS or len(params.getlist("page")) > 1:
            raise exceptions.ValidationError("Unsupported query fields.")
        raw = params.get("page", "1")
        if not raw.isascii() or not raw.isdecimal() or len(raw) > 4:
            raise services.AcademicPeriodInvalid({"page": "invalid"})
        return Response(history.school_year_history(actor=actor, school_year_id=school_year_id, page=int(raw)))
