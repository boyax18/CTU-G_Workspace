"""AR-6C1 draft API: disabled by default, not registered in config.urls.

Requires TWO separately approved feature gates before any request proceeds:
WORKSPACE_REGISTRATION_REVIEW_API_ENABLED and WORKSPACE_REGISTRATION_APPROVAL_ENABLED.
Do not enable the gates or register routes until institutional governance approval.
"""

from django.conf import settings
from django.contrib.auth import get_user
from django.core.exceptions import RequestDataTooBig
from django.db.models import Exists, OuterRef
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.access_control.models import AccountRole, Service
from apps.access_control.services import has_permission

from .models import Account
from .registration_review import (
    REJECTION_CODES,
    RegistrationReviewDenied,
    RegistrationReviewUnavailable,
    approve_registration,
    reject_registration,
)
from .session_auth import WorkspaceSessionAPI, _workspace_account


READ_CODE = "accounts.registration_requests.read"
APPROVE_CODE = "accounts.registration_requests.approve"
REJECT_CODE = "accounts.registration_requests.reject"


class ReviewAPIUnavailable(exceptions.APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Registration review is unavailable."
    default_code = "review_unavailable"


class ReviewBurstThrottle(SimpleRateThrottle):
    scope = "workspace_review_burst"
    rate = "20/min"

    def get_cache_key(self, request, view):
        # Never trust forwarding headers without a configured trusted proxy.
        address = request.META.get("REMOTE_ADDR", "unknown")
        return self.cache_format % {"scope": self.scope, "ident": address}


class RegistrationReviewAPI(WorkspaceSessionAPI):
    """Inherit explicit CSRF, bounded JSON parser and no-store headers."""

    throttle_classes = [ReviewBurstThrottle]

    def initial(self, request, *args, **kwargs):
        if not (
            getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False)
            and getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False)
        ):
            raise ReviewAPIUnavailable()
        super().initial(request, *args, **kwargs)

    def handle_exception(self, exc):
        # Stable, non-enumerating responses: a stale target and an inaccessible
        # target are intentionally indistinguishable to the caller.
        if isinstance(exc, RegistrationReviewDenied):
            return Response({"error": {"code": "request_unavailable", "message": "Registration request is unavailable."}}, status=404)
        if isinstance(exc, RegistrationReviewUnavailable):
            return Response({"error": {"code": "review_unavailable", "message": "Registration review is unavailable."}}, status=503)
        if isinstance(exc, RequestDataTooBig):
            exc = exceptions.ParseError("Request body too large.")
        if isinstance(exc, exceptions.APIException):
            messages = {
                400: ("invalid_request", "Check the request data."),
                401: ("authentication_required", "Sign in to continue."),
                403: ("access_denied", "You cannot perform this action."),
                404: ("request_unavailable", "Registration request is unavailable."),
                405: ("method_not_allowed", "Method not supported."),
                406: ("not_acceptable", "Request JSON."),
                415: ("unsupported_media_type", "Send JSON."),
                429: ("rate_limited", "Too many attempts. Try later."),
                503: ("review_unavailable", "Registration review is unavailable."),
            }
            code, message = messages.get(exc.status_code, ("request_failed", "Request failed."))
            return Response({"error": {"code": code, "message": message}}, status=exc.status_code)
        # WorkspaceSessionAPI's generic handler safely hides unexpected errors.
        return super().handle_exception(exc)

    def require_actor(self, request, permission_code):
        actor = _workspace_account(get_user(request._request))
        if actor is None:
            raise exceptions.NotAuthenticated("Workspace session required.")
        if not AccountRole.objects.filter(
            account_id=actor.pk,
            account__is_active=True,
            account__request_status="Approved",
            role__role_name="Admin",
            role__is_active=True,
        ).exists():
            raise exceptions.PermissionDenied("Admin assignment required.")
        # Review service locks both service rows for mutations. Match the same
        # prerequisite for read-only views, without granting by role name.
        active_services = set(Service.objects.filter(
            service_code__in=("accounts", "access_control"),
            is_active=True,
        ).values_list("service_code", flat=True))
        if active_services != {"accounts", "access_control"}:
            raise ReviewAPIUnavailable()
        if not has_permission(actor, permission_code):
            raise exceptions.PermissionDenied("Exact effective permission required.")
        return actor


class PendingRegistrationRequestsView(RegistrationReviewAPI):
    http_method_names = ["get", "head", "options"]

    def get(self, request):
        actor = self.require_actor(request, READ_CODE)
        if set(request.query_params) - {"page", "status"}:
            raise exceptions.ValidationError("Unsupported query fields.")
        if request.query_params.get("status", "Pending") != "Pending":
            raise exceptions.ValidationError("Only Pending may be listed.")
        page_text = request.query_params.get("page", "1")
        if not page_text.isascii() or not page_text.isdecimal():
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        if not 1 <= page <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        # Current ERD is single-campus; do not invent tenant/campus scope.
        # Exclude assigned, previously reviewed and privileged accounts.
        assigned = AccountRole.objects.filter(account_id=OuterRef("pk"))
        qs = (Account.objects
            .filter(
                request_status="Pending", is_active=False,
                is_staff=False, is_superuser=False,
                requested_role__role_name__in=("Student", "Instructor"),
                requested_role__is_active=True,
                reviewed_by__isnull=True, reviewed_at__isnull=True,
            )
            .exclude(pk=actor.pk)
            .filter(~Exists(assigned))
            .select_related("requested_role")
            .order_by("account_id"))
        page_size = 20
        start = (page - 1) * page_size
        # Minimum proposed fields; no email, hashes or reset tokens.
        results = [
            {
                "account_id": account.pk,
                "school_id": account.school_id,
                "requested_role": account.requested_role.role_name,
                "created_at": account.created_at.isoformat(),
            }
            for account in qs[start:start + page_size]
        ]
        return Response({"results": results, "page": page, "page_size": page_size})


class ApproveRegistrationRequestView(RegistrationReviewAPI):
    http_method_names = ["post", "options"]

    def post(self, request, account_id):
        actor = self.require_actor(request, APPROVE_CODE)
        if not isinstance(request.data, dict) or request.data:
            raise exceptions.ValidationError("Approval takes an empty JSON object.")
        if not 1 <= account_id <= 2_147_483_647:
            raise exceptions.NotFound()
        decided_id = approve_registration(actor=actor, target_id=account_id)
        return Response({"account_id": decided_id, "status": "Approved"})


class RejectRegistrationRequestView(RegistrationReviewAPI):
    http_method_names = ["post", "options"]

    def post(self, request, account_id):
        actor = self.require_actor(request, REJECT_CODE)
        if not isinstance(request.data, dict) or set(request.data) != {"rejection_code"}:
            raise exceptions.ValidationError("A rejection_code is required.")
        rejection_code = request.data["rejection_code"]
        if type(rejection_code) is not str or rejection_code not in REJECTION_CODES:
            raise exceptions.ValidationError("Invalid rejection_code.")
        if not 1 <= account_id <= 2_147_483_647:
            raise exceptions.NotFound()
        decided_id = reject_registration(actor=actor, target_id=account_id, rejection_code=rejection_code)
        return Response({"account_id": decided_id, "status": "Rejected"})
