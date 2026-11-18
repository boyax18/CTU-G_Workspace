"""WF-02.05 account directory, read-only detail and status changes (stage 1).

Mounted ONLY by apps.accounts.account_status_urls (an isolated URLconf); never by config.urls.
Every view subclasses RegistrationReviewAPI on purpose: it reuses the explicit CSRF check, the
bounded JSON parser, no-store headers, the Admin-assignment pre-check and error mapping, and the
existing P1/P3C release safeguard already refuses any mounted RegistrationReviewAPI route that is
not an approved read route (D-69). Its own default-off gate WORKSPACE_ACCOUNT_STATUS_ENABLED.
"""

from django.db.models import Exists, OuterRef, Q
from rest_framework import exceptions
from rest_framework.response import Response

from apps.access_control.models import AccountRole

from .account_status import (
    ACTIVATE_CODE, READ_CODE, SUSPEND_CODE, AccountStatusConflict,
    activate_account, gate_open, is_reserved_role, suspend_account,
)
from .models import Account
from .registration_review_api import (
    MAX_ACCOUNT_ID, NAME_FIELDS, PAGE_SIZE, RegistrationReviewAPI, ReviewBurstThrottle, ReviewListThrottle,
    _clean, _full_name, _profile_or_none, _search_terms, _single,
)

QUERY_FIELDS = frozenset({"page", "q", "status"})
STATUSES = {"active": True, "inactive": False}
ID_LABELS = {"Instructor": "Staff ID"}


def _reserved_role_ids():
    from apps.access_control.models import Role
    return [role.pk for role in Role.objects.all() if is_reserved_role(role.role_name)]


def eligible_accounts(actor):
    """D-63/D-71: Approved, non-framework accounts holding no administrator or governance role,
    never the actor. Pending and Rejected accounts are never listed."""
    reserved = AccountRole.objects.filter(account_id=OuterRef("pk"), role_id__in=_reserved_role_ids())
    return (Account.objects
            .filter(request_status="Approved", is_staff=False, is_superuser=False)
            .exclude(pk=actor.pk)
            .filter(~Exists(reserved)))


def _roles(account):
    return sorted(set(AccountRole.objects.filter(account_id=account.pk, role__is_active=True)
                      .values_list("role__role_name", flat=True)))


def _id_label(account):
    role = getattr(account.requested_role, "role_name", None)
    return ID_LABELS.get(role, "School ID")


class AccountStatusAPI(RegistrationReviewAPI):
    def review_gate_open(self):
        return gate_open()

    def handle_exception(self, exc):
        if isinstance(exc, AccountStatusConflict):
            return Response({"error": {
                "code": "account_status_conflict", "reason": exc.reason,
                "message": "The account status could not be changed.",
            }}, status=409)
        return super().handle_exception(exc)


class SchoolAccountListView(AccountStatusAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_actor(request, READ_CODE)
        params = request.query_params
        if set(params) - QUERY_FIELDS:
            raise exceptions.ValidationError("Unsupported query fields.")
        page_text = _single(params, "page", "1")
        if not page_text.isascii() or not page_text.isdecimal() or not 1 <= int(page_text) <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        status_value = _single(params, "status")
        if status_value is not None and status_value not in STATUSES:
            raise exceptions.ValidationError("Invalid status.")
        qs = eligible_accounts(actor)
        if status_value is not None:
            qs = qs.filter(is_active=STATUSES[status_value])
        for term in _search_terms(_single(params, "q")):
            match = Q(school_id__istartswith=term)
            for field in NAME_FIELDS:
                match |= Q(**{f"profile__{field}__icontains": term})
            qs = qs.filter(match)
        qs = qs.select_related("requested_role", "profile").order_by("school_id", "account_id")
        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start:start + PAGE_SIZE + 1])
        # Minimized fields: no email, credentials, review data, sessions or permission detail.
        results = [{
            "account_id": account.pk, "school_id": account.school_id, "id_label": _id_label(account),
            "full_name": _full_name(account), "roles": _roles(account), "is_active": account.is_active,
        } for account in rows[:PAGE_SIZE]]
        return Response({"results": results, "page": page, "page_size": PAGE_SIZE, "has_next": len(rows) > PAGE_SIZE})


class SchoolAccountDetailView(AccountStatusAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id):
        actor = self.require_actor(request, READ_CODE)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query fields.")
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        account = eligible_accounts(actor).select_related("requested_role", "profile").filter(pk=account_id).first()
        if account is None:
            raise exceptions.NotFound()
        profile = _profile_or_none(account)
        roles = _roles(account)
        return Response({
            "account_id": account.pk, "school_id": account.school_id, "id_label": _id_label(account),
            "name": {field: _clean(getattr(profile, f"{field}_name" if field != "suffix" else "suffix", None))
                     for field in ("first", "middle", "last", "suffix")},
            "full_name": _full_name(account), "roles": roles, "is_active": account.is_active,
            "request_status": "Approved", "created_at": account.created_at.isoformat(),
            # A hint only: the service re-checks it inside the lock (D-63).
            "can_reactivate": bool(roles),
        })


class _StatusChangeView(AccountStatusAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]
    code = None
    change = None

    def post(self, request, account_id):
        actor = self.require_actor(request, self.code)
        data = request.data
        if not isinstance(data, dict) or set(data) != {"expected_active"} or type(data["expected_active"]) is not bool:
            raise exceptions.ValidationError("Provide exactly the confirmed expected_active state.")
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        result = type(self).change(actor=actor, target_id=account_id, expected_active=data["expected_active"])
        return Response(result)


class SuspendSchoolAccountView(_StatusChangeView):
    code = SUSPEND_CODE
    change = staticmethod(suspend_account)


class ActivateSchoolAccountView(_StatusChangeView):
    code = ACTIVATE_CODE
    change = staticmethod(activate_account)
