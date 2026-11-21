"""WF-03.04 individual restrictions — isolated development routes only.

New Deny is account-wide (including all active role contexts). Removing a
Deny can increase access; both operations require explicit confirmed actions.
Protected-executor mode is unsupported and refuses before business logic.
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
    is_governance_permission, require_delegation,
)
from .executor.client import enabled as executor_enabled
from .models import AccountPermission, AccountPermissionRoleScope, AccountRole, Permission
from .mutations import AccountRestrictionStateConflict, change_account_restriction
from .technical_admin import has_technical_authority
from .writer_boundary import WriterBoundaryUnavailable

MAX_ID = 2_147_483_647
MAX_PERMISSIONS = 1024


def eligible_target(actor, account_id):
    if type(account_id) is not int or not 1 <= account_id <= MAX_ID:
        raise exceptions.NotFound()
    target = Account.objects.filter(
        pk=account_id, request_status="Approved", is_active=True,
        is_staff=False, is_superuser=False,
    ).exclude(pk=actor.pk).select_related("profile").first()
    if target is None:
        raise exceptions.NotFound()
    return target


def eligible_permission(actor, target, permission):
    if not permission.service.is_active or is_governance_permission(permission):
        return False
    try:
        scope = require_delegation(actor, permission)
        # Respect all role assignments, including inactive and reserved roles,
        # just as the locked mutation writer does.
        names = set(AccountRole.objects.filter(account=target).values_list("role__role_name", flat=True))
        return bool(names) and names <= scope.role_names
    except (PermissionManagementDenied, PermissionManagementValidationError):
        return False


class RestrictionAPI(RegistrationReviewAPI):
    def review_gate_open(self):
        return getattr(settings, "WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED", False) is True

    def initial(self, request, *args, **kwargs):
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
        if isinstance(exc, AccountRestrictionStateConflict):
            return Response({"error": {"code": "state_changed",
                        "message": "Account permissions changed; reload before continuing."}}, status=409)
        if isinstance(exc, (DelegationPolicyUnavailable, WriterBoundaryUnavailable, DatabaseError)):
            exc = ReviewAPIUnavailable()
        elif isinstance(exc, PermissionManagementDenied):
            exc = exceptions.PermissionDenied()
        elif isinstance(exc, PermissionManagementValidationError):
            exc = exceptions.ValidationError("Invalid account restriction.")
        return super().handle_exception(exc)


class RestrictionSearchView(RestrictionAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        actor = self.require_technical(request)
        if set(request.query_params) != {"q"}:
            raise exceptions.ValidationError("Search by CTU-G ID.")
        q = request.query_params.get("q", "")
        if type(q) is not str or not 3 <= len(q) <= 64 or q != q.strip():
            raise exceptions.ValidationError("Provide a CTU-G ID prefix (3-64 characters).")
        matches = list(Account.objects.filter(
            school_id__istartswith=q, request_status="Approved", is_active=True,
            is_staff=False, is_superuser=False,
        ).exclude(pk=actor.pk).select_related("profile").order_by("school_id", "account_id")[:21])
        return Response({"accounts": [{
            "account_id": a.pk, "ctug_id": a.school_id,
            "full_name": _full_name(a) or "Name unavailable",
        } for a in matches[:20]], "has_next": len(matches) > 20})


class RestrictionDetailView(RestrictionAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id):
        actor = self.require_technical(request)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query parameters.")
        target = eligible_target(actor, account_id)
        permissions = list(Permission.objects.select_related("service").order_by(
            "permission_code", "permission_id",
        )[:MAX_PERMISSIONS + 1])
        if len(permissions) > MAX_PERMISSIONS:
            raise ReviewAPIUnavailable()
        overrides = {r.permission_id: r for r in AccountPermission.objects.filter(
            account=target, is_active=True,
        )}
        # Migration 0005 required for safely inspecting scoped Grants. If not
        # applied, the resulting DB failure becomes 503, never an unsafe read.
        scopes = dict(AccountPermissionRoleScope.objects.filter(
            account_permission__account=target,
        ).values_list("account_permission_id", "role_id"))
        write_enabled = (
            getattr(settings, "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED", False) is True
            and getattr(settings, "WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED", False) is True
        )
        rows = []
        for permission in permissions:
            override = overrides.get(permission.pk)
            effect = override.effect if override else None
            scope_id = scopes.get(override.pk) if override and effect == "Grant" else None
            eligible = write_enabled and eligible_permission(actor, target, permission)
            rows.append({
                "permission_id": permission.pk,
                "permission_code": permission.permission_code,
                "permission_name": permission.permission_name,
                "service_code": permission.service.service_code,
                "effect": effect,
                "scope_role_id": scope_id,
                "can_deny": bool(eligible and effect != "Deny"),
                "can_revoke_grant": bool(eligible and effect == "Grant"),
                "can_remove_deny": bool(eligible and effect == "Deny"),
            })
        return Response({"account": {
            "account_id": target.pk, "ctug_id": target.school_id,
            "full_name": _full_name(target) or "Name unavailable",
        }, "permissions": rows})


class RestrictionChangeView(RestrictionAPI):
    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def post(self, request, account_id, permission_id):
        actor = self.require_technical(request)
        if (getattr(settings, "WORKSPACE_WF0304_ACCOUNT_RESTRICTION_MUTATIONS_ENABLED", False) is not True
                or getattr(settings, "WORKSPACE_WF0303_SCOPED_GRANT_EVALUATION_ENABLED", False) is not True):
            raise ReviewAPIUnavailable()
        body = request.data
        if (type(body) is not dict or set(body) != {"action", "expected_effect", "expected_scope_role_id"}
                or type(body["action"]) is not str
                or body["action"] not in {"deny", "revoke_grant", "remove_deny"}
                or (body["expected_effect"] is not None and
                    (type(body["expected_effect"]) is not str or body["expected_effect"] not in {"Grant", "Deny"}))
                or (body["expected_scope_role_id"] is not None
                    and (type(body["expected_scope_role_id"]) is not int
                        or not 1 <= body["expected_scope_role_id"] <= MAX_ID))):
            raise exceptions.ValidationError("Provide an action and the observed override state.")
        target = eligible_target(actor, account_id)
        if type(permission_id) is not int or not 1 <= permission_id <= MAX_ID:
            raise exceptions.NotFound()
        permission = Permission.objects.select_related("service").filter(pk=permission_id).first()
        if permission is None:
            raise exceptions.NotFound()
        if not eligible_permission(actor, target, permission):
            raise exceptions.PermissionDenied()
        changed = change_account_restriction(
            actor=actor, target=target, permission=permission,
            action=body["action"], expected_effect=body["expected_effect"],
            expected_scope_role_id=body["expected_scope_role_id"],
        )
        return Response({"account_id": target.pk, "permission_id": permission.pk,
                         "action": body["action"], "changed": bool(changed)})
