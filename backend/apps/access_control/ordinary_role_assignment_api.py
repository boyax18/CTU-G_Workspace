"""WF-03.01 D-100 ordinary-role endpoints; isolated review URLconf ONLY.

An S1 Technical Super Admin with the exact effective ordinary.manage code is
required on both reads and writes. Appointment evidence comes only from a
trusted server-side verifier. A form field is never proof. No production mount.
"""

from django.db.models import Exists, OuterRef, Q
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.models import Account
from apps.accounts.registration_review_api import (
    MAX_ACCOUNT_ID, NAME_FIELDS, PAGE_SIZE, ReviewBurstThrottle, ReviewListThrottle,
    _full_name, _search_terms, _single,
)

from .models import AccountRole
from .ordinary_appointment_evidence import appointment_verified_for
from .role_assignment import assign_ordinary_role, ordinary_gate_open, revoke_ordinary_role
from .role_assignment_api import RoleAssignmentAPI, _active_roles
from .role_management import (
    ADMIN, INSTRUCTOR, ORDINARY_ASSIGNMENT_CODE, SSG_ADVISOR, STUDENT, TECHNICAL, TREASURER,
)
from .technical_admin import has_technical_authority

QUERY_FIELDS = frozenset({"page", "q"})
SLUG_TO_ROLE = {"treasurer": TREASURER, "ssg-advisor": SSG_ADVISOR}


class OrdinaryRoleAssignmentAPI(RoleAssignmentAPI):
    def review_gate_open(self):
        return ordinary_gate_open()

    def require_ordinary_authority(self, request):
        # require_actor also confirms the School Admin composite prerequisite.
        actor = self.require_actor(request, ORDINARY_ASSIGNMENT_CODE)
        if not has_technical_authority(actor, ORDINARY_ASSIGNMENT_CODE):
            raise exceptions.PermissionDenied("The effective Technical Super Admin profile is required.")
        return actor


def _ordinary_accounts(actor):
    base = AccountRole.objects.filter(account_id=OuterRef("pk"), role__is_active=True,
                                      role__role_name__in=(STUDENT, INSTRUCTOR))
    # Exclude even dormant protected-role assignments; enabling such a role later
    # must not combine it with ordinary assignment paths.
    privileged = AccountRole.objects.filter(account_id=OuterRef("pk"),
                                            role__role_name__in=(ADMIN, TECHNICAL))
    return (Account.objects.filter(request_status="Approved", is_active=True,
                                   is_staff=False, is_superuser=False)
            .exclude(pk=actor.pk).filter(Exists(base)).filter(~Exists(privileged)))


def _actions(roles, account_id, assigning_account_id):
    # These are DISPLAY HINTS, not grants: the service checks the exact state
    # under a row lock. No forged client claim can open the evidence gate.
    result = {}
    role_set = set(roles)
    for role, base in ((TREASURER, STUDENT), (SSG_ADVISOR, INSTRUCTOR)):
        conflicting = {STUDENT, INSTRUCTOR, TREASURER, SSG_ADVISOR, ADMIN, TECHNICAL} - {role, base}
        if base not in role_set or role_set & conflicting:
            result[role] = None
        elif role in role_set:
            result[role] = "revoke"
        elif appointment_verified_for(
            target_account_id=account_id, role_name=role, assigning_account_id=assigning_account_id,
        ) is True:
            result[role] = "assign"
        else:
            result[role] = None
    return result


class OrdinaryRoleListView(OrdinaryRoleAssignmentAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_ordinary_authority(request)
        params = request.query_params
        if set(params) - QUERY_FIELDS:
            raise exceptions.ValidationError("Unsupported query fields.")
        page_text = _single(params, "page", "1")
        if not page_text.isascii() or not page_text.isdecimal() or not 1 <= int(page_text) <= 10000:
            raise exceptions.ValidationError("Invalid page.")
        page = int(page_text)
        qs = _ordinary_accounts(actor)
        for term in _search_terms(_single(params, "q")):
            match = Q(school_id__istartswith=term)
            for field in NAME_FIELDS:
                match |= Q(**{f"profile__{field}__icontains": term})
            qs = qs.filter(match)
        qs = qs.select_related("profile").order_by("school_id", "account_id")
        start = (page - 1) * PAGE_SIZE
        rows = list(qs[start:start + PAGE_SIZE + 1])
        results = []
        for account in rows[:PAGE_SIZE]:
            roles = _active_roles(account.pk)
            actions = _actions(roles, account.pk, actor.pk)
            results.append({
                "account_id": account.pk, "school_id": account.school_id,
                "full_name": _full_name(account), "roles": roles,
                "treasurer_action": actions[TREASURER], "advisor_action": actions[SSG_ADVISOR],
            })
        return Response({"results": results, "page": page, "page_size": PAGE_SIZE,
                         "has_next": len(rows) > PAGE_SIZE})


class OrdinaryRoleChangeView(OrdinaryRoleAssignmentAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request, account_id, role_slug, action):
        actor = self.require_ordinary_authority(request)
        role = SLUG_TO_ROLE.get(role_slug)
        if role is None or action not in ("assign", "revoke") or not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        data = request.data
        if not isinstance(data, dict) or set(data) != {"expected_present"} or type(data["expected_present"]) is not bool:
            raise exceptions.ValidationError("Provide exactly the confirmed expected_present state.")
        change = assign_ordinary_role if action == "assign" else revoke_ordinary_role
        return Response(change(actor=actor, target_id=account_id, role_name=role,
                               expected_present=data["expected_present"]))
