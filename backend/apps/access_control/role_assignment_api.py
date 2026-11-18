"""WF-03.01 Role assignments API for the Technical Super Admin (owner-approved stage B, 18 Nov 2026).

Isolated URLconf (role_assignment_urls); NOT mounted by config.urls, review_local_urls or
review_sandbox_urls — mounting it is a separately authorized protected change. Every view subclasses
RegistrationReviewAPI on purpose: explicit CSRF, bounded JSON, no-store headers, error mapping, and the
existing release safeguard already refuses any mounted RegistrationReviewAPI route outside the
reviewed local modes. Default-off WORKSPACE_ROLE_ASSIGNMENT_ENABLED. Django authorizes every request:
the composite Technical Super Admin profile plus access_control.admin_assignments.manage.
"""

from django.db.models import Exists, OuterRef, Q
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.models import Account
from apps.accounts.registration_review_api import (
    MAX_ACCOUNT_ID, NAME_FIELDS, PAGE_SIZE, RegistrationReviewAPI, ReviewBurstThrottle, ReviewListThrottle,
    _full_name, _search_terms, _single,
)

from .models import AccountRole
from .role_assignment import assign_school_admin, gate_open, revoke_school_admin
from .role_management import (
    ADMIN, ADMIN_ASSIGNMENT_CODE, INSTRUCTOR, TECHNICAL, RoleChangeConflict, RoleChangeDenied, RoleChangeUnavailable,
)
from .technical_admin import has_technical_authority

QUERY_FIELDS = frozenset({"page", "q"})


class RoleAssignmentAPI(RegistrationReviewAPI):
    def review_gate_open(self):
        return gate_open()

    def require_technical(self, request):
        actor = self.require_actor(request, ADMIN_ASSIGNMENT_CODE)
        if not has_technical_authority(actor, ADMIN_ASSIGNMENT_CODE):
            raise exceptions.PermissionDenied("The Technical Super Admin profile is required.")
        return actor

    def handle_exception(self, exc):
        if isinstance(exc, RoleChangeConflict):
            return Response({"error": {"code": "role_assignment_conflict", "reason": exc.reason,
                                       "message": "The role assignment could not be changed."}}, status=409)
        if isinstance(exc, RoleChangeDenied):
            exc = exceptions.NotFound()  # the shared non-enumerating 404
        elif isinstance(exc, RoleChangeUnavailable):
            exc = exceptions.APIException()
            exc.status_code = 503
        return super().handle_exception(exc)


def _active_roles(account_id):
    return sorted(set(AccountRole.objects.filter(account_id=account_id, role__is_active=True)
                      .values_list("role__role_name", flat=True)))


def _hint(roles, others_hold_admin):
    """A display hint only; the service re-checks everything inside the lock."""
    if ADMIN not in roles:
        return ("assign", None) if INSTRUCTOR in roles else (None, "not_instructor")
    if TECHNICAL in roles:
        return None, "technical_super_admin"
    if INSTRUCTOR not in roles:
        return None, "legacy_admin"
    return ("revoke", None) if others_hold_admin else (None, "last_school_admin")


def manageable_accounts(actor):
    """Approved, active, non-framework accounts holding an active Instructor or Admin role; never the actor."""
    holds = AccountRole.objects.filter(account_id=OuterRef("pk"), role__is_active=True,
                                       role__role_name__in=[INSTRUCTOR, ADMIN])
    return (Account.objects.filter(request_status="Approved", is_active=True, is_staff=False, is_superuser=False)
            .exclude(pk=actor.pk).filter(Exists(holds)))


class RoleAssignmentListView(RoleAssignmentAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_technical(request)
        params = request.query_params
        if set(params) - QUERY_FIELDS:
            raise exceptions.ValidationError("Unsupported query fields.")
        page_text = _single(params, "page", "1")
        if not page_text.isascii() or not page_text.isdecimal() or not 1 <= int(page_text) <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        qs = manageable_accounts(actor)
        for term in _search_terms(_single(params, "q")):
            match = Q(school_id__istartswith=term)
            for field in NAME_FIELDS:
                match |= Q(**{f"profile__{field}__icontains": term})
            qs = qs.filter(match)
        qs = qs.select_related("profile").order_by("school_id", "account_id")
        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start:start + PAGE_SIZE + 1])
        admins = effective_holders_ids()
        results = []
        for account in rows[:PAGE_SIZE]:
            roles = _active_roles(account.pk)
            action, restriction = _hint(roles, bool(admins - {account.pk}))
            results.append({"account_id": account.pk, "school_id": account.school_id, "full_name": _full_name(account),
                            "roles": roles, "school_admin_action": action, "restriction": restriction})
        return Response({"results": results, "page": page, "page_size": PAGE_SIZE, "has_next": len(rows) > PAGE_SIZE})


def effective_holders_ids():
    return set(effective_holders_query().values_list("pk", flat=True))


def effective_holders_query():
    # Read-only (no locks) for display hints; the mutation path locks before counting.
    return Account.objects.filter(is_active=True, request_status="Approved", is_staff=False, is_superuser=False,
                                  pk__in=AccountRole.objects.filter(role__role_name=ADMIN, role__is_active=True)
                                  .values("account_id"))


class _SchoolAdminChangeView(RoleAssignmentAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]
    change = None

    def post(self, request, account_id):
        actor = self.require_technical(request)
        data = request.data
        if not isinstance(data, dict) or set(data) != {"expected_present"} or type(data["expected_present"]) is not bool:
            raise exceptions.ValidationError("Provide exactly the confirmed expected_present state.")
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        return Response(type(self).change(actor=actor, target_id=account_id, expected_present=data["expected_present"]))


class AssignSchoolAdminView(_SchoolAdminChangeView):
    change = staticmethod(assign_school_admin)


class RevokeSchoolAdminView(_SchoolAdminChangeView):
    change = staticmethod(revoke_school_admin)


__all__ = ["RoleAssignmentListView", "AssignSchoolAdminView", "RevokeSchoolAdminView"]
