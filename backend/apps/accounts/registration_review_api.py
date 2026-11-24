"""Registration review API: every view is disabled by default.

Decisions (approve/reject, WF-02.03/02.04) are not registered in config.urls and require
TWO separately approved feature gates: WORKSPACE_REGISTRATION_REVIEW_API_ENABLED and
WORKSPACE_REGISTRATION_APPROVAL_ENABLED.

WF-02.01 (D-31): only the read-only pending list is mounted in config.urls, behind its own
WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED gate (default off). The list gate never opens a
decision view. The isolated review URLconfs keep their existing two-gate behavior.
"""

from django.conf import settings
from django.contrib.auth import get_user
from django.core.exceptions import ObjectDoesNotExist, RequestDataTooBig
from django.db import DatabaseError
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Value, When
from django.db.models.functions import Lower
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle

from apps.access_control.models import AccountRole, Service
from apps.access_control.services import has_permission
from apps.access_control.writer_boundary import WriterBoundaryUnavailable

from .models import Account
from .registration_review import (
    ELIGIBILITY_SOURCES,
    REJECTION_CODES,
    RegistrationApprovalNotAllowed,
    RegistrationRejectionNotAllowed,
    RegistrationReviewDenied,
    RegistrationReviewUnavailable,
    approve_registration,
    reject_registration,
)
from .session_auth import WorkspaceSessionAPI, _workspace_account


READ_CODE = "accounts.registration_requests.read"
# WF-02.03: the only accepted attestation sources; the service checks the one valid for the role.
APPROVAL_SOURCES = frozenset(ELIGIBILITY_SOURCES.values())
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


class ReviewListThrottle(SimpleRateThrottle):
    """WF-02.01 D-36: listing has its own 60/min budget per signed-in account.

    Decisions keep ReviewBurstThrottle. Anonymous callers (refused with 401 later)
    fall back to the socket address; forwarding headers are never trusted.
    """

    scope = "workspace_review_list"
    rate = "60/min"

    def get_cache_key(self, request, view):
        # DRF marks request.user anonymous here (authentication_classes=[]), so read the
        # session exactly as require_actor does. This identifies; it never authorizes.
        user = get_user(request._request)
        account_id = getattr(user, "pk", None) if isinstance(user, Account) else None
        ident = f"account:{account_id}" if type(account_id) is int else "address:" + request.META.get("REMOTE_ADDR", "unknown")
        return self.cache_format % {"scope": self.scope, "ident": ident}


def _decision_gates_open():
    return bool(
        getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_API_ENABLED", False)
        and getattr(settings, "WORKSPACE_REGISTRATION_APPROVAL_ENABLED", False)
    )


class RegistrationReviewAPI(WorkspaceSessionAPI):
    """Inherit explicit CSRF, bounded JSON parser and no-store headers."""

    throttle_classes = [ReviewBurstThrottle]

    def review_gate_open(self):
        return _decision_gates_open()

    def initial(self, request, *args, **kwargs):
        if not self.review_gate_open():
            raise ReviewAPIUnavailable()
        super().initial(request, *args, **kwargs)

    def handle_exception(self, exc):
        # WF-02.03 D-47: a policy refusal on an application the reviewer may read is reported
        # with a fixed reason only (never applicant data); the application stays Pending.
        if isinstance(exc, RegistrationApprovalNotAllowed):
            return Response({"error": {
                "code": "approval_not_allowed", "reason": exc.reason,
                "message": "Approval is not allowed for this application.",
            }}, status=409)
        # WF-02.04 D-58: fixed rejection policy conflicts, raised only after authorization and
        # eligibility were confirmed in the lock; stale or unknown targets stay 404 below.
        if isinstance(exc, RegistrationRejectionNotAllowed):
            return Response({"error": {
                "code": "rejection_not_allowed", "reason": exc.reason,
                "message": "Rejection is not allowed for this application.",
            }}, status=409)
        # Stable, non-enumerating responses: a stale target and an inaccessible
        # target are intentionally indistinguishable to the caller.
        if isinstance(exc, RegistrationReviewDenied):
            return Response({"error": {"code": "request_unavailable", "message": "Registration request is unavailable."}}, status=404)
        if isinstance(exc, (RegistrationReviewUnavailable, WriterBoundaryUnavailable, DatabaseError)):
            # WF-02.01 R-13: a database failure is a review outage, never an auth result.
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


PAGE_SIZE = 20
LIST_QUERY_FIELDS = frozenset({"page", "status", "q", "role", "proof", "sort"})
LIST_ROLES = frozenset({"Student", "Instructor"})
LIST_PROOF = frozenset({"verified", "legacy"})
# Stable orderings; account_id breaks ties so pages never overlap or skip rows.
LIST_SORTS = {
    "submitted": ("created_at", "account_id"),
    "-submitted": ("-created_at", "-account_id"),
    "school_id": ("school_id", "account_id"),
    "-school_id": ("-school_id", "-account_id"),
}
MAX_SEARCH_LENGTH = 50
MAX_SEARCH_TERMS = 5
NAME_FIELDS = ("first_name", "middle_name", "last_name", "suffix")


def _single(params, name, default=None):
    values = params.getlist(name)
    if len(values) > 1:
        raise exceptions.ValidationError("Repeated query field.")
    return values[0] if values else default


def _search_terms(raw):
    if raw is None:
        return ()
    term = raw.strip()
    # Printable ASCII only: School IDs and the current registration name fields.
    if not 1 <= len(term) <= MAX_SEARCH_LENGTH or not all(" " <= ch <= "~" for ch in term):
        raise exceptions.ValidationError("Invalid search.")
    terms = term.split()
    if len(terms) > MAX_SEARCH_TERMS:
        raise exceptions.ValidationError("Invalid search.")
    return tuple(terms)


def _read_gate_open():
    """D-31/D-37: the independent read switch, or the isolated review configs' existing pair."""
    return bool(getattr(settings, "WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED", False)) or _decision_gates_open()


def _reviewable_pending(actor):
    """Applications a reviewer may read (WF-02.01 list and WF-02.02 detail share this filter).

    Current ERD is single-campus; do not invent tenant/campus scope. Excludes assigned,
    previously reviewed and privileged accounts (D-35) and the reviewer's own account.
    """
    assigned = AccountRole.objects.filter(account_id=OuterRef("pk"))
    return (Account.objects
        .filter(
            request_status="Pending", is_active=False,
            is_staff=False, is_superuser=False,
            requested_role__role_name__in=tuple(LIST_ROLES),
            requested_role__is_active=True,
            reviewed_by__isnull=True, reviewed_at__isnull=True,
        )
        .exclude(pk=actor.pk)
        .filter(~Exists(assigned)))


def _full_name(account):
    try:
        profile = account.profile
    except ObjectDoesNotExist:
        return None
    parts = [getattr(profile, field) for field in NAME_FIELDS]
    name = " ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())
    return name or None


class PendingRegistrationRequestsView(RegistrationReviewAPI):
    """WF-02.01: read-only list of eligible Pending Student/Instructor applications."""

    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def review_gate_open(self):
        return _read_gate_open()

    def get(self, request):
        actor = self.require_actor(request, READ_CODE)
        params = request.query_params
        if set(params) - LIST_QUERY_FIELDS:
            raise exceptions.ValidationError("Unsupported query fields.")
        if _single(params, "status", "Pending") != "Pending":
            raise exceptions.ValidationError("Only Pending may be listed.")
        page_text = _single(params, "page", "1")
        if not page_text.isascii() or not page_text.isdecimal():
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        if not 1 <= page <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        terms = _search_terms(_single(params, "q"))
        role = _single(params, "role")
        if role is not None and role not in LIST_ROLES:
            raise exceptions.ValidationError("Invalid role.")
        proof = _single(params, "proof")
        if proof is not None and proof not in LIST_PROOF:
            raise exceptions.ValidationError("Invalid proof filter.")
        sort = _single(params, "sort", "submitted")
        if sort not in LIST_SORTS:
            raise exceptions.ValidationError("Invalid sort.")

        qs = _reviewable_pending(actor)
        if role is not None:
            qs = qs.filter(requested_role__role_name=role)
        for term in terms:
            # ORM lookups escape % and _; every term must match somewhere.
            match = Q(school_id__istartswith=term)
            for field in NAME_FIELDS:
                match |= Q(**{f"profile__{field}__icontains": term})
            qs = qs.filter(match)
        # D-34: proof counts only when it was recorded for the address now on file.
        qs = qs.annotate(_email_lower=Lower("email"), _proof_lower=Lower("email_verified_address")).annotate(
            email_verified=Case(
                When(
                    Q(email__isnull=False, email_verified_at__isnull=False,
                      email_verified_address__isnull=False, _email_lower=F("_proof_lower")),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        if proof is not None:
            qs = qs.filter(email_verified=(proof == "verified"))
        qs = qs.select_related("requested_role", "profile").order_by(*LIST_SORTS[sort])

        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start:start + PAGE_SIZE + 1])
        # D-32 (amended 24 Nov 2026 by the owner): permitted fields plus the applicant's email
        # address on file, which the queue now shows instead of an email-proof column. Still no
        # hashes, tokens, verification evidence details or reviewer data.
        results = [
            {
                "account_id": account.pk,
                "school_id": account.school_id,
                "full_name": _full_name(account),
                "requested_role": account.requested_role.role_name,
                "created_at": account.created_at.isoformat(),
                "email_verified": bool(account.email_verified),
                "email": account.email or None,
            }
            for account in rows[:PAGE_SIZE]
        ]
        response = Response({
            "results": results, "page": page, "page_size": PAGE_SIZE,
            "has_next": len(rows) > PAGE_SIZE,
        })
        from .management_availability import attach_pending_registration_actions
        return attach_pending_registration_actions(response, actor, request)


class ApproveRegistrationRequestView(RegistrationReviewAPI):
    http_method_names = ["post", "options"]

    def post(self, request, account_id):
        actor = self.require_actor(request, APPROVE_CODE)
        # WF-02.03 D-45: exactly the reviewer's attestation; nothing else (no role, status or
        # account fields) is accepted, so the request cannot choose what is assigned.
        data = request.data
        if not isinstance(data, dict) or set(data) != {"eligibility_confirmed", "eligibility_source"}:
            raise exceptions.ValidationError("Approval takes exactly the eligibility attestation.")
        if (type(data["eligibility_confirmed"]) is not bool or type(data["eligibility_source"]) is not str
                or data["eligibility_source"] not in APPROVAL_SOURCES):
            raise exceptions.ValidationError("Invalid eligibility attestation.")
        if not 1 <= account_id <= 2_147_483_647:
            raise exceptions.NotFound()
        decided_id = approve_registration(actor=actor, target_id=account_id, attestation={
            "confirmed": data["eligibility_confirmed"], "source": data["eligibility_source"],
        })
        # Success means the approval notification is durably queued in the same
        # transaction; delivery happens later and is not claimed here.
        return Response({"account_id": decided_id, "status": "Approved", "notification": "queued"})


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
        # WF-02.04 D-54: success means the encrypted email is QUEUED in the same committed
        # transaction; delivery happens later in the outbox worker and is never claimed here.
        return Response({"account_id": decided_id, "status": "Rejected", "notification": "queued"})


ID_LABELS = dict.fromkeys(("Student", "Instructor"), "CTU-G ID")
INSTITUTIONAL_SUBJECT = {"Student": "enrollment", "Instructor": "employment"}
MAX_ACCOUNT_ID = 2_147_483_647


def _profile_or_none(account):
    try:
        return account.profile
    except ObjectDoesNotExist:
        return None


def _clean(value):
    return value.strip() if isinstance(value, str) and value.strip() else None


def _email_evidence(account):
    """D-43: four distinct states; only the first is evidence, and only of mailbox control."""
    email = _clean(account.email)
    proof = _clean(account.email_verified_address)
    if email is None:
        return {"state": "no_email", "verified_at": None}
    if account.email_verified_at is None or proof is None:
        return {"state": "no_proof", "verified_at": None}
    if proof.lower() != email.lower():
        return {"state": "address_changed", "verified_at": None}
    return {"state": "verified", "verified_at": account.email_verified_at.isoformat()}


class PendingRegistrationDetailView(RegistrationReviewAPI):
    """WF-02.02: read-only detail of ONE application that WF-02.01 would list.

    Strictly read-only (D-39): no write of reviewed_by, reviewed_at, request_status,
    is_active, roles or registration data, and no read audit (D-40). Unknown, ineligible
    and no-longer-Pending identifiers share one 404 so nothing can be enumerated.
    """

    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]  # one read budget with the list (D-36)

    def review_gate_open(self):
        return _read_gate_open()

    def get(self, request, account_id):
        actor = self.require_actor(request, READ_CODE)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query fields.")
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        account = (_reviewable_pending(actor)
            .select_related("requested_role", "profile")
            .filter(pk=account_id)
            .first())
        if account is None:
            raise exceptions.NotFound()
        role = account.requested_role.role_name
        profile = _profile_or_none(account)
        name = {
            "first": _clean(getattr(profile, "first_name", None)),
            "middle": _clean(getattr(profile, "middle_name", None)),
            "last": _clean(getattr(profile, "last_name", None)),
            "suffix": _clean(getattr(profile, "suffix", None)),
        }
        notes = []
        if profile is None:
            notes.append("missing_profile")
        else:
            if name["first"] is None:
                notes.append("missing_first_name")
            if name["last"] is None:
                notes.append("missing_last_name")
        # D-38: the full email only here, never in the list, never in logs or errors.
        response = Response({
            "account_id": account.pk,
            "school_id": account.school_id,
            "id_label": ID_LABELS[role],
            "name": name,
            "full_name": _full_name(account),
            "email": _clean(account.email),
            "requested_role": role,
            "request_status": "Pending",
            "created_at": account.created_at.isoformat(),
            "email_evidence": _email_evidence(account),
            "institutional_check": {"subject": INSTITUTIONAL_SUBJECT[role], "verified_by_workspace": False},
            "data_notes": notes,
        })
        from .management_availability import attach_available_actions
        return attach_available_actions(response, actor, account.pk, "registration")
