"""WF-03.03 role-bound individual Grant API — isolated review profiles only.

A read hint is never authorization. The durable writer locks all actor,
target, role, permission and governance state inside a single transaction.
"""
from django.conf import settings
from django.db import DatabaseError
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.models import Account
from apps.accounts.registration_review_api import (
    RegistrationReviewAPI, ReviewAPIUnavailable, ReviewBurstThrottle,
    ReviewListThrottle, _full_name,
)
from .delegation import (
    ACCOUNT_PERMISSION_MANAGE, DelegationPolicyUnavailable,
    PermissionManagementDenied, PermissionManagementValidationError,
    is_governance_permission, is_reserved_role, require_delegation,
)
from .executor.client import enabled as executor_enabled
from .models import (
    AccountPermission, AccountPermissionRoleScope, AccountRole, Permission, Role,
)
from .mutations import AccountGrantStateConflict, grant_account_permission_for_role
from .ordinary_role_runtime import (
    ORDINARY_ROLE_NAMES, runtime_enforcement_enabled, verified_ordinary_roles_for,
)
from .technical_admin import has_technical_authority
from .writer_boundary import WriterBoundaryUnavailable

MAX_ID = 2_147_483_647
MAX_PERMISSIONS = 1024


def _eligible_target(actor, account_id):
    if type(account_id) is not int or not 1 <= account_id <= MAX_ID:
        raise exceptions.NotFound()
    target = Account.objects.filter(
        pk=account_id, request_status="Approved", is_active=True,
        is_staff=False, is_superuser=False,
    ).exclude(pk=actor.pk).select_related("profile").first()
    if target is None:
        raise exceptions.NotFound()
    return target


def _role_names_and_instances(target):
    return list(Role.objects.filter(
        account_assignments__account=target, is_active=True,
    ).order_by("role_name", "role_id"))


def _grant_allowed(actor, target, role, permission, target_all_role_names):
    if (role is None or is_reserved_role(role.role_name)
            or not permission.service.is_active or is_governance_permission(permission)):
        return False
    try:
        scope = require_delegation(actor, permission)
        if not target_all_role_names or not target_all_role_names <= scope.role_names:
            return False
        if role.role_name not in scope.role_names:
            return False
        if role.role_name in ORDINARY_ROLE_NAMES and (
            not runtime_enforcement_enabled()
            or role.role_name not in verified_ordinary_roles_for(target.pk)
        ):
            return False
        return True
    except (PermissionManagementDenied, PermissionManagementValidationError):
        return False


class AccountGrantAPI(RegistrationReviewAPI):
    def review_gate_open(self):
        return getattr(settings, "WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED", False) is True

    def initial(self, request, *args, **kwargs):
        # No account-permission protocols for the protected executor/profile.
        if (executor_enabled() and
                getattr(settings, "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED", False) is not True):
            raise ReviewAPIUnavailable()
        return super().initial(request, *args, **kwargs)

    def require_technical(self, request):
        actor = self.require_actor(request, ACCOUNT_PERMISSION_MANAGE)
        if not has_technical_authority(actor, ACCOUNT_PERMISSION_MANAGE):
            raise exceptions.PermissionDenied("Technical Super Admin authority required.")
        return actor

    def handle_exception(self, exc):
        if isinstance(exc, AccountGrantStateConflict):
            return Response({"error": {"code": "state_changed",
                                       "message": "Account permissions changed; reload first."}}, status=409)
        if isinstance(exc, (DelegationPolicyUnavailable, WriterBoundaryUnavailable, DatabaseError)):
            exc = ReviewAPIUnavailable()
        elif isinstance(exc, PermissionManagementDenied):
            exc = exceptions.PermissionDenied()
        elif isinstance(exc, PermissionManagementValidationError):
            exc = exceptions.ValidationError("Invalid account permission change.")
        return super().handle_exception(exc)


class AccountGrantSearchView(AccountGrantAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_technical(request)
        if set(request.query_params) != {"q"}:
            raise exceptions.ValidationError("Search by CTU-G ID.")
        q = request.query_params.get("q", "")
        if type(q) is not str or not 3 <= len(q.strip()) <= 64 or q != q.strip():
            raise exceptions.ValidationError("Provide a CTU-G ID prefix (3-64 characters).")
        # Protected, bounded directory; never expose pending/disabled/framework accounts.
        accounts = list(Account.objects.filter(
            school_id__istartswith=q, request_status="Approved", is_active=True,
            is_staff=False, is_superuser=False,
        ).exclude(pk=actor.pk).select_related("profile").order_by("school_id", "account_id")[:21])
        return Response({"accounts": [
            {"account_id": a.pk, "ctug_id": a.school_id, "full_name": _full_name(a) or "Name unavailable"}
            for a in accounts[:20]
        ], "has_next": len(accounts) > 20})


class AccountGrantDetailView(AccountGrantAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id):
        actor = self.require_technical(request)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query fields.")
        target = _eligible_target(actor, account_id)
        active_roles = _role_names_and_instances(target)
        all_names = set(AccountRole.objects.filter(account=target).values_list("role__role_name", flat=True))
        roles = [{"role_id": role.pk, "role_name": role.role_name} for role in active_roles]
        permissions = list(Permission.objects.select_related("service").order_by(
            "permission_code", "permission_id",
        )[:MAX_PERMISSIONS + 1])
        if len(permissions) > MAX_PERMISSIONS:
            raise ReviewAPIUnavailable()
        active = {item.permission_id: item for item in AccountPermission.objects.filter(
            account=target, is_active=True,
        )}
        # Scope table existence is required BEFORE the API can be switched on;
        # the missing-migration condition is converted into 503, not a bypass.
        scopes = dict(AccountPermissionRoleScope.objects.filter(
            account_permission__account=target,
        ).values_list("account_permission_id", "role_id"))
        can_write = (getattr(settings, "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED", False) is True
                     and getattr(settings, "WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED", False) is True)
        rows = []
        for permission in permissions:
            binding = active.get(permission.pk)
            scope_role_id = scopes.get(binding.pk) if binding is not None else None
            allowed_role_ids = [role.pk for role in active_roles if can_write and binding is None
                and _grant_allowed(actor, target, role, permission, all_names)]
            rows.append({
                "permission_id": permission.pk,
                "permission_code": permission.permission_code,
                "permission_name": permission.permission_name,
                "service_code": permission.service.service_code,
                "effect": binding.effect if binding is not None else None,
                "scope_role_id": scope_role_id,
                "grant_role_ids": allowed_role_ids,
            })
        return Response({"account": {
            "account_id": target.pk, "ctug_id": target.school_id,
            "full_name": _full_name(target) or "Name unavailable", "roles": roles,
        }, "permissions": rows})


class AccountGrantChangeView(AccountGrantAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request, account_id, permission_id):
        actor = self.require_technical(request)
        if (getattr(settings, "WORKSPACE_WF0303_ACCOUNT_GRANT_MUTATIONS_ENABLED", False) is not True
                or getattr(settings, "WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED", False) is not True):
            raise ReviewAPIUnavailable()
        body = request.data
        if (type(body) is not dict or set(body) != {"role_id", "expected_active"}
                or type(body["role_id"]) is not int or not 1 <= body["role_id"] <= MAX_ID
                or body["expected_active"] is not False):
            raise exceptions.ValidationError("Provide the selected role and an inactive expected state.")
        target = _eligible_target(actor, account_id)
        permission = Permission.objects.select_related("service").filter(pk=permission_id).first()
        role = Role.objects.filter(pk=body["role_id"], is_active=True).first()
        if permission is None or role is None or type(permission_id) is not int or not 1 <= permission_id <= MAX_ID:
            raise exceptions.NotFound()
        all_names = set(AccountRole.objects.filter(account=target).values_list("role__role_name", flat=True))
        if (not AccountRole.objects.filter(account=target, role=role).exists()
                or not _grant_allowed(actor, target, role, permission, all_names)):
            raise exceptions.PermissionDenied()
        changed = grant_account_permission_for_role(
            actor=actor, target=target, role=role,
            permission=permission, expected_active=body["expected_active"],
        )
        return Response({"account_id": target.pk, "permission_id": permission.pk,
                         "role_id": role.pk, "effect": "Grant", "changed": bool(changed)})
