"""WF-03.01 D-113: gated, session-selected role-context scope (STAGED).

The context variable is a *request-local restriction*, not a permission or a
trusted role claim. All selected-role IDs and inheritance are freshly validated
against active AccountRole rows before evaluating stored RolePermission grants.
When enabled, an absent scope denies all effective permissions. No middleware
is installed in normal production settings; isolated review profiles only.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user
from django.db import DEFAULT_DB_ALIAS

from apps.access_control.models import AccountRole
from apps.access_control.ordinary_role_runtime import (
    ORDINARY_ROLE_NAMES, runtime_enforcement_enabled, verified_ordinary_roles_for,
)

SESSION_ROLE_KEY = "workspace_active_role_id"
_SELECTED = ContextVar("workspace_selected_role_scope", default=None)


def context_enabled():
    return getattr(settings, "WORKSPACE_ACTIVE_ROLE_CONTEXT_ENABLED", False) is True


@dataclass(frozen=True)
class RoleScope:
    account_id: int
    role_id: int | None


@contextmanager
def bind_role_scope(account_id, role_id):
    # Only trusted server code may set a scope. Query validation is in allowed_role_ids.
    chosen = role_id if type(role_id) is int and role_id > 0 else None
    token = _SELECTED.set(RoleScope(account_id, chosen))
    try:
        yield
    finally:
        _SELECTED.reset(token)


def selected_scope():
    return _SELECTED.get()


def _eligible_rows(account_id):
    return list(AccountRole.objects.using(DEFAULT_DB_ALIAS).filter(
        account_id=account_id, account__is_active=True,
        account__request_status="Approved", role__is_active=True,
    ).values_list("role_id", "role__role_name"))


def available_roles(account_id):
    """Only eligible assignments, not roles claimed by the session or request."""
    if type(account_id) is not int or account_id <= 0:
        return []
    rows = _eligible_rows(account_id)
    verified = verified_ordinary_roles_for(account_id) if runtime_enforcement_enabled() else frozenset()
    return sorted(({"role_id": role_id, "role_name": name} for role_id, name in rows
                   if name not in ORDINARY_ROLE_NAMES or name in verified),
                  key=lambda x: (x["role_name"], x["role_id"]))


def allowed_role_ids(account_id, selected_role_id):
    """Restrict to selected stored grants; Technical inherits *assigned* Admin grants.

    This does not manufacture permissions or bypass the permission catalogue:
    both role assignments and all RolePermission rows must already exist.
    """
    if type(account_id) is not int or type(selected_role_id) is not int or selected_role_id <= 0:
        return frozenset()
    choices = available_roles(account_id)
    selected = next((r for r in choices if r["role_id"] == selected_role_id), None)
    if selected is None:
        return frozenset()
    allowed = {selected_role_id}
    if selected["role_name"] == "Technical Super Admin":
        allowed.update(r["role_id"] for r in choices if r["role_name"] == "Admin")
    return frozenset(allowed)


def initial_role_id(account_id):
    """Choose least-privileged familiar base context on login (never a new grant)."""
    priority = ("Student", "Instructor", "Treasurer", "SSG Advisor", "Admin", "Technical Super Admin")
    choices = available_roles(account_id)
    if not choices:
        return None
    return min(choices, key=lambda x: (priority.index(x["role_name"])
               if x["role_name"] in priority else len(priority), x["role_id"]))["role_id"]


class ActiveRoleContextMiddleware:
    """Bracket each isolated-review API request; reset scope on every exit.

    The request's Django session selects an ID, but never authorizes it.
    Session logout and CSRF run normally. Other paths have no role context.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not context_enabled() or not request.path.startswith("/api/v1/"):
            return self.get_response(request)
        # The protected executor authorizes through a separate process and has
        # not adopted the session-selected role contract. Refuse rather than
        # letting an unscoped executor operation bypass the UI role boundary.
        from apps.access_control.executor.client import enabled as executor_enabled
        if executor_enabled() and getattr(settings, "WORKSPACE_WF03_EXECUTOR_ACCOUNT_WRITES_ENABLED", False) is not True:
            from django.http import JsonResponse
            from django.utils.cache import patch_cache_control
            response = JsonResponse({"error": {"code": "role_context_unavailable",
                                              "message": "Role context is not available."}}, status=503)
            patch_cache_control(response, no_store=True)
            return response
        user = get_user(request)
        from apps.accounts.models import Account
        account_id = (user.pk if isinstance(user, Account) and user.pk
                      and not user.is_staff and not user.is_superuser else 0)
        selected = request.session.get(SESSION_ROLE_KEY, None)
        with bind_role_scope(account_id, selected):
            return self.get_response(request)
