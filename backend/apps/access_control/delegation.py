"""Explicit proposed delegation contracts; absent approval always denies.

ACCESS_CONTROL_DELEGATION_POLICY is server configuration, never request data.
No policy or catalogue rows are installed by importing or using this module.
"""

from dataclasses import dataclass
import re
import unicodedata

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DEFAULT_DB_ALIAS

from apps.accounts.models import Account

from .models import Permission
from .services import has_permission

ROLE_PERMISSION_MANAGE = "access_control.role_permissions.manage"
ACCOUNT_PERMISSION_MANAGE = "access_control.account_permissions.manage"
GOVERNANCE_SERVICE = "access_control"


class PermissionManagementDenied(PermissionDenied):
    pass


class DelegationPolicyUnavailable(PermissionManagementDenied):
    pass


class PermissionManagementValidationError(ValidationError):
    pass


def _normalized(value):
    text = "".join(char for char in unicodedata.normalize("NFKD", value) if not unicodedata.combining(char))
    return re.sub(r"[\W_]+", "", text.casefold())


def is_reserved_role(role_name):
    return _normalized(role_name) in {"admin", "superadmin", "technicalsuperadmin"}


def is_governance_permission(permission):
    reserved = {"accesscontrol", "accounts", "auth", "authentication", "authorization", "security", "governance", "admin"}
    return any(_normalized(value) in reserved for value in (
        permission.service.service_code,
        permission.module_name,
        permission.permission_code.split(".", 1)[0],
    ))


@dataclass(frozen=True)
class ApprovedDelegationScope:
    service_code: str
    authority_permission: str
    permission_codes: frozenset[str]
    role_names: frozenset[str]


def _policy_error():
    raise DelegationPolicyUnavailable("An explicit reviewed delegation scope is required.")


def _strings(value, limit, max_length):
    if type(value) not in (list, tuple, frozenset) or not 1 <= len(value) <= limit:
        _policy_error()
    if any(type(item) is not str or not item.strip() or len(item) > max_length for item in value):
        _policy_error()
    if len(frozenset(value)) != len(value):
        _policy_error()
    return frozenset(value)


def approved_scope(service_code):
    """Validate reviewed configuration and return an immutable service scope.

    Required entry: authority_permission, permission_codes, role_names.
    A catalogue row or permission possession alone never creates a scope.
    """
    registry = getattr(settings, "ACCESS_CONTROL_DELEGATION_POLICY", {})
    if type(registry) is not dict or not registry or len(registry) > 128:
        _policy_error()
    result = None
    for code, entry in registry.items():
        if type(code) is not str or len(code) > 100 or not re.fullmatch(r"[a-z][a-z0-9_]*", code):
            _policy_error()
        if type(entry) is not dict or set(entry) != {"authority_permission", "permission_codes", "role_names"}:
            _policy_error()
        authority = entry["authority_permission"]
        if type(authority) is not str or authority != f"access_control.delegate.{code}" or len(authority) > 150:
            _policy_error()
        permissions = _strings(entry["permission_codes"], 1024, 150)
        roles = _strings(entry["role_names"], 100, 50)
        if any(not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", item) for item in permissions):
            _policy_error()
        if any(is_reserved_role(name) for name in roles):
            _policy_error()
        if code == service_code:
            result = ApprovedDelegationScope(code, authority, permissions, roles)
    if result is None:
        _policy_error()
    return result


def require_governance_authority(actor, permission_code):
    """Use the existing evaluator and require the proposed catalogue placement."""
    entry = Permission.objects.using(DEFAULT_DB_ALIAS).select_related("service").filter(permission_code=permission_code).first()
    if (
        entry is None or entry.permission_code != permission_code
        or entry.service.service_code != GOVERNANCE_SERVICE
        or not entry.service.is_active or not has_permission(actor, permission_code)
    ):
        raise PermissionManagementDenied("Explicit active management/delegation authority is required.")


def require_delegation(actor, permission):
    """Deny-by-default check for one actual permission and its approved service.

    Mutation services must additionally lock authorization state and validate
    recipients. This read-only check alone is not permission to perform writes.
    """
    for value, model in ((actor, Account), (permission, Permission)):
        if not isinstance(value, model) or value._state.adding or value._state.db != DEFAULT_DB_ALIAS or type(value.pk) is not int:
            raise PermissionManagementDenied("Trusted persisted references are required.")
    current = Permission.objects.using(DEFAULT_DB_ALIAS).select_related("service").filter(pk=permission.pk).first()
    if current is None or not current.service.is_active or is_governance_permission(current):
        raise PermissionManagementDenied("The permission is not eligible for ordinary delegation.")
    scope = approved_scope(current.service.service_code)
    if current.permission_code not in scope.permission_codes:
        raise PermissionManagementDenied("The permission is outside the reviewed delegation scope.")
    require_governance_authority(actor, scope.authority_permission)
    return scope
