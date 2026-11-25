"""WF-11.01 Draft academic-period API (versioned, default-off, HDAC-enforced).

Mounted from config.urls under ``api/v1/academic/``. Every view answers 503 unless
``WORKSPACE_ACADEMIC_PERIODS_ENABLED`` is exactly True, then requires the Workspace session, the
explicit CSRF check on POST, the bounded duplicate-key-refusing JSON parser and no-store headers
inherited from WorkspaceSessionAPI. Authorization is decided ONLY by apps.academic.services
(fresh HDAC evaluation on every request, re-checked under lock for every mutation).

This is deliberately NOT a RegistrationReviewAPI subclass: the existing WF-02 release safeguard
(init_registration_review_metadata_local_dev.unexpected_review_routes) keeps covering exactly the
review routes it was approved for, and these routes neither match nor weaken it.

No activation, closure, archiving, fee or curriculum route exists here.
"""

from django.contrib.auth import get_user
from django.core.exceptions import RequestDataTooBig
from django.db import DatabaseError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.accounts.models import Account
from apps.accounts.session_auth import WorkspaceSessionAPI, _workspace_account

from . import services

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
}
CODE_MESSAGES = {
    "outside_school_year": "Dates must fall within the two calendar years of this school year.",
    "start_not_before_end": "The end date must be after the start date.",
}
CONFLICT_MESSAGES = {
    "school_year_exists": "This school year already exists.",
    "stale_version": "This semester was changed by someone else. Reload and try again.",
    "period_not_draft": "Only Draft semesters can be changed here.",
    "semesters_overlap": "The First semester must end before the Second semester starts.",
    "cross_year_overlap": "These dates overlap a semester of another school year. Review and confirm to save.",
    "period_in_use": "This school year is in use and cannot be deleted.",
    "confirmation_mismatch": "The confirmed school year does not match. Reload and try again.",
}


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
            fields = {name: [CODE_MESSAGES.get(code, FIELD_MESSAGES.get(name, "Check this value."))]
                      for name, code in exc.fields.items() if name in FIELD_MESSAGES}
            return _error("invalid_request", "Check the submitted academic-period details.", 400, fields=fields)
        if isinstance(exc, services.AcademicPeriodConflict):
            return _error("period_conflict", CONFLICT_MESSAGES[exc.reason], 409, reason=exc.reason)
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
