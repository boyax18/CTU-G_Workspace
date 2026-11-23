"""WF-02.05 account directory, read-only detail and status changes (stage 1).

Reads are mounted directly in config.urls behind an independent default-off directory gate.
The isolated account_status_urls additionally mounts separately gated status writes.
Every view subclasses RegistrationReviewAPI on purpose: it reuses the explicit CSRF check, the
bounded JSON parser, no-store headers, the Admin-assignment pre-check and error mapping, and the
existing P1/P3C release safeguard already refuses any mounted RegistrationReviewAPI route that is
not an approved read route (D-69). Its own default-off gate WORKSPACE_ACCOUNT_STATUS_ENABLED.
"""

from django.conf import settings
from django.db.models import Exists, OuterRef, Q
from rest_framework import exceptions
from rest_framework.response import Response

from apps.access_control.audit import APPROVAL_ACTION
from apps.access_control.models import AccessAuditLog, AccountRole

from .account_status import (
    ACTIVATE_ACTION, ACTIVATE_CODE, READ_CODE, SUSPEND_ACTION, SUSPEND_CODE, AccountStatusConflict,
    activate_account, gate_open, is_reserved_role, suspend_account,
)
from .models import Account
from .registration_review_api import (
    MAX_ACCOUNT_ID, NAME_FIELDS, PAGE_SIZE, RegistrationReviewAPI, ReviewBurstThrottle, ReviewListThrottle,
    _clean, _full_name, _profile_or_none, _search_terms, _single,
)

QUERY_FIELDS = frozenset({"page", "q", "status"})
STATUSES = {"active": True, "inactive": False}


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
    return "CTU-G ID"


# WF-02.06 D-74 (owner-approved 18 Nov 2026): the ONLY audit events a school-account reader may see,
# each reduced to a fixed event type, a fixed description, its time and a server-made actor label.
# Raw audit JSON, reasons, approval attestations, IDs and identities are never returned (D-73, D-77).
HISTORY_EVENTS = {
    APPROVAL_ACTION: ("registration_approved", "Registration approved"),
    SUSPEND_ACTION: ("account_deactivated", "Account deactivated"),
    ACTIVATE_ACTION: ("account_reactivated", "Account reactivated"),
}
STATUS_ACTIONS = (SUSPEND_ACTION, ACTIVATE_ACTION)
# What each status event must record (old is_active, new is_active); anything else is not shown.
_STATUS_STATES = {SUSPEND_ACTION: (True, False), ACTIVATE_ACTION: (False, True)}
HISTORY_QUERY_FIELDS = frozenset({"page"})
_HISTORY_COLUMNS = ("action", "actor_account_id", "old_value", "new_value", "created_at")


def _history_rows(account_id, actions):
    """Deterministic newest first (the append-only primary key); only the columns needed."""
    return (AccessAuditLog.objects.filter(target_account_id=account_id, action__in=actions)
            .order_by("-access_audit_log_id").values(*_HISTORY_COLUMNS))


def _actor_label(actor_id, viewer):
    # D-73: generated from the trusted session identity; never a name, e-mail, School ID or ID.
    return "You" if type(actor_id) is int and actor_id == viewer.pk else "An administrator"


def _recorded_state(value):
    state = value.get("is_active") if isinstance(value, dict) else None
    return state if type(state) is bool else None


def _history_entry(row, viewer):
    event, description = HISTORY_EVENTS[row["action"]]
    entry = {"event": event, "description": description,
             "occurred_at": row["created_at"].isoformat(), "actor": _actor_label(row["actor_account_id"], viewer)}
    if row["action"] in _STATUS_STATES:
        # Only states the audit row itself recorded, and only when they match the event; never inferred.
        recorded = (_recorded_state(row["old_value"]), _recorded_state(row["new_value"]))
        previous, new = recorded if recorded == _STATUS_STATES[row["action"]] else (None, None)
        entry.update(previous_is_active=previous, new_is_active=new)
    return entry


def _approved_at(account):
    """D-75: the append-only approval audit time (written with the decision); otherwise the account's
    own reviewed_at (legacy rows); otherwise None ("Not recorded"). A date is never inferred."""
    audited = (AccessAuditLog.objects.filter(target_account_id=account.pk, action=APPROVAL_ACTION)
               .order_by("-access_audit_log_id").values_list("created_at", flat=True).first())
    moment = audited or account.reviewed_at
    return moment.isoformat() if moment else None


def _page(params):
    page_text = _single(params, "page", "1")
    if not page_text.isascii() or not page_text.isdecimal() or not 1 <= int(page_text) <= 10000:
        raise exceptions.ValidationError("Invalid page.")
    return int(page_text)


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


class SchoolAccountReadAPI(AccountStatusAPI):
    def review_gate_open(self):
        return getattr(settings, "WORKSPACE_ACCOUNT_DIRECTORY_ENABLED", False) is True or gate_open()


class SchoolAccountListView(SchoolAccountReadAPI):
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


class SchoolAccountDetailView(SchoolAccountReadAPI):
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
        response = Response({
            "account_id": account.pk, "school_id": account.school_id, "id_label": _id_label(account),
            "name": {field: _clean(getattr(profile, f"{field}_name" if field != "suffix" else "suffix", None))
                     for field in ("first", "middle", "last", "suffix")},
            # Current state comes from the account row only (D-75); history never decides it.
            "full_name": _full_name(account), "roles": roles, "is_active": account.is_active,
            "request_status": account.request_status, "created_at": account.created_at.isoformat(),
            # A hint only: the service re-checks it inside the lock (D-63).
            "can_reactivate": bool(roles),
            # WF-02.06 D-75/D-76: status dates; None means "Not recorded".
            "approved_at": _approved_at(account),
            "last_status_change": next(
                (_history_entry(row, actor) for row in _history_rows(account.pk, STATUS_ACTIONS)[:1]), None),
        })
        from .management_availability import attach_available_actions
        return attach_available_actions(response, actor, account.pk, "status")


class SchoolAccountHistoryView(SchoolAccountReadAPI):
    """WF-02.06 D-76: read-only, paginated status history of ONE eligible account.

    Same gate, session, Admin-assignment, service and exact-permission checks as the WF-02.05 detail
    (accounts.school_accounts.read; account-level Deny wins), the same eligibility queryset and the
    same non-enumerating 404. Only the D-74 allowlisted events are read; nothing is written.
    """

    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id):
        actor = self.require_actor(request, READ_CODE)
        params = request.query_params
        if set(params) - HISTORY_QUERY_FIELDS:
            raise exceptions.ValidationError("Unsupported query fields.")
        page = _page(params)
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        if not eligible_accounts(actor).filter(pk=account_id).exists():
            raise exceptions.NotFound()
        start = (page - 1) * PAGE_SIZE
        rows = list(_history_rows(account_id, tuple(HISTORY_EVENTS))[start:start + PAGE_SIZE + 1])
        return Response({"results": [_history_entry(row, actor) for row in rows[:PAGE_SIZE]],
                         "page": page, "page_size": PAGE_SIZE, "has_next": len(rows) > PAGE_SIZE})


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
