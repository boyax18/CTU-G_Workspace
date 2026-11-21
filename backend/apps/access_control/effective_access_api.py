"""WF-03.05: gated, read-only effective access / service state inspection.

Permission checks for *real* operations remain in services.has_permission; this
inspector cannot grant, revoke, activate a service or change the live session.
Under a selected, server-validated target role, use the SAME evaluator as API
operations. Avoid reverse-engineering a second authorization policy.
"""
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError, transaction
from rest_framework import exceptions
from rest_framework.response import Response

from apps.accounts.active_role_context import (
    available_roles, allowed_role_ids, bind_role_scope, context_enabled,
)
from apps.accounts.models import Account
from apps.accounts.registration_review_api import (
    RegistrationReviewAPI, ReviewAPIUnavailable, ReviewListThrottle, _full_name,
)
from .executor.client import enabled as executor_enabled
from .models import AccountPermission, AccountRole, Permission, RolePermission, Service
from .services import get_effective_permissions
from .technical_admin import has_technical_authority

INSPECT_CODE = "access_control.effective_permissions.inspect"
MAX_ID = 2_147_483_647
MAX_PERMISSIONS = 1024
MAX_SERVICES = 128


class EffectiveAccessAPI(RegistrationReviewAPI):
    def review_gate_open(self):
        return getattr(settings, "WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED", False) is True

    def initial(self, request, *args, **kwargs):
        # The protected executor has no active-role inspection contract.
        if executor_enabled() or not context_enabled():
            raise ReviewAPIUnavailable()
        return super().initial(request, *args, **kwargs)

    def require_technical(self, request):
        actor = self.require_actor(request, INSPECT_CODE)
        if not has_technical_authority(actor, INSPECT_CODE):
            raise exceptions.PermissionDenied("Technical Super Admin authority required.")
        return actor

    def handle_exception(self, exc):
        if isinstance(exc, DatabaseError):
            exc = ReviewAPIUnavailable()
        return super().handle_exception(exc)


def _target(account_id):
    if type(account_id) is not int or not 1 <= account_id <= MAX_ID:
        raise exceptions.NotFound()
    target = (Account.objects.using(DEFAULT_DB_ALIAS)
        .filter(pk=account_id, request_status="Approved", is_active=True,
                is_staff=False, is_superuser=False)
        .select_related("profile").first())
    if target is None:
        raise exceptions.NotFound()
    return target


class EffectiveAccessSearchView(EffectiveAccessAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request):
        self.require_technical(request)
        if set(request.query_params) != {"q"} or len(request.query_params.getlist("q")) != 1:
            raise exceptions.ValidationError("Search by CTU-G ID.")
        q = request.query_params.get("q", "")
        if type(q) is not str or not 3 <= len(q) <= 64 or q != q.strip():
            raise exceptions.ValidationError("Provide a CTU-G ID prefix (3-64 characters).")
        matches = list(Account.objects.using(DEFAULT_DB_ALIAS).filter(
            school_id__istartswith=q, request_status="Approved", is_active=True,
            is_staff=False, is_superuser=False,
        ).select_related("profile").order_by("school_id", "account_id")[:21])
        return Response({"accounts": [
            {"account_id": account.pk, "ctug_id": account.school_id,
             "full_name": _full_name(account) or "Name unavailable"}
            for account in matches[:20]], "has_next": len(matches) > 20})


class EffectiveAccessRolesView(EffectiveAccessAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id):
        self.require_technical(request)
        if request.query_params:
            raise exceptions.ValidationError("Unsupported query parameters.")
        account = _target(account_id)
        roles = available_roles(account.pk)  # current DB assignments and appointments
        if len(roles) > 32:
            raise ReviewAPIUnavailable()
        return Response({"account": {"account_id": account.pk,
                         "ctug_id": account.school_id,
                         "full_name": _full_name(account) or "Name unavailable"},
                         "roles": roles})


class EffectiveAccessDetailView(EffectiveAccessAPI):
    http_method_names = ["get", "head", "options"]
    throttle_classes = [ReviewListThrottle]

    def get(self, request, account_id, role_id):
        # Authorization uses the ACTOR's session role context before temporarily
        # binding the target scope for read-only evaluation.
        self.require_technical(request)
        if request.query_params or type(role_id) is not int or not 1 <= role_id <= MAX_ID:
            raise exceptions.ValidationError("Select an assigned role.")
        with transaction.atomic(using=DEFAULT_DB_ALIAS):
            account = _target(account_id)
            roles = available_roles(account.pk)
            chosen = next((role for role in roles if role["role_id"] == role_id), None)
            if chosen is None:
                raise exceptions.NotFound()
            allowed_ids = allowed_role_ids(account.pk, role_id)
            if not allowed_ids:
                raise exceptions.NotFound()
            service_rows = list(Service.objects.using(DEFAULT_DB_ALIAS)
                .order_by("service_code", "service_id")[:MAX_SERVICES + 1])
            if len(service_rows) > MAX_SERVICES:
                raise ReviewAPIUnavailable()
            permissions = list(Permission.objects.using(DEFAULT_DB_ALIAS)
                .select_related("service").order_by("permission_code", "permission_id")[:MAX_PERMISSIONS + 1])
            if len(permissions) > MAX_PERMISSIONS:
                raise ReviewAPIUnavailable()

            # The centralized evaluator is the only source of effective access.
            # Binding is context-local and restored before returning to the view.
            with bind_role_scope(account.pk, role_id):
                effective = get_effective_permissions(account)

            denied_ids = set(AccountPermission.objects.using(DEFAULT_DB_ALIAS)
                .filter(account=account, effect="Deny", is_active=True)
                .values_list("permission_id", flat=True))
            recorded_grant_ids = set(RolePermission.objects.using(DEFAULT_DB_ALIAS)
                .filter(role_id__in=allowed_ids, is_active=True,
                        role__is_active=True)
                .values_list("permission_id", flat=True))
            result = []
            for permission in permissions:
                is_effective = permission.permission_code in effective
                service_active = bool(permission.service.is_active)
                denied = permission.pk in denied_ids
                # These are explanatory HINTS only; all other security rules
                # (appointment, role status, scope, override policy) are resolved
                # exclusively by get_effective_permissions().
                result.append({
                    "permission_id": permission.pk,
                    "permission_code": permission.permission_code,
                    "permission_name": permission.permission_name,
                    "service_code": permission.service.service_code,
                    "service_active": service_active,
                    "effective": is_effective,
                    "explicit_deny": denied,
                    "role_grant_recorded": permission.pk in recorded_grant_ids,
                })
            service_summary = [{"service_code": service.service_code,
                                "service_name": service.service_name,
                                "is_active": bool(service.is_active)}
                               for service in service_rows]
        return Response({
            "account_id": account.pk,
            "role": chosen,
            "inherited_role_ids": sorted(allowed_ids.difference({role_id})),
            "services": service_summary,
            "permissions": result,
            "effective_count": len(effective),
        })
